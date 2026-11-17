import asyncio
import contextlib
import time
from ..world import map_for
from ..rooms import same_room,chat_id
from ..social import zone_channel
from ..services.work_status import participation_for

class Peer:
    def __init__(self,ws,user):
        self.ws=ws
        self.expires=user['expires']
        self.player={k:v for k,v in user.items() if k not in ('expires','auth_kind')}
        self.player.update(zone='office',presence='online',participation_mode=participation_for(user['work_status']),
            world_id='nobis',channel_id='ch1',scope='office',active_object=None,action='idle',direction='south',avatar={'id':'placeholder-v1','palette':'lavender'},**map_for('office')['spawn'])
        self.lock=asyncio.Lock()
        self.moved=time.monotonic()
        self.move_credit=.35
        self.chatted=0.
        self.window,self.count=time.monotonic(),0
        self.office_return=None
        self.persisted=0.
    async def send(self,data):
        async with self.lock:
            await asyncio.wait_for(self.ws.send_json(data),timeout=3)

class Hub:
    def __init__(self,repository=None):
        self.repository=repository
        self.peers={}
        self.lock=asyncio.Lock()
        self.avatar_colors={}
    def assign_avatar(self,peer):
        colors=['#d2beff','#b5e5d0','#ffceaf','#a9d8ff','#f4bfe7','#e5e8ac','#b7c6f2','#e5bbbc',
                '#bbdedc','#e2c99d','#c0b1df','#b2d4ad','#e6b8d0','#abc1dc','#d4d4aa','#d0b9a6']
        uid=peer.player['id']
        used={p.player['avatar']['palette'] for p in self.peers.values() if p.player['id']!=uid and p.player['channel_id']==peer.player['channel_id']}
        color=(self.repository.avatar_for(uid).get('palette') if self.repository else None) or self.avatar_colors.get(uid)
        if color not in colors or color in used: color=next((c for c in colors if c not in used),colors[0])
        self.avatar_colors[uid]=color
        peer.player['avatar']={'id':'placeholder-v1','palette':color}
        if self.repository:self.repository.save_avatar(uid,color)
    def can_read(self,peer,channel):
        if channel=='world':return True
        if channel=='channel:'+peer.player.get('channel_id','ch1'):return True
        scope=peer.player.get('scope','office')
        zone_id=chat_id(peer.player)
        if channel==zone_id:
            if peer.player.get('room_type')=='meeting':
                member=self.repository.member(peer.player.get('room_id'),peer.player['id']) if self.repository else None
                meeting=self.repository.channel(peer.player.get('room_id')) if self.repository else None
                return bool(member and member['state']=='active' and meeting and meeting['status']=='open')
            return True
        member=self.repository.member(channel,peer.player['id']) if self.repository else None
        return bool(channel.startswith('room:') and member and member['state']=='active')
    def can_write(self,peer,channel):
        if not self.can_read(peer,channel):return False
        ch=self.repository.channel(channel) if self.repository else None
        return not channel.startswith('room:') or bool(ch and ch['status']=='open')
    def public_player(self,player,viewer_id):
        result={**player,'zone_id':player['zone']}
        actions={'sitting':'앉아서 쉬는 중','working':'코드 작성 중','drinking':'커피 마시는 중','resting':'휴식 중','meeting':'회의 중'}
        work={'before_work':'출근 전','working':'근무 중','focusing':'집중 업무 중','meeting':'회의 중','break':'휴식 중','outside':'외근','after_work':'퇴근','vacation':'휴가 중'}
        result['status_text']=(player.get('message') or '휴가 중') if player['work_status']=='vacation' else (('미니게임 플레이 중' if player.get('minigame') else player.get('message')) or actions.get(player['action']) or work.get(player['work_status'],''))
        if player.get('scope','office').startswith('personal:') and viewer_id!=player['id'] and (not self.peers.get(viewer_id) or self.peers[viewer_id].player['scope']!=player['scope']):
            result.update(x=0,y=0,active_object=None,action='idle',status_text=player.get('message') or work.get(player['work_status'],''))
        return self.profile_filter(result,viewer_id) if hasattr(self,'profile_filter') else result
    def players_for(self,viewer_id):
        viewer=self.peers.get(viewer_id)
        return [self.public_player(p.player,viewer_id) for p in self.peers.values() if viewer and same_room(p.player,viewer.player)]
    def payload_for(self,data,peer):
        return {**data,'player':self.public_player(data['player'],peer.player['id'])} if 'player' in data else data
    async def broadcast(self,data,predicate=None):
        targets=[p for p in list(self.peers.values()) if predicate is None or predicate(p)]
        results=await asyncio.gather(*(p.send(self.payload_for(data,p)) for p in targets),return_exceptions=True)
        for p,result in zip(targets,results):
            if isinstance(result,Exception):
                with contextlib.suppress(Exception): await p.ws.close(code=1011)
    async def presence(self,kind,peer): await self.broadcast({'type':kind,'player':peer.player},lambda p:same_room(p.player,peer.player))
