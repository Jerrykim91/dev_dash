import asyncio
import anyio
import contextlib
import hmac
import json
import math
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import Request, Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from .repository import Repository
from .client_config import client_config,valid_dashboard_url
from .home import HomeService, HomeError
from .rooms import RoomManager,same_room,instance_id,chat_id
from .integration.service import IntegrationService
from .integration.api import install_integration
from .games.service import GameService
from .games.api import install_games
from .community.service import CommunityService,CommunityError
from .community.api import install_community
from .collectibles.service import CollectibleService
from .collectibles.api import install_collectibles
from .social import SocialService,SocialError,zone_channel
from fastapi.responses import JSONResponse
from .models.contracts import Login, Move, ChatInput, StatusChange, ChannelCreate, PersonalSettings, HomeLayout, ShopPurchase, PasswordLogin, PrivateInput, ChatPreferences
from .services.work_status import MockWorkStatusProvider, participation_for
from .websocket.hub import Hub, Peer
from .world import allowed, map_for, valid_move, zones_for, zone_at, walkable, WORLD, WORLD_REVISION

ENV=os.getenv('APP_ENV','development')
DEV_AUTH=os.getenv('DEV_AUTH_ENABLED','false').lower()=='true'
ADMIN_KEY=os.getenv('DEV_ADMIN_KEY','')
ORIGINS=set(os.getenv('ALLOWED_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:15173,http://127.0.0.1:15173,http://localhost:8080,http://127.0.0.1:8080').split(','))
repository=Repository(os.getenv('DATABASE_URL') or os.getenv('DATABASE_PATH','data/nobis.sqlite3'))
social=SocialService(repository)
homes=HomeService(repository,1000 if ENV=='development' else 0)
games=GameService(repository,homes,social)
work_status_provider=MockWorkStatusProvider(repository)
hub=Hub(repository)
community=CommunityService(repository,social,hub)
collectibles=CollectibleService(repository,homes,social)
hub.profile_filter=community.mask_world
collectibles.community=community
integration=IntegrationService(repository,homes,social,community,games,hub)
games.multiplayer=integration
rooms=RoomManager(repository,hub,homes)

@asynccontextmanager
async def lifespan(app):
    if DEV_AUTH and ENV!='development': raise RuntimeError('Development authentication is forbidden outside development')
    app.state.started_at=time.monotonic()
    client_config()
    repository.initialize()
    homes.initialize()
    social.initialize(int(os.getenv('CHANNEL_CAPACITY','15')))
    games.initialize()
    collectibles.initialize()
    integration.initialize()
    rooms.initialize()
    for cid,kind,name in [('world','world','월드'),('announcements','announcement','운영자 공지')]+[(f"zone:{z['id']}",'zone',z['name']) for z in zones_for()]:
        repository.ensure_channel(cid,kind,name)
    watcher=asyncio.create_task(integration_tick())
    try:yield
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):await watcher
    for p in list(hub.peers.values()):
        with contextlib.suppress(Exception): await p.ws.close(code=1001)
    hub.peers.clear()

app=FastAPI(title='NOBIS Office',version='0.6.0',lifespan=lifespan)

def current_user(authorization:str=Header(default='')):
    user=repository.user_for(authorization.removeprefix('Bearer '))
    if not user or (ENV!='development' and user.get('auth_kind')!='password'): raise HTTPException(401,'세션이 만료되었습니다')
    return user

@app.get('/health')
@app.get('/api/health')
def health():
    try:repository.ping()
    except repository.errors:return JSONResponse(status_code=503,content={'status':'error','database':'unavailable'})
    return {'status':'ok','temporary_auth':DEV_AUTH,'max_players':15,'dev_admin_login':bool(DEV_AUTH and ENV=='development' and ADMIN_KEY),'database':repository.kind}

@app.middleware('http')
async def database_availability(request,call_next):
    try:return await call_next(request)
    except repository.errors:return JSONResponse(status_code=503,content={'detail':'DB 연결이 일시적으로 중단됐습니다. 잠시 후 다시 시도하세요.'})

@app.get('/api/client-config')
def public_config():return client_config()

@app.post('/api/dev-login')
def login(data:Login):
    if ENV!='development' or not DEV_AUTH: raise HTTPException(403,'개발 인증 비활성화')
    nickname=data.nickname.strip()
    if not nickname: raise HTTPException(422,'닉네임을 입력하세요')
    if data.admin_key and (not ADMIN_KEY or not hmac.compare_digest(data.admin_key.encode(),ADMIN_KEY.encode())):
        raise HTTPException(403,'운영자 테스트 키가 올바르지 않습니다')
    token,user=repository.create_user(nickname,'admin' if data.admin_key else 'member',origin='development')
    public={k:v for k,v in user.items() if k not in ('expires','auth_kind')}
    return {'token':token,'user':public,'home_id':f"personal:{user['id']}"}

login_attempts={}
@app.post('/api/login')
def password_login(data:PasswordLogin,request:Request):
    key=request.client.host if request.client else 'local';now=time.monotonic()
    attempts=[t for t in login_attempts.get(key,[]) if now-t<60]
    if len(attempts)>=10:raise HTTPException(429,'잠시 후 다시 시도하세요.')
    attempts.append(now);login_attempts[key]=attempts
    uid=social.password_user(data.user_id,data.password)
    if not uid:raise HTTPException(401,'계정 ID 또는 비밀번호를 확인하세요.')
    token,user=repository.issue_session(uid);login_attempts.pop(key,None)
    return {'token':token,'user':{k:v for k,v in user.items() if k not in ('expires','auth_kind')},'home_id':f"personal:{user['id']}"}

@app.exception_handler(SocialError)
async def social_error(_request,exc):return JSONResponse(status_code=exc.status,content={'detail':exc.message})

def ensure_instance_chat(cid):
    repository.ensure_channel('channel:'+cid,'channel',cid)
    for z in zones_for():repository.ensure_channel(zone_channel(cid,z['id']),'zone',z['name'])

def world_channels_payload():
    return [{**ch,'online':sum(p.player['channel_id']==ch['id'] and p.player['scope']=='office' for p in hub.peers.values())} for ch in social.channels()]

async def world_channel_counts():
    await hub.broadcast({'type':'world_channels','channels':world_channels_payload()})
    await asyncio.gather(*(p.send({'type':'room_counts','counts':rooms.counts(p.player['channel_id'])}) for p in list(hub.peers.values())),return_exceptions=True)

@app.get('/api/world-channels')
def world_channels(user=Depends(current_user)):return world_channels_payload()

@app.get('/api/directory')
def user_directory(q:str='',user=Depends(current_user)):
    result=[]
    for u in social.directory(q[:60]):
        profile=community.profile(user['id'],u['id']);peer=hub.peers.get(u['id'])
        result.append({**u,'online':profile['presence']=='online' if profile['presence'] is not None else None,'channel_id':peer.player['channel_id'] if peer and profile['location'] is not None else None})
    return result

@app.get('/api/private-messages')
def private_history(user=Depends(current_user)):return social.private_history(user['id'])

@app.get('/api/chat-preferences')
def preferences(user=Depends(current_user)):return social.preference(user['id'])

@app.put('/api/chat-preferences')
async def set_preferences(data:ChatPreferences,user=Depends(current_user)):
    result=social.save_preference(user['id'],data.chat_bubbles_enabled)
    peer=hub.peers.get(user['id'])
    if peer:
        await peer.send({'type':'chat_preferences','preferences':result})
        if not data.chat_bubbles_enabled:await hub.broadcast({'type':'bubble_clear','user_id':user['id']},lambda p:p.player['channel_id']==peer.player['channel_id'])
    return result

@app.get('/api/announcements')
def announcement_history(user=Depends(current_user)):
    peer=hub.peers.get(user['id']);saved=repository.presence_for(user['id'])
    return social.announcements(peer.player['channel_id'] if peer else (saved or {}).get('channel_id','ch1'))

async def snapshot(peer):
    rooms.normalize(peer.player);uid=peer.player['id'];current=rooms.map(peer.player)
    revision=__import__('hashlib').sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()[:16]
    room_instance=instance_id(peer.player);revision=room_instance+':'+revision
    office_map=current if peer.player['scope']=='office' and getattr(peer,'world_revision_sent',None)!=revision else None
    await peer.send({'type':'snapshot','world_revision':revision,'office_map':office_map,'room_instance_id':room_instance,'room_type':peer.player['room_type'],'room_id':peer.player['room_id'],'room':rooms.info(peer.player),'room_counts':rooms.counts(peer.player['channel_id']),'players':hub.players_for(uid),'zones':rooms.zones(peer.player),'scope_map':current if peer.player['scope'].startswith('personal:') else None,'max_players':social.channel(peer.player['channel_id'])['capacity'],'channels':repository.channels_for(uid),'home_state':homes.state(uid),'world_channels':world_channels_payload(),'world_channel_id':peer.player['channel_id'],'room_settings':repository.settings_for(uid),'dashboard_config':client_config(),'chat_preferences':social.preference(uid),'private_messages':social.private_history(uid),'announcements':social.announcements(peer.player['channel_id'])})
    peer.world_revision_sent=revision

async def change_public_room(peer,typ,meeting_id=None):
    p=peer.player
    async with hub.lock:
        if p['scope']!='office':raise SocialError('개인 집에서 먼저 나와 주세요.',409)
        old=dict(p)
        position=rooms.defs.get(p.get('room_type'),{}).get('lobby_return') if typ=='lobby' else None
        plan=rooms.plan(p,typ,meeting_id,position)
        repository.ensure_channel('zone:'+plan['room_instance_id'] if typ=='meeting' else zone_channel(p['channel_id'],plan['zone']),'zone',rooms.defs[typ]['name'])
        p.update(**plan,action='idle',active_object=None)
        try:persist(peer)
        except repository.errors:
            p.clear();p.update(old);raise
        peer.moved=time.monotonic();peer.move_credit=.35
    await hub.broadcast({'type':'left','id':p['id']},lambda q:q is not peer and same_room(q.player,old))
    await snapshot(peer);await hub.presence('joined',peer);await world_channel_counts()

@app.get('/api/rooms')
def room_directory(user=Depends(current_user)):
    p=hub.peers.get(user['id'])
    return rooms.directory(p.player if p else {'id':user['id'],'channel_id':'ch1','scope':'office'})

async def switch_world_channel(peer,cid):
    p=peer.player
    if p['scope']!='office':raise SocialError('집에서 나온 뒤 채널을 이동하세요.',409)
    async with hub.lock:
        target=social.channel(cid)
        if not target or not target['enabled']:raise SocialError('입장할 수 없는 채널입니다.',404)
        if cid==p['channel_id']:return
        if sum(other.player['channel_id']==cid and other.player['scope']=='office' for other in hub.peers.values())>=target['capacity']:raise SocialError('대상 채널의 정원이 찼습니다.',409)
        old=p['channel_id']
        rooms.persist(p);p.update(channel_id=cid);p.update(**rooms.restore(p),world_id='nobis',action='idle',active_object=None)
        hub.assign_avatar(peer);peer.moved=time.monotonic();peer.move_credit=.35
    await hub.broadcast({'type':'left','id':p['id']},lambda other:other.player['channel_id']==old)
    ensure_instance_chat(cid)
    await snapshot(peer);await hub.presence('joined',peer);await world_channel_counts()

async def whisper(peer,text,recipient=None):
    social.muted(peer.player['id'])
    if time.monotonic()-peer.chatted<.4:raise SocialError('메시지를 잠시 후 다시 보내 주세요.',429)
    recipient,body=social.resolve_recipient(text,recipient)
    if recipient['id']==peer.player['id']:raise SocialError('본인에게는 귓속말을 보낼 수 없어요.')
    community.require_unblocked(peer.player['id'],recipient['id'])
    target=hub.peers.get(recipient['id']);chat=social.private(peer.player['id'],recipient['id'],body,False);peer.chatted=time.monotonic()
    if target:
        try:
            await target.send({'type':'private_message','chat':{**chat,'delivery':'delivered'}})
            social.mark_delivered(chat['id'])
            chat['delivery']='delivered'
        except Exception:pass
    await peer.send({'type':'private_message','chat':chat})

@app.get('/api/me')
def me(user=Depends(current_user)):
    return {k:v for k,v in user.items() if k not in ('expires','auth_kind')}

@app.get('/api/zones')
def zones(user=Depends(current_user)): return zones_for(user['id'])

@app.get('/api/users')
def users(user=Depends(current_user)): return hub.players_for(user['id'])

@app.get('/api/zones/{zone}/users')
def zone_users(zone:str,user=Depends(current_user)):
    if not allowed(zone,user['id']): raise HTTPException(403,'공간 권한 없음')
    viewer=hub.peers.get(user['id'])
    return [hub.public_player(p.player,user['id']) for p in hub.peers.values() if viewer and p.player['zone']==zone and same_room(p.player,viewer.player)]

@app.get('/api/work-status')
def work_status(user=Depends(current_user)):
    return {'work_status':user['work_status'],'participation_mode':participation_for(user['work_status']),'provider':'mock'}

def actor_for(user):
    from types import SimpleNamespace
    return hub.peers.get(user['id']) or SimpleNamespace(player={**user,'zone':'office','scope':'office','channel_id':(repository.presence_for(user['id']) or {}).get('channel_id','ch1')})

@app.get('/api/channels')
def channels(user=Depends(current_user)):
    return repository.channels_for(user['id'])

@app.get('/api/channels/{channel_id}/messages')
def messages(channel_id:str,user=Depends(current_user)):
    if channel_id=='private':return social.private_history(user['id'])
    if not hub.can_read(actor_for(user),channel_id):raise HTTPException(403,'메시지 조회 권한 없음')
    return repository.history(channel_id)

@app.get('/api/personal-room')
def room_settings(user=Depends(current_user)):
    return repository.settings_for(user['id'])

@app.put('/api/personal-room')
def save_room_settings(data:PersonalSettings,user=Depends(current_user)):
    url=data.dashboard_url.strip()
    if not valid_dashboard_url(url,ENV!='development'):raise HTTPException(422,'유효한 http(s) 주소가 필요합니다. 운영 환경에서는 localhost/127.0.0.1 등 로컬 주소를 사용할 수 없습니다.')
    result=repository.save_settings(user['id'],data.name.strip() or '나의 방',url)
    return result

@app.exception_handler(HomeError)
async def home_error_handler(_request,exc):return JSONResponse(status_code=exc.status,content={'detail':exc.message})

@app.get('/api/home')
def home_state(user=Depends(current_user)):return homes.state(user['id'])

@app.get('/api/homes/{room_id}')
def get_home(room_id:str,user=Depends(current_user)):
    if room_id==f"personal:{user['id']}":return homes.state(user['id'])
    p=hub.peers.get(user['id'])
    if not p or p.player['scope']!=room_id:raise HomeError('방문 중인 집만 조회할 수 있습니다.',403)
    with repository.connect() as c:
        if not integration.allowed(c,user['id'],room_id[9:]):raise HomeError('방문 권한 없음',403)
    return {'map':homes.map_for(room_id[9:])}

@app.put('/api/homes/{room_id}/layout')
async def save_home(room_id:str,data:HomeLayout,user=Depends(current_user)):
    homes.require_home(user['id'],room_id)
    peer=hub.peers.get(user['id'])
    if not peer or peer.player['scope']!=room_id:raise HomeError('내 집에 입장한 상태에서만 꾸밀 수 있어요.',403)
    if peer.player['participation_mode']!='normal':raise HomeError('관람 중에는 집을 편집할 수 없어요.',403)
    from .home import validate_layout,CATALOG_BY_ID
    for visitor in hub.peers.values():
        if visitor.player['scope']==room_id:
            validate_layout([p.model_dump() for p in data.placements],{i['id']:CATALOG_BY_ID[i['item_id']] for i in homes.state(user['id'])['inventory']},(visitor.player['x'],visitor.player['y']))
    result=homes.save(user['id'],room_id,data.revision,[p.model_dump() for p in data.placements],(peer.player['x'],peer.player['y']))
    peer.player.update(action='idle',active_object=None)
    await peer.send({'type':'home_state','state':result})
    await hub.broadcast({'type':'home_layout','scope':room_id,'map':result['map']},lambda p:p.player['scope']==room_id)
    await hub.presence('action',peer)
    return result

@app.post('/api/shop/purchases')
async def buy_furniture(data:ShopPurchase,user=Depends(current_user)):
    result=homes.purchase(user['id'],data.item_id,str(data.request_id))
    peer=hub.peers.get(user['id'])
    if peer:await peer.send({'type':'home_state','state':result['state']})
    return result

def player_map(player):
    return homes.map_for(player['scope'][9:]) if player['scope'].startswith('personal:') else rooms.map(player)

async def channel_updates():
    await asyncio.gather(*(p.send({'type':'channels','channels':repository.channels_for(p.player['id'])}) for p in list(hub.peers.values())))

def persist(peer):
    rooms.normalize(peer.player);rooms.persist(peer.player)
    repository.save_presence(peer.player,peer.office_return)
    peer.persisted=time.monotonic()

async def refresh_world():
    for member in list(hub.peers.values()):
        with contextlib.suppress(Exception):await snapshot(member)

async def change_scope(peer,personal,owner=None):
    p=peer.player;old=dict(p);owner=owner or p['id']
    if personal:
        if p['scope']=='personal:'+owner:return
        if p['scope']!='office':raise CommunityError('현재 집에서 나온 뒤 다른 집으로 이동하세요.',409)
        destination=integration.may_enter(p['id'],owner)['spawn']
        if sum(q.player['scope']=='personal:'+owner for q in hub.peers.values() if q is not peer)>=15:raise SocialError('개인 집의 정원이 찼습니다.',409)
        rooms.persist(p);peer.office_return={'x':p['x'],'y':p['y']}
        owner_peer=hub.peers.get(owner)
        if owner_peer and owner!=p['id']:p['channel_id']=owner_peer.player['channel_id']
        p.update(scope='personal:'+owner,zone='personal',**destination,action='idle',active_object=None)
        integration.mark_home(p['id'],owner);repository.ensure_channel('zone:personal:'+owner,'zone','개인 집')
        if p['id']!=owner:
            with repository.connect() as c:integration.note(c,owner,p['id'],'home_entered','승인한 방문자가 집에 들어왔습니다.',p['id'])
    else:
        if p['scope']=='office':return
        p['channel_id']=rooms.last_public_channel(p['id']) or p['channel_id']
        if sum(q.player['channel_id']==p['channel_id'] and q.player['scope']=='office' for q in hub.peers.values())>=social.channel(p['channel_id'])['capacity']:
            alternatives=[ch for ch in social.channels() if ch['enabled'] and sum(q.player['channel_id']==ch['id'] and q.player['scope']=='office' for q in hub.peers.values())<ch['capacity']]
            if not alternatives:raise CommunityError('복귀할 오피스 채널에 빈자리가 없습니다. 잠시 후 다시 시도하세요.',409)
            p['channel_id']=alternatives[0]['id'];peer.office_return=None
        p.update(**rooms.restore(p),action='idle',active_object=None);integration.mark_home(p['id'])
    rooms.normalize(p)
    peer.moved=time.monotonic();peer.move_credit=.35;persist(peer)
    await hub.broadcast({'type':'left','id':p['id']},lambda other:other is not peer and same_room(other.player,old))
    await snapshot(peer);await hub.presence('scope_changed',peer);await world_channel_counts()

async def integration_tick():
    while True:
        await asyncio.sleep(2)
        try:
            with repository.connect() as c:c.execute('BEGIN IMMEDIATE');integration.expire(c)
            for p in list(hub.peers.values()):
                if p.player.get('room_type')=='meeting' and not rooms.allowed_meeting(p.player['id'],p.player.get('room_id')):
                    await change_public_room(p,'lobby')
                if hub.peers.get(p.player['id']) is not p:continue
                if p.player['scope'].startswith('personal:') and p.player['scope']!='personal:'+p.player['id']:
                    with repository.connect() as c:permitted=integration.allowed(c,p.player['id'],p.player['scope'][9:])
                    if not permitted:
                        try:await change_scope(p,False)
                        except CommunityError:
                            spawn=map_for('office')['spawn'];p.player.update(scope='office',zone=zone_at(**spawn),**spawn);persist(p);await p.ws.close(code=4003)
                if p.player.get('minigame',{} ) and p.player['minigame'].get('game_id')=='coop-memory' and not integration.active(p.player['id']):
                    p.player['minigame']=None;await hub.presence('status',p)
            targets=set(community.pending);community.pending.clear()
            for uid in targets:
                peer=hub.peers.get(uid)
                if peer:
                    with contextlib.suppress(Exception):await peer.send({'type':'social_refresh'})
        except repository.errors:continue

async def error(peer,message): await peer.send({'type':'error','message':message})

async def handle(peer,msg):
    kind=msg.get('type')
    player=peer.player
    rooms.normalize(player)
    now=time.monotonic()
    if player['scope'].startswith('personal:') and player['scope']!='personal:'+player['id']:
        with repository.connect() as c:permitted=integration.allowed(c,player['id'],player['scope'][9:])
        if not permitted:await change_scope(peer,False)
    active_game=(games.active(player['id']) or integration.active(player['id'])) if kind in ('move','world_channel_move','room_enter','room_leave','interact','meeting_enter') else None
    if active_game and kind!='move':await error(peer,'게임을 종료한 뒤 이동하거나 상호작용해 주세요.');return
    if kind=='move':
        data=Move.model_validate(msg)
        before=(player['x'],player['y'])
        elapsed=now-peer.moved
        credit=min(.8,peer.move_credit+elapsed*4.5)
        distance=math.hypot(data.x-before[0],data.y-before[1])
        if active_game or player['participation_mode']=='spectator' or data.scope!=player['scope'] or data.channel_id!=player['channel_id'] or distance>credit or not valid_move(player.get('scope','office'),before,(data.x,data.y),max(elapsed,credit/4.5),player_map(player)):
            await peer.send({'type':'correction','zone':player['zone'],'scope':player['scope'],'x':before[0],'y':before[1]})
            return
        peer.moved=now;peer.move_credit=credit-distance
        previous_zone=player['zone']
        action='walking' if data.moving else ('idle' if player['action']=='walking' or distance>.001 else player['action'])
        player.update(x=data.x,y=data.y,zone='personal' if player['scope'].startswith('personal:') else rooms.defs[player.get('room_type','lobby')]['zone_id'],direction=data.direction,action=action)
        if data.moving or distance>.001:player['active_object']=None
        if previous_zone!=player['zone'] or now-peer.persisted>=1:persist(peer)
        kind='zone_changed' if previous_zone!=player['zone'] else 'moved'
        await hub.broadcast({'type':kind,'player':player,'from_zone':previous_zone},lambda p:same_room(p.player,player))
    elif kind=='travel':
        await error(peer,'별도 맵 이동은 없습니다. 월드 안의 목적지까지 걸어가세요.')
    elif kind=='status':
        data=StatusChange.model_validate(msg)
        work_status_provider.set_test_status(player['id'],data.work_status,data.message)
        player.update(work_status=data.work_status,message=data.message,participation_mode=participation_for(data.work_status))
        player['action']=data.work_status if data.work_status in ('vacation','after_work') else 'idle'
        player['active_object']=None
        persist(peer)
        await hub.presence('status',peer)
    elif kind=='meeting_enter':
        portal=next(o for o in map_for('office')['objects'] if o['id']=='portal-meeting')
        if player.get('room_type')!='lobby' or math.hypot(player['x']-portal['x'],player['y']-portal['y'])>1.15:raise SocialError('회의실 입구로 먼저 이동해 주세요.',403)
        await change_public_room(peer,'meeting',msg.get('meeting_id'))
    elif kind=='world_channel_move':
        cid=msg.get('channel_id')
        if not isinstance(cid,str) or len(cid)>32:raise SocialError('채널을 선택하세요.')
        await switch_world_channel(peer,cid)
    elif kind=='private_message':
        data=PrivateInput.model_validate({k:v for k,v in msg.items() if k!='type'})
        await whisper(peer,data.text,data.recipient_id)
    elif kind=='chat':
        data=ChatInput.model_validate(msg)
        if data.text.strip().startswith('@'):
            await whisper(peer,data.text.strip(),data.mentions[0] if data.mentions else None);return
        social.muted(player['id'])
        if not hub.can_write(peer,data.channel):await error(peer,'채팅 채널 권한이 없습니다');return
        if not data.text.strip():return
        if now-peer.chatted<.4:await error(peer,'메시지를 잠시 후 다시 보내 주세요');return
        peer.chatted=now
        mtype='world' if data.channel=='world' else 'channel' if data.channel.startswith('channel:') else 'zone' if data.channel.startswith('zone:') else 'private'
        chat={'id':str(uuid.uuid4()),'user_id':player['id'],'nickname':player['nickname'],'text':data.text.strip(),'time':datetime.now(timezone.utc).isoformat(),'channel':data.channel,'mentions':[],'message_type':mtype}
        repository.save_chat(chat)
        await hub.broadcast({'type':'chat','chat':chat},lambda p:hub.can_read(p,data.channel))
        zone=next((z for z in zones_for() if z['id']==player['zone']),{})
        if mtype in ('world','channel','zone') and player['scope']=='office' and zone.get('chat_bubbles_allowed',False) and social.preference(player['id'])['chat_bubbles_enabled']:
            await hub.broadcast({'type':'chat_bubble','user_id':player['id'],'channel_id':player['channel_id'],'zone':player['zone'],'text':chat['text'][:80],'expires_at':time.time()+6},lambda p:same_room(p.player,player) and hub.can_read(p,data.channel))
    elif kind=='interact':
        if player['participation_mode']=='spectator': await error(peer,'관람 중에는 오브젝트를 사용할 수 없어요');return
        obj=next((o for o in player_map(player)['objects'] if o['id']==msg.get('object_id')),None)
        if not obj or min(math.hypot(player['x']-(obj['x']+dx),player['y']-(obj['y']+dy)) for dx in range(obj.get('width',1)) for dy in range(obj.get('height',1)))>1.15:
            await error(peer,'오브젝트 옆으로 먼저 이동해 주세요');return
        interaction=obj.get('interaction')
        if not interaction: await error(peer,'이 오브젝트는 사용할 수 없어요');return
        if interaction['kind']=='public_enter':
            await change_public_room(peer,interaction['room_type']);return
        if interaction['kind']=='public_exit':
            await change_public_room(peer,'lobby');return
        if interaction['kind']=='home_exit':
            await change_scope(peer,False);return
        if interaction['kind']=='action':
            toggle=interaction.get('toggle') and player.get('active_object')==obj['id'] and player['action']==interaction['action']
            player['action']='idle' if toggle else interaction['action']
            player['active_object']=None if toggle else obj['id']
            persist(peer)
            await hub.presence('action',peer)
        payload={**interaction,'object_id':obj['id'],'label':obj['label']}
        if interaction['kind']=='action':payload['message']=({'desk':'작업을 종료했어요.','chair':'의자에서 일어났어요.','sofa':'휴식을 마쳤어요.'}.get(obj['kind'],'휴식을 마쳤어요.') if toggle else interaction.get('message','상태를 변경했어요.'))
        if obj['kind']=='bookshelf':
            await hub.broadcast({'type':'object_effect','scope':player['scope'],'object_id':obj['id']},lambda p:same_room(p.player,player))
        if payload['kind']=='menu':
            payload['targets']=[z for z in payload['targets'] if allowed(z,player['id'])]
        await peer.send({'type':'interaction','interaction':payload})
    elif kind=='channel_create':
        data=ChannelCreate.model_validate(msg)
        if player['scope']!='office' or not(player['zone']==data.kind or(data.kind=='meeting' and rooms.at_meeting_portal(player))):raise PermissionError('해당 카페/회의실 구역에서 대화를 만들어 주세요.')
        if not data.name.strip():raise ValueError('대화 이름이 필요해요.')
        cid=repository.create_channel(player['id'],data.kind,data.name.strip())
        await channel_updates();await peer.send({'type':'channel_created','channel_id':cid})
    elif kind in ('channel_invite','channel_accept','channel_leave','channel_close'):
        cid=msg.get('channel_id')
        if not isinstance(cid,str) or len(cid)>100:raise ValueError('채널 ID가 필요해요.')
        if kind=='channel_invite':
            target=msg.get('user_id')
            if not isinstance(target,str):raise ValueError('사용자 ID가 필요해요.')
            repository.invite(cid,player['id'],target)
            invited=hub.peers.get(target)
            if invited:await invited.send({'type':'notification','notification':{'id':str(uuid.uuid4()),'kind':'invite','message':f"{player['nickname']}님이 비공개 대화에 초대했어요.",'channel':cid}})
        elif kind=='channel_accept':repository.accept(cid,player['id'])
        elif kind=='channel_leave':
            repository.leave(cid,player['id']);await peer.send({'type':'channel_revoked','channel_id':cid})
        else:repository.close_channel(cid,player['id'])
        await channel_updates()
        if kind=='channel_accept':await peer.send({'type':'channel_accepted','channel_id':cid})
    elif kind=='history':
        cid=msg.get('channel')
        if cid=='private':
            await peer.send({'type':'history','channel':cid,'messages':social.private_history(player['id'])});return
        if not isinstance(cid,str) or not hub.can_read(peer,cid):raise PermissionError('메시지 조회 권한이 없어요.')
        await peer.send({'type':'history','channel':cid,'messages':repository.history(cid)})
    elif kind=='room_enter':
        await change_scope(peer,True,msg.get('owner_id') or player['id'])
    elif kind=='room_leave':await change_scope(peer,False)
    elif kind=='presence':
        state=msg.get('presence')
        if state not in ('online','away'): await error(peer,'유효하지 않은 접속 상태');return
        player['presence']=state;persist(peer);await hub.presence('presence',peer)
    elif kind=='ping': await peer.send({'type':'pong'})
    else: await error(peer,'지원하지 않는 이벤트')

@app.websocket('/ws')
async def websocket(ws:WebSocket):
    if ws.headers.get('origin') is not None and ws.headers['origin'] not in ORIGINS:
        await ws.close(code=1008);return
    await ws.accept()
    peer=None
    try:
        raw_auth=await asyncio.wait_for(ws.receive_text(),timeout=5)
        if len(raw_auth)>4096:await ws.close(code=1009);return
        auth=json.loads(raw_auth)
        if not isinstance(auth,dict) or not isinstance(auth.get('token'),str) or len(auth['token'])>256:await ws.close(code=1008);return
        user=repository.user_for(auth['token'])
        if not user or (ENV!='development' and user.get('auth_kind')!='password'): await ws.close(code=1008,reason='세션 만료');return
        peer=Peer(ws,user)
        active_game=games.active(user['id']) or integration.active(user['id'])
        peer.player['minigame']={'session_id':active_game['id'],'game_id':active_game.get('game_id','coop-memory')} if active_game else None
        saved=repository.presence_for(user['id'])
        requested=auth.get('channel_id')
        if requested is not None and (not isinstance(requested,str) or len(requested)>32):await ws.close(code=1008);return
        if active_game and requested and saved and requested!=saved['channel_id']:
            await ws.send_json({'type':'admission_denied','message':'게임을 종료한 뒤 채널을 변경해 주세요.','channel_id':requested,'world_channels':world_channels_payload()})
            await ws.close(code=4003,reason='게임 중 채널 변경 제한');return
        selected=requested or (saved['channel_id'] if saved and social.channel(saved['channel_id']) and social.channel(saved['channel_id'])['enabled'] else 'ch1')
        target=social.channel(selected)
        if not target or not target['enabled']:
            await ws.send_json({'type':'admission_denied','message':'입장할 수 없는 채널입니다. 다른 채널을 선택하세요.','channel_id':selected,'world_channels':world_channels_payload()})
            await ws.close(code=4003,reason='비활성화 또는 없는 채널');return
        peer.player['channel_id']=selected
        destination=social.location_for(user['id'],selected)
        peer.player.update(x=destination['x'],y=destination['y'],zone=zone_at(destination['x'],destination['y']))
        if saved and saved['channel_id']==selected and (saved['scope']=='office' or saved['scope'].startswith('personal:')) and walkable(saved['scope'],saved['x'],saved['y'],homes.map_for(saved['scope'][9:]) if saved['scope'].startswith('personal:') else None):
            peer.player.update(scope=saved['scope'],zone=zone_at(saved['x'],saved['y'],saved['scope']),x=saved['x'],y=saved['y'],active_object=None)
            if saved['return_x'] is not None:peer.office_return={'x':saved['return_x'],'y':saved['return_y']}
        if peer.player['scope'].startswith('personal:'):
            try:integration.may_enter(user['id'],peer.player['scope'][9:])
            except CommunityError:
                peer.player.update(scope='office',zone=zone_at(destination['x'],destination['y']),**destination);integration.mark_home(user['id'])
        if peer.player['scope']=='office':
            try:peer.player.update(**rooms.restore(peer.player))
            except SocialError as exc:
                await ws.send_json({'type':'admission_denied','message':exc.message,'world_channels':world_channels_payload()});await ws.close(code=4003);return
        rooms.normalize(peer.player)
        async with hub.lock:
            previous=hub.peers.get(user['id'])
            if peer.player['scope']=='office' and sum(p.player['channel_id']==selected and p.player['scope']=='office' and p.player['id']!=user['id'] for p in hub.peers.values())>=target['capacity']:
                await ws.send_json({'type':'admission_denied','message':'채널 정원이 찼습니다. 다른 채널을 선택하세요.','channel_id':selected,'world_channels':world_channels_payload()})
                await ws.close(code=4003,reason='채널 정원 초과');return
            if previous:
                if previous.player['channel_id']==selected:
                    peer.player.update(zone=previous.player['zone'],scope=previous.player['scope'],x=previous.player['x'],y=previous.player['y'])
                    peer.office_return=previous.office_return
                else:
                    persist(previous)
                    await hub.broadcast({'type':'left','id':user['id']},lambda p:same_room(p.player,previous.player))
                await previous.ws.close(code=4001,reason='다른 연결에서 접속했습니다')
            if peer.player['scope'].startswith('personal:'):
                with repository.connect() as c:permitted=integration.allowed(c,user['id'],peer.player['scope'][9:])
                if not permitted:peer.player.update(scope='office',zone=zone_at(destination['x'],destination['y']),**destination)
            hub.assign_avatar(peer)
            hub.peers[user['id']]=peer
        repository.ensure_channel(f"zone:personal:{user['id']}",'zone','개인 방')
        integration.connection(user['id'],True)
        if peer.player['scope'].startswith('personal:'):integration.mark_home(user['id'],peer.player['scope'][9:])
        persist(peer)
        ensure_instance_chat(peer.player['channel_id'])
        for delivered in social.deliver(user['id']):
            sender=hub.peers.get(delivered['sender_id'])
            if sender:await sender.send({'type':'private_delivered','id':delivered['id']})
        await snapshot(peer)
        await hub.presence('joined',peer)
        await world_channel_counts()
        session_checked=time.monotonic()
        while True:
            raw=await ws.receive_text()
            if len(raw)>4096: await ws.close(code=1009);break
            if time.time()>=peer.expires: await ws.close(code=1008,reason='세션 만료');break
            now=time.monotonic()
            if now-session_checked>=1:
                current=repository.user_for(auth.get('token'));session_checked=now
                if not current or (ENV!='development' and current.get('auth_kind')!='password'):
                    await ws.close(code=1008,reason='세션 만료 또는 회수');break
                if current['role']!=peer.player['role']:
                    peer.player['role']=current['role'];await hub.presence('status',peer)
            if now-peer.window>=1: peer.window,peer.count=now,0
            peer.count+=1
            if peer.count>40: await ws.close(code=1008,reason='전송 빈도 초과');break
            try:
                msg=json.loads(raw)
                if not isinstance(msg,dict): raise ValueError('object required')
                await handle(peer,msg)
            except (SocialError,CommunityError) as exc:
                await error(peer,exc.message)
            except PermissionError as exc:
                await error(peer,str(exc))
            except (ValidationError,ValueError,TypeError,AttributeError,KeyError):
                await error(peer,'유효하지 않은 메시지')
    except repository.errors:
        with contextlib.suppress(Exception):await ws.close(code=1013,reason='DB 연결 재시도 필요')
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):await ws.close(code=1008,reason='인증 시간 초과')
    except (ValueError,TypeError,KeyError):
        with contextlib.suppress(Exception):await ws.close(code=1003,reason='유효하지 않은 프레임')
    except (WebSocketDisconnect,RuntimeError):pass
    finally:
        if peer and hub.peers.get(peer.player['id']) is peer:
            del hub.peers[peer.player['id']]
            peer.player['presence']='offline'
            integration.connection(peer.player['id'],False)
            with contextlib.suppress(*repository.errors):persist(peer)
            with anyio.CancelScope(shield=True),contextlib.suppress(*repository.errors):
                await hub.broadcast({'type':'left','id':peer.player['id']},lambda p:same_room(p.player,peer.player))
                await world_channel_counts()

install_integration(app,integration,current_user,change_scope,change_scope,snapshot,refresh_world)
install_games(app,games,hub,current_user)
install_community(app,community,current_user)
install_collectibles(app,collectibles,hub,current_user)

from .admin import install_admin
install_admin(app,repository,social,hub,current_user,world_channels_payload,world_channel_counts)
