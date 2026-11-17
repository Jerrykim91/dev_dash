import contextlib
import asyncio
from typing import Literal
from fastapi import Depends,Request,Query
from fastapi.responses import JSONResponse,FileResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from .service import CommunityError,PRIVACY
from .storage import MAX_BYTES
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Profile(Strict):
 bio:str=Field(default='',max_length=500)
 privacy:dict[str,Literal['public','friends','private']]
 @model_validator(mode='after')
 def keys(self):
  if set(self.privacy)!=set(PRIVACY):raise ValueError('All privacy fields required')
  return self
class Target(Strict):user_id:str=Field(min_length=1,max_length=100)
class Answer(Strict):action:Literal['accept','reject','cancel']
class Enabled(Strict):enabled:bool
class Group(Strict):
 name:str=Field(min_length=1,max_length=60)
 description:str=Field(default='',max_length=1000)
 visibility:Literal['private','public']='private'
 max_members:int=Field(default=12,ge=2,le=50)
 cover_media_id:str|None=Field(default=None,max_length=100)
 @field_validator('name')
 @classmethod
 def name_text(cls,v):
  if not v.strip():raise ValueError('Name required')
  return v.strip()
class Member(Strict):user_id:str=Field(min_length=1,max_length=100);action:Literal['leave','kick','manager','member']
class Decision(Strict):accept:bool
class Log(Strict):
 group_id:str=Field(min_length=1,max_length=100)
 text:str=Field(default='',max_length=5000)
 visibility:Literal['group','self']='group'
 media_ids:list[str]=Field(default_factory=list,max_length=4)
class Text(Strict):
 text:str=Field(min_length=1,max_length=1500)
 @field_validator('text')
 @classmethod
 def text_valid(cls,v):
  if not v.strip():raise ValueError('Text required')
  return v.strip()
class Reaction(Strict):emoji:Literal['like','heart','laugh','cheer'];enabled:bool
class Report(Strict):target_kind:Literal['log','comment','user'];target_id:str=Field(min_length=1,max_length=100);reason:str=Field(min_length=1,max_length=500)
class Resolution(Strict):hidden:bool;resolution:str=Field(min_length=1,max_length=500)

def install_community(app,svc,current_user):
 decode_slots=asyncio.Semaphore(2)
 @app.exception_handler(CommunityError)
 async def failed(_req,exc):return JSONResponse(status_code=exc.status,content={'detail':exc.message})
 async def flush(result):
  targets=set(svc.pending);svc.pending.clear()
  for who in targets:
   peer=svc.hub.peers.get(who)
   if peer:
    with contextlib.suppress(Exception):await peer.send({'type':'social_refresh'})
  return result
 @app.get('/api/community/profiles/me')
 def mine(user=Depends(current_user)):return svc.profile(user['id'],user['id'])
 @app.put('/api/community/profiles/me')
 async def edit_profile(data:Profile,user=Depends(current_user)):
  result=svc.save_profile(user['id'],data.model_dump());peer=svc.hub.peers.get(user['id'])
  if peer:await svc.hub.presence('status',peer)
  return await flush(result)
 @app.get('/api/community/profiles/{target}')
 def profile(target:str,user=Depends(current_user)):return svc.profile(user['id'],target)
 @app.get('/api/community/friends')
 def friends(user=Depends(current_user)):return svc.friends(user['id'])
 @app.post('/api/community/friend-requests')
 async def request_friend(data:Target,user=Depends(current_user)):return await flush(svc.request_friend(user['id'],data.user_id))
 @app.post('/api/community/friend-requests/{rid}')
 async def answer_friend(rid:str,data:Answer,user=Depends(current_user)):return await flush(svc.respond_friend(user['id'],rid,data.action))
 @app.delete('/api/community/friends/{target}')
 async def remove_friend(target:str,user=Depends(current_user)):return await flush(svc.remove_friend(user['id'],target))
 @app.put('/api/community/blocks/{target}')
 async def block(target:str,data:Enabled,user=Depends(current_user)):
  result=svc.block(user['id'],target,data.enabled)
  if data.enabled and hasattr(svc,'on_block'):await svc.on_block(user['id'],target)
  return await flush(result)
 @app.get('/api/community/groups')
 def groups(discover:bool=False,user=Depends(current_user)):return svc.groups(user['id'],discover)
 @app.get('/api/community/groups/{gid}')
 def group(gid:str,user=Depends(current_user)):
  with svc.repo.connect() as c:return svc.group_view(c,user['id'],gid)
 @app.post('/api/community/groups')
 async def create_group(data:Group,user=Depends(current_user)):return await flush(svc.save_group(user['id'],data.model_dump()))
 @app.put('/api/community/groups/{gid}')
 async def edit_group(gid:str,data:Group,user=Depends(current_user)):return await flush(svc.save_group(user['id'],data.model_dump(),gid))
 @app.delete('/api/community/groups/{gid}')
 async def delete_group(gid:str,user=Depends(current_user)):return await flush(svc.delete_group(user['id'],gid))
 @app.post('/api/community/groups/{gid}/members')
 async def member(gid:str,data:Member,user=Depends(current_user)):return await flush(svc.membership(user['id'],gid,data.user_id,data.action))
 @app.post('/api/community/groups/{gid}/invitations')
 async def invite(gid:str,data:Target,user=Depends(current_user)):return await flush(svc.invite(user['id'],gid,data.user_id))
 @app.post('/api/community/groups/{gid}/join')
 async def join(gid:str,user=Depends(current_user)):return await flush(svc.invite(user['id'],gid))
 @app.post('/api/community/invitations/{iid}')
 async def decide(iid:str,data:Decision,user=Depends(current_user)):return await flush(svc.respond_invite(user['id'],iid,data.accept))
 @app.get('/api/community/groups/{gid}/logs')
 def feed(gid:str,cursor:str|None=Query(default=None,max_length=300),limit:int=Query(default=10,ge=1,le=30),user=Depends(current_user)):return svc.feed(user['id'],gid,cursor,limit)
 @app.get('/api/community/logs/{lid}')
 def log(lid:str,user=Depends(current_user)):return svc.get_log(user['id'],lid)
 @app.post('/api/community/logs')
 async def write(data:Log,user=Depends(current_user)):return await flush(svc.write_log(user['id'],data.model_dump()))
 @app.put('/api/community/logs/{lid}')
 async def edit_log(lid:str,data:Log,user=Depends(current_user)):return await flush(svc.write_log(user['id'],data.model_dump(),lid))
 @app.delete('/api/community/logs/{lid}')
 async def delete_log(lid:str,user=Depends(current_user)):return await flush(svc.delete_log(user['id'],lid))
 @app.get('/api/community/logs/{lid}/comments')
 def comments(lid:str,user=Depends(current_user)):return svc.comments(user['id'],lid)
 @app.post('/api/community/logs/{lid}/comments')
 async def comment(lid:str,data:Text,user=Depends(current_user)):return await flush(svc.comment(user['id'],lid,data.text))
 @app.put('/api/community/logs/{lid}/comments/{cid}')
 async def edit_comment(lid:str,cid:str,data:Text,user=Depends(current_user)):return await flush(svc.comment(user['id'],lid,data.text,cid))
 @app.delete('/api/community/logs/{lid}/comments/{cid}')
 async def delete_comment(lid:str,cid:str,user=Depends(current_user)):return await flush(svc.comment(user['id'],lid,'',cid,True))
 @app.put('/api/community/reactions/{kind}/{target}')
 async def reaction(kind:Literal['log','comment'],target:str,data:Reaction,user=Depends(current_user)):return await flush(svc.reaction(user['id'],kind,target,data.emoji,data.enabled))
 @app.post('/api/community/media')
 async def upload(request:Request,user=Depends(current_user)):
  data=bytearray()
  async for chunk in request.stream():
   data.extend(chunk)
   if len(data)>MAX_BYTES:raise CommunityError('이미지는 5MB 이하로 업로드해 주세요.',413)
  async with decode_slots:return await run_in_threadpool(svc.upload,user['id'],bytes(data))
 @app.get('/api/community/media/{mid}')
 def media(mid:str,user=Depends(current_user)):
  path,kind=svc.media(user['id'],mid);return FileResponse(path,media_type=kind,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
 @app.get('/api/community/notifications')
 def notifications(user=Depends(current_user)):return svc.notifications(user['id'])
 @app.post('/api/community/notifications/read')
 async def read_all(user=Depends(current_user)):return await flush(svc.mark_read(user['id']))
 @app.post('/api/community/notifications/{nid}/read')
 async def read(nid:str,user=Depends(current_user)):return await flush(svc.mark_read(user['id'],nid))
 @app.post('/api/community/reports')
 def report(data:Report,user=Depends(current_user)):return svc.report(user['id'],data.target_kind,data.target_id,data.reason)
 @app.get('/api/admin/community/reports')
 def reports(user=Depends(current_user)):return svc.admin_reports(user['id'])
 @app.get('/api/admin/community/reports/{rid}')
 def review(rid:str,user=Depends(current_user)):return svc.admin_reports(user['id'],rid)
 @app.put('/api/admin/community/reports/{rid}')
 async def moderate(rid:str,data:Resolution,user=Depends(current_user)):return await flush(svc.moderate(user['id'],rid,data.hidden,data.resolution))

 @app.get('/api/admin/community/reports/{rid}/media/{mid}')
 def reported_media(rid:str,mid:str,user=Depends(current_user)):
  path,kind=svc.report_media(user['id'],rid,mid);return FileResponse(path,media_type=kind,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
