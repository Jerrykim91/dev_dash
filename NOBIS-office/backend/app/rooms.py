"""Channel-scoped public rooms and ACL-bound meetings; personal homes reuse HomeService."""
import json,time,os
from .world import ROOM_DATA,map_for,walkable
from .social import SocialError,zone_channel


def instance_id(p):
 if p.get('scope','office').startswith('personal:'):return p['scope']
 return p.get('room_instance_id') or f"public:{p.get('channel_id','ch1')}:lobby"
def same_room(a,b):return instance_id(a)==instance_id(b) and a.get('channel_id')==b.get('channel_id')
def chat_id(p):
 if p.get('room_type')=='meeting' and p.get('scope')=='office':return 'zone:'+instance_id(p)
 return zone_channel(p.get('channel_id','ch1'),p['zone'],p.get('scope','office'))
class RoomManager:
 def __init__(self,repo,hub,homes):self.repo=repo;self.hub=hub;self.homes=homes;self.defs={d['room_type']:dict(d) for d in ROOM_DATA['definitions']}
 def initialize(self):
  with self.repo.connect() as c:
   for typ,d in self.defs.items():c.execute('INSERT INTO room_definitions VALUES(?,?) ON CONFLICT(room_type) DO UPDATE SET data=excluded.data',(typ,json.dumps(d,ensure_ascii=False)))
   for d in self.defs.values():
    if d.get('portal_id'):c.execute('INSERT INTO room_portals VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(d['portal_id'],'lobby',d['room_type'],json.dumps(d)))
 def map(self,p):return self.homes.map_for(p['scope'][9:]) if p.get('scope','office').startswith('personal:') else ROOM_DATA['maps'].get(p.get('room_type','lobby'),map_for('office'))
 def normalize(self,p):
  if p.get('scope','office').startswith('personal:'):p.update(room_type='home',room_id=p['scope'][9:],room_instance_id=p['scope'],owner_id=p['scope'][9:]);return
  if p.get('room_type') not in self.defs or p.get('room_instance_id','').startswith('personal:') or (p.get('scope')=='office' and not p.get('room_instance_id','').startswith(('meeting:'if p.get('room_type')=='meeting'else'public:')+p['channel_id']+':')):p.update(owner_id=None,room_type='lobby',room_id='lobby',room_instance_id=f"public:{p['channel_id']}:lobby",zone='office',**map_for('office')['spawn'])
 def allowed_meeting(self,uid,cid):
  row=self.repo.member(cid,uid)
  with self.repo.connect() as c:room=c.execute('SELECT * FROM chat_channels WHERE id=?',(cid,)).fetchone()
  return bool(row and row['state']=='active' and room and room['kind']=='meeting' and room['status']=='open')
 def plan(self,p,typ,meeting_id=None,position=None):
  if typ not in self.defs:raise SocialError('알 수 없는 룸입니다.',404)
  d=self.defs[typ];rid=meeting_id if typ=='meeting' else typ
  if typ=='meeting' and not self.allowed_meeting(p['id'],rid):raise SocialError('참석 권한이 있는 열린 회의만 입장할 수 있어요.',403)
  iid=f"meeting:{p['channel_id']}:{rid}" if typ=='meeting' else f"public:{p['channel_id']}:{typ}"
  if sum(instance_id(q.player)==iid and q.player['id']!=p['id'] for q in self.hub.peers.values())>=d['max_occupancy']:raise SocialError('해당 룸의 정원이 찼습니다.',409)
  m=ROOM_DATA['maps'][typ];dest=position if position and walkable('office',position['x'],position['y'],m) else d['spawn_point']
  self.ensure_instance(iid,typ,p['channel_id'],rid)
  return {'owner_id':None,'room_type':typ,'room_id':rid,'room_instance_id':iid,'zone':d['zone_id'],'scope':'office','x':dest['x'],'y':dest['y']}
 def ensure_instance(self,iid,typ,cid,rid):
  d=self.defs[typ]
  with self.repo.connect() as c:c.execute('INSERT OR IGNORE INTO room_instances VALUES(?,?,?,?,?,?,?)',(iid,typ,cid,rid,None,d['access_policy'],d['max_occupancy']))
 def restore(self,p,cid=None):
  with self.repo.connect() as c:saved=c.execute('SELECT * FROM room_presence WHERE user_id=? AND channel_id=?',(p['id'],cid or p['channel_id'])).fetchone()
  if saved:
   row=dict(saved)
   try:
    iid=row['room_instance_id'];meeting=iid.split(':',2)[2] if row['room_type']=='meeting' else None
    return self.plan(p,row['room_type'],meeting,{'x':row['x'],'y':row['y']})
   except SocialError:pass
  return self.plan(p,'lobby')
 def persist(self,p):
  if p.get('scope')!='office':return
  self.normalize(p);self.ensure_instance(p['room_instance_id'],p['room_type'],p['channel_id'],p['room_id'])
  with self.repo.connect() as c:c.execute('INSERT INTO room_presence VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,channel_id) DO UPDATE SET channel_id=excluded.channel_id,room_instance_id=excluded.room_instance_id,room_type=excluded.room_type,x=excluded.x,y=excluded.y,updated_at=excluded.updated_at',(p['id'],p['channel_id'],p['room_instance_id'],p['room_type'],p['x'],p['y'],time.time()))
 def zones(self,p):
  if p['scope'].startswith('personal:'):return [{'id':'personal','name':'개인 집','map_id':'home','private':True,'tiles':None,'anchor':self.map(p)['spawn'],'chat_bubbles_allowed':False}]
  d=self.defs[p.get('room_type','lobby')];m=self.map(p);return [{'id':d['zone_id'],'name':d['name'],'map_id':m['id'],'private':d['access_policy']!='public','tiles':None,'cells':m['walkable_tiles'],'anchor':m['spawn'],'chat_bubbles_allowed':p.get('room_type') not in ['focus','meeting']}]
 def info(self,p):
  d=self.defs.get(p.get('room_type'));m=self.map(p)
  if d is None:
   with self.repo.connect() as c:setting=c.execute('SELECT capacity FROM home_visit_settings WHERE owner_id=?',(p['owner_id'],)).fetchone()
   d={'access_policy':'owner_or_approved_visitor','max_occupancy':setting['capacity'] if setting else int(os.getenv('HOME_MAX_OCCUPANTS','5'))}
  return {k:p.get(k) for k in ['room_type','channel_id','room_instance_id','room_id','owner_id']}|{'access_policy':d['access_policy'],'max_occupancy':d['max_occupancy'],'spawn_point':m['spawn'],'exit_point':m.get('exit')}
 def last_public_channel(self,uid):
  with self.repo.connect() as c:row=c.execute('SELECT channel_id FROM room_presence WHERE user_id=? ORDER BY updated_at DESC LIMIT 1',(uid,)).fetchone()
  return row['channel_id'] if row else None
 def at_meeting_portal(self,p):
  o=next(o for o in map_for('office')['objects'] if o['id']=='portal-meeting')
  return p.get('room_type')=='lobby' and abs(p['x']-o['x'])+abs(p['y']-o['y'])<=1.15
 def counts(self,cid):return {typ:sum(p.player.get('scope')=='office' and p.player['channel_id']==cid and p.player.get('room_type','lobby')==typ for p in self.hub.peers.values()) for typ in self.defs}
 def directory(self,p):
  data=[{**d,'channel_id':p['channel_id'],'room_instance_id':f"public:{p['channel_id']}:{typ}",'occupancy':self.counts(p['channel_id'])[typ]} for typ,d in self.defs.items() if typ!='meeting']
  for room in self.repo.channels_for(p['id']):
   if room['kind']=='meeting':data.append({**self.defs['meeting'],'room_id':room['id'],'room_instance_id':f"meeting:{p['channel_id']}:{room['id']}",'channel_id':p['channel_id'],'name':room['name'],'membership':room['membership'],'status':room['status'],'can_enter':room['membership']=='active' and room['status']=='open','occupancy':sum(instance_id(q.player)==f"meeting:{p['channel_id']}:{room['id']}" for q in self.hub.peers.values())})
  return data
