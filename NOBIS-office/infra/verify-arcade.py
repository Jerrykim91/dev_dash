#!/usr/bin/env python3
"""Real-time arcade smoke test against an isolated running stack (creates records/rewards)."""
import argparse,json,math,os,time,uuid,urllib.request,urllib.error
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit
from websockets.sync.client import connect
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-url',required=True);p.add_argument('--user-id',required=True);p.add_argument('--password-env',default='NOBIS_VERIFY_PASSWORD');p.add_argument('--plays',type=int,default=2);p.add_argument('--output');args=p.parse_args()
base=args.base_url.rstrip('/');token=None

def api(path,body=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(base+'/api'+path,headers=headers,data=None if body is None else json.dumps(body).encode(),method='GET' if body is None else 'POST')
 try:
  with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
 except urllib.error.HTTPError as e:raise RuntimeError(f'{path}: HTTP {e.code} '+e.read().decode()) from None
password=os.environ.get(args.password_env,'')
if not password:p.error('The password environment variable is empty')
login=api('/login',{'user_id':args.user_id,'password':password});token=login['token'];password=None
parsed=urlsplit(base);ws_url=('wss' if parsed.scheme=='https' else 'ws')+'://'+parsed.netloc+'/ws'
world=json.loads((Path(__file__).resolve().parents[1]/'shared/maps.json').read_text())['office'];blocked={(o['x'],o['y']) for o in world['objects'] if o.get('blocking',True)}
def path(start,target):
 queue=deque([start]);parent={start:None}
 while queue:
  a=queue.popleft()
  if a==target:
   result=[]
   while a is not None:result.append(a);a=parent[a]
   return result[::-1]
  for b in ((a[0]+1,a[1]),(a[0]-1,a[1]),(a[0],a[1]+1),(a[0],a[1]-1)):
   if 0<=b[0]<world['width'] and 0<=b[1]<world['height'] and b not in blocked and b not in parent:parent[b]=a;queue.append(b)
 raise RuntimeError('No connected path to the arcade')
with connect(ws_url,origin=base,open_timeout=10) as ws:
 ws.send(json.dumps({'token':token}))
 while True:
  m=json.loads(ws.recv(timeout=10))
  if m['type']=='snapshot':break
 own=next(v for v in m['players'] if v['id']==args.user_id);original=(own['x'],own['y']);channel=m['world_channel_id']
 if own['scope']!='office':raise RuntimeError('Use a test account in the public office')
 route=path((round(own['x']),round(own['y'])),(29,7));x,y=original
 for tx,ty in route[1:]:
  sx,sy=x,y
  for step in range(1,4):
   time.sleep(.1);x=sx+(tx-sx)*step/3;y=sy+(ty-sy)*step/3
   ws.send(json.dumps({'type':'move','scope':'office','zone':'office','channel_id':channel,'x':x,'y':y,'direction':'east','moving':True}))
   while True:
    event=json.loads(ws.recv(timeout=10))
    if event['type']=='correction':raise RuntimeError('Server rejected path movement')
    if event['type'] in ('moved','zone_changed') and event['player']['id']==args.user_id:break
 start_balance=api('/home')['balance'];results=[]
 for _ in range(args.plays):
  s=api('/games/sessions',{'game_id':'whack_a_mole','request_id':str(uuid.uuid4())});sid=s['session_id'];hit_waves=set()
  while s['remaining_ms']>0:
   m=s['mole']
   if m and m['wave'] not in hit_waves:
    try:
     result=api('/games/sessions/'+sid+'/inputs',{'event_id':str(uuid.uuid4()),'cell':m['cell'],'wave':m['wave'],'challenge':m['challenge']})
     if result['hit']:hit_waves.add(m['wave'])
    except RuntimeError as exc:
     if 'HTTP 422' not in str(exc) and 'HTTP 429' not in str(exc):raise
   time.sleep(.12);s=api('/games/sessions/'+sid)
  r=api('/games/sessions/'+sid+'/finish',{});repeat=api('/games/sessions/'+sid+'/finish',{})
  assert r['status']=='completed' and r['score']>=150 and r['reward']==30 and repeat['reward']==30 and repeat['balance']==r['balance'];results.append({'score':r['score'],'hits':r['hits'],'reward':r['reward'],'balance':r['balance']})
 end_balance=api('/home')['balance'];assert end_balance==start_balance+sum(r['reward'] for r in results)
 purchase=api('/shop/purchases',{'item_id':'furniture_plant_001','request_id':str(uuid.uuid4())});assert purchase['state']['balance']==end_balance-40
 history=api('/games/history');assert history['statistics'][0]['total_plays']>=args.plays
 ws.send(json.dumps({'type':'ping'}))
 while json.loads(ws.recv(timeout=10))['type']!='pong':pass
report={'real_time_play':results,'initial_balance':start_balance,'after_reward_balance':end_balance,'after_shop_balance':purchase['state']['balance'],'websocket_via_proxy':'passed','duplicate_finish':'passed','history_persistence':'checked','world_entry':'walked connected A* grid path; no teleport'}
if args.output:Path(args.output).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
