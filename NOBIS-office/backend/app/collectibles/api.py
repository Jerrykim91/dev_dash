import contextlib,uuid
from typing import Literal
from fastapi import Depends,Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .service import CollectibleError
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Empty(Strict):pass
class Draw(Strict):
 banner_id:str=Field(min_length=1,max_length=80)
 pool_version:int=Field(ge=1)
 count:Literal[1,5]
 request_id:str=Field(min_length=36,max_length=36)
 @model_validator(mode='after')
 def key(self):
  uuid.UUID(self.request_id)
  if hasattr(self,'count') and type(self.count)!=int:raise ValueError('Integer draw count required')
  return self
class PoolItem(Strict):coin_amount:int=Field(ge=10,le=1000);weight_bps:int=Field(ge=1,le=10000)
class Banner(Strict):
 name:str=Field(min_length=1,max_length=80)
 description:str=Field(default='',max_length=500)
 enabled:bool
 rarity_weights:dict[str,int]
 items:list[PoolItem]=Field(min_length=1,max_length=100)
 @model_validator(mode='after')
 def valid(self):
  if not self.name.strip() or any(type(v)!=int or v<0 or v>10000 for v in self.rarity_weights.values()):raise ValueError('Invalid probability weights')
  return self
class Reward(Strict):reward_tickets:int=Field(ge=0,le=10)
class Grant(Strict):
 user_id:str=Field(min_length=1,max_length=100)
 tickets:int=Field(ge=1,le=1000)
 request_id:str=Field(min_length=36,max_length=36)
 @model_validator(mode='after')
 def key(self):uuid.UUID(self.request_id);return self

def install_collectibles(app,svc,hub,current_user):
 @app.exception_handler(CollectibleError)
 async def failed(_req,exc):return JSONResponse(status_code=exc.status,content={'detail':exc.message})
 @app.get('/api/collectibles/attendance')
 def status(month:str|None=Query(default=None,max_length=7),user=Depends(current_user)):return svc.status(user['id'],month)
 @app.post('/api/collectibles/attendance')
 def claim(data:Empty,user=Depends(current_user)):return svc.claim(user['id'])
 @app.get('/api/collectibles/banners')
 def banners(user=Depends(current_user)):return svc.banners()
 @app.post('/api/collectibles/draws')
 async def draw(data:Draw,user=Depends(current_user)):
  result=svc.draw(user['id'],data.banner_id,data.count,data.request_id,data.pool_version);peer=hub.peers.get(user['id'])
  if peer:
   with contextlib.suppress(Exception):await peer.send({'type':'home_state','state':svc.homes.state(user['id'])})
  if hasattr(svc,'community'):
   targets=set(svc.community.pending);svc.community.pending.clear()
   for uid in targets:
    p=hub.peers.get(uid)
    if p:
     with contextlib.suppress(Exception):await p.send({'type':'social_refresh'})
  return result
 @app.get('/api/collectibles/history')
 def history(user=Depends(current_user)):return svc.history(user['id'])
 @app.get('/api/collectibles/draws/{did}')
 def receipt(did:str,user=Depends(current_user)):return svc.receipt(user['id'],did)
 @app.get('/api/admin/collectibles')
 def admin(user=Depends(current_user)):return svc.admin(user['id'])
 @app.put('/api/admin/collectibles/attendance')
 def reward(data:Reward,user=Depends(current_user)):return svc.configure_attendance(user['id'],data.reward_tickets)
 @app.put('/api/admin/collectibles/banners/{bid}')
 def banner(bid:str,data:Banner,user=Depends(current_user)):
  if not 1<=len(bid)<=80 or not all(c.isalnum() or c in '-_' for c in bid):raise CollectibleError('배너 ID 형식을 확인해 주세요.')
  return svc.configure_banner(user['id'],bid,data.model_dump())
 @app.post('/api/admin/collectibles/grants')
 def grant(data:Grant,user=Depends(current_user)):return svc.grant(user['id'],data.user_id,data.tickets,data.request_id)
