import math
import contextlib
from uuid import UUID
from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .service import GameError
from ..world import map_for

class StrictModel(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Start(StrictModel):
    game_id:str=Field(max_length=40)
    request_id:str=Field(min_length=36,max_length=36)
    @model_validator(mode='after')
    def request(self):UUID(self.request_id);return self
class Hit(StrictModel):
    event_id:str=Field(min_length=36,max_length=36)
    cell:int=Field(ge=0,le=8)
    wave:int=Field(ge=-1,le=10000)
    challenge:str=Field(default='',max_length=56)
    @model_validator(mode='after')
    def event(self):UUID(self.event_id);return self
class Empty(StrictModel):pass
class Tier(StrictModel):
    min_score:int=Field(ge=0,le=100000)
    coins:int=Field(ge=0,le=1000)
class Settings(StrictModel):
    enabled:bool
    daily_cap:int=Field(ge=0,le=100000)
    rewards:list[Tier]=Field(min_length=1,max_length=10)
    @model_validator(mode='after')
    def ordered(self):
        if self.rewards[0].min_score!=0 or any(a.min_score>=b.min_score or a.coins>b.coins for a,b in zip(self.rewards,self.rewards[1:])):raise ValueError('Rewards must start at zero and increase monotonically')
        return self

def install_games(app,game,hub,current_user):
    async def presence(uid):
        peer=hub.peers.get(uid)
        if peer:
            active=game.active(uid);coop=game.multiplayer.active(uid) if hasattr(game,'multiplayer') else None;peer.player['minigame']={'session_id':active['id'],'game_id':active['game_id']} if active else {'session_id':coop['id'],'game_id':'coop-memory'} if coop else None
            if active:peer.player.update(action='idle',active_object=None)
            await hub.presence('status',peer)
    @app.exception_handler(GameError)
    async def game_error(_request,exc):return JSONResponse(status_code=exc.status,content={'detail':exc.message})
    @app.get('/api/games')
    def catalog(user=Depends(current_user)):return game.catalog()
    @app.get('/api/games/history')
    def history(user=Depends(current_user)):return game.history(user['id'])
    @app.get('/api/games/active')
    async def active(user=Depends(current_user)):
        current=game.active(user['id']);await presence(user['id'])
        return game.state(user['id'],current['id']) if current else None
    @app.post('/api/games/sessions')
    async def start(data:Start,user=Depends(current_user)):
        peer=hub.peers.get(user['id']);arcade=next(o for o in map_for('lounge')['objects'] if o['id']=='arcade')
        if not peer or peer.player['scope']!='office' or peer.player.get('room_type')!='lounge' or peer.player['participation_mode']!='normal' or math.hypot(peer.player['x']-arcade['x'],peer.player['y']-arcade['y'])>1.15:raise GameError('오피스 게임기 옆으로 먼저 이동해 주세요.',403)
        result=game.start(user['id'],data.game_id,data.request_id);await presence(user['id']);return result
    @app.get('/api/games/sessions/{sid}')
    async def state(sid:str,user=Depends(current_user)):
        result=game.state(user['id'],sid)
        if result['status']!='active':await presence(user['id'])
        return result
    @app.post('/api/games/sessions/{sid}/inputs')
    def inputs(sid:str,data:Hit,user=Depends(current_user)):return game.hit(user['id'],sid,data.event_id,data.cell,data.wave,data.challenge)
    async def end(uid,sid,cancel):
        result=game.finish(uid,sid,cancel);await presence(uid)
        peer=hub.peers.get(uid)
        if peer:
            with contextlib.suppress(Exception):await peer.send({'type':'home_state','state':game.homes.state(uid)})
        return result
    @app.post('/api/games/sessions/{sid}/finish')
    async def finish(sid:str,data:Empty,user=Depends(current_user)):return await end(user['id'],sid,False)
    @app.post('/api/games/sessions/{sid}/cancel')
    async def cancel(sid:str,data:Empty,user=Depends(current_user)):return await end(user['id'],sid,True)
    @app.get('/api/admin/games')
    def admin_games(user=Depends(current_user)):return game.admin_data(user['id'],'games')
    @app.get('/api/admin/game-rewards')
    def rewards(user=Depends(current_user)):return game.admin_data(user['id'],'game-rewards')
    @app.get('/api/admin/game-sessions')
    def sessions(user=Depends(current_user)):return game.admin_data(user['id'],'game-sessions')
    @app.get('/api/admin/game-alerts')
    def alerts(user=Depends(current_user)):return game.admin_data(user['id'],'game-alerts')
    @app.put('/api/admin/games/{gid}')
    def configure(gid:str,data:Settings,user=Depends(current_user)):return game.configure(user['id'],gid,data.model_dump())
