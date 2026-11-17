import contextlib,uuid,time,json
from typing import Literal
from fastapi import Depends
from pydantic import BaseModel,ConfigDict,Field,model_validator
from ..community.service import CommunityError
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Empty(Strict):pass
class Target(Strict):user_id:str=Field(min_length=1,max_length=100)
class HomeConfig(Strict):access:Literal['private','friends','invite_only'];capacity:int=Field(ge=1,le=5)
class Decision(Strict):accept:bool
class Invite(Target):
 request_id:str=Field(min_length=36,max_length=36)
 @model_validator(mode='after')
 def valid(self):uuid.UUID(self.request_id);return self
class Choice(Strict):
 card:int=Field(ge=0,le=11)
 revision:int=Field(ge=0)
 event_id:str=Field(min_length=36,max_length=36)
 @model_validator(mode='after')
 def valid(self):uuid.UUID(self.event_id);return self
class Share(Strict):kind:Literal['collection','furniture','multiplayer','solo'];target_id:str|None=Field(default=None,max_length=100);group_id:str|None=Field(default=None,max_length=100)
class Report(Strict):owner_id:str=Field(min_length=1,max_length=100);reason:str=Field(min_length=1,max_length=500)

def install_integration(app,svc,current_user,enter,leave,snapshot,flush_world):
 hub=svc.hub
 async def flush(result=None):
  targets=set(svc.community.pending);svc.community.pending.clear()
  for uid in targets:
   p=hub.peers.get(uid)
   if p:
    with contextlib.suppress(Exception):await p.send({'type':'social_refresh'})
  return result
 async def games_changed(result):
  for p in list(hub.peers.values()):
   active=svc.active(p.player['id']);solo=svc.games.active(p.player['id'])
   p.player['minigame']={'session_id':active['id'],'game_id':'coop-memory'} if active else {'session_id':solo['id'],'game_id':solo['game_id']} if solo else None
   with contextlib.suppress(Exception):
    await p.send({'type':'integration_refresh'});await hub.presence('status',p)
    if result and result.get('status')=='completed' and p.player['id'] in (result['host_user_id'],result['invited_user_id']):await p.send({'type':'home_state','state':svc.homes.state(p.player['id'])})
  return await flush(result)
 async def enforce(owner=None):
  for p in list(hub.peers.values()):
   scope=p.player['scope']
   if scope.startswith('personal:') and p.player['id']!=scope[9:] and (owner is None or scope=='personal:'+owner):
    with svc.repo.connect() as c:allowed=svc.allowed(c,p.player['id'],scope[9:])
    if not allowed:
     try:await leave(p,False)
     except CommunityError:
      p.player.update(scope='office',zone='office',x=2,y=2);svc.repo.save_presence(p.player,p.office_return);await p.ws.close(code=4003,reason='방문 권한 회수 및 복귀 채널 만석')
 async def blocked(a,b):
  svc.revoke(a,b);svc.revoke(b,a);await enforce()
  with svc.repo.connect() as c:
   for s in c.execute("SELECT * FROM multiplayer_game_sessions WHERE status IN ('pending','active') AND ((host_user_id=? AND invited_user_id=?) OR (host_user_id=? AND invited_user_id=?))",(a,b,b,a)).fetchall():svc.end(c,s['id'],'cancelled')
  await games_changed(None)
 svc.community.on_block=blocked
 @app.get('/api/integration')
 async def panel(user=Depends(current_user)):
  return await flush({'home':svc.home_panel(user['id']),'games':svc.panel(user['id'])})
 @app.put('/api/integration/home')
 async def config(data:HomeConfig,user=Depends(current_user)):
  result=svc.configure_home(user['id'],data.access,data.capacity);await enforce(user['id'])
  occupants=[p for p in hub.peers.values() if p.player['scope']=='personal:'+user['id'] and p.player['id']!=user['id']]
  owner_present=int(user['id'] in hub.peers and hub.peers[user['id']].player['scope']=='personal:'+user['id'])
  for p in occupants[max(0,data.capacity-owner_present):]:
   svc.revoke(user['id'],p.player['id'])
  await enforce(user['id']);return result
 @app.post('/api/integration/visits')
 async def visit(data:Target,user=Depends(current_user)):return await flush(svc.request_visit(user['id'],data.user_id))
 @app.post('/api/integration/visits/{rid}')
 async def decide(rid:str,data:Decision,user=Depends(current_user)):return await flush(svc.decide_visit(user['id'],rid,data.accept))
 @app.post('/api/integration/homes/{owner}/enter')
 async def home_enter(owner:str,data:Empty,user=Depends(current_user)):
  p=hub.peers.get(user['id'])
  if not p:raise CommunityError('월드에 연결한 뒤 입장하세요.',409)
  if svc.games.active(user['id']) or svc.active(user['id']):raise CommunityError('게임을 종료하고 이동하세요.',409)
  await enter(p,True,owner);return {'entered':owner}
 @app.post('/api/integration/homes/{owner}/kick')
 async def kick(owner:str,data:Target,user=Depends(current_user)):
  if owner!=user['id'] or owner==data.user_id:raise CommunityError('집 소유자만 방문자를 내보낼 수 있습니다.',403)
  svc.revoke(owner,data.user_id);await enforce(owner)
  return svc.home_panel(owner)
 @app.post('/api/integration/home-reports')
 async def report(data:Report,user=Depends(current_user)):
  p=hub.peers.get(user['id'])
  if not p or p.player['scope']!='personal:'+data.owner_id:raise CommunityError('방문 중인 집만 신고할 수 있습니다.',403)
  with svc.repo.connect() as c:c.execute('INSERT INTO integration_reports VALUES (?,?,?,?,0,?)',(str(uuid.uuid4()),user['id'],data.owner_id,data.reason,svc.clock()))
  return {'ok':True}
 @app.post('/api/integration/games')
 async def invite(data:Invite,user=Depends(current_user)):
  for uid in (user['id'],data.user_id):
   p=hub.peers.get(uid)
   if not p or p.player['participation_mode']!='normal':raise CommunityError('두 사용자 모두 접속한 일반 모드여야 합니다.',409)
  return await games_changed(svc.invite_game(user['id'],data.user_id,data.request_id))
 @app.get('/api/integration/games/{sid}')
 async def game(sid:str,user=Depends(current_user)):return await flush(svc.game_state(user['id'],sid))
 @app.post('/api/integration/games/{sid}/accept')
 async def accept(sid:str,data:Decision,user=Depends(current_user)):return await games_changed(svc.accept_game(user['id'],sid,data.accept))
 @app.post('/api/integration/games/{sid}/cards')
 async def choose(sid:str,data:Choice,user=Depends(current_user)):
  try:result=svc.choose(user['id'],sid,data.card,data.revision,data.event_id)
  except CommunityError as exc:
   with svc.repo.connect() as c:
    if not c.execute('SELECT 1 FROM multiplayer_validation_events WHERE user_id=? AND created_at>?',(user['id'],svc.clock()-10)).fetchone():c.execute('INSERT INTO multiplayer_validation_events VALUES (?,?,?,?,?)',(str(uuid.uuid4()),user['id'],sid,exc.message,svc.clock()))
   raise
  return await games_changed(result)
 @app.post('/api/integration/games/{sid}/cancel')
 async def cancel(sid:str,data:Empty,user=Depends(current_user)):return await games_changed(svc.cancel_game(user['id'],sid))
 @app.get('/api/integration/collection')
 def collection(user=Depends(current_user)):return svc.collections(user['id'])
 @app.post('/api/integration/share/preview')
 def preview(data:Share,user=Depends(current_user)):return {'text':svc.share_preview(user['id'],data.kind,data.target_id)}
 @app.post('/api/integration/share')
 async def share(data:Share,user=Depends(current_user)):
  text=svc.share_preview(user['id'],data.kind,data.target_id)
  if not data.group_id:raise CommunityError('공유할 그룹을 선택하세요.')
  return await flush(svc.community.write_log(user['id'],{'group_id':data.group_id,'text':text,'visibility':'group','media_ids':[]}))
 @app.get('/api/admin/integration')
 def admin(user=Depends(current_user)):return svc.admin(user['id'])
 @app.put('/api/admin/integration/reports/{rid}')
 def resolve(rid:str,data:Empty,user=Depends(current_user)):
  svc.social.require(user['id'],'social_moderate')
  with svc.repo.connect() as c:c.execute('UPDATE integration_reports SET resolved=1 WHERE id=?',(rid,));svc.social.audit(c,user['id'],'home_report_resolved',rid)
  return {'ok':True}
