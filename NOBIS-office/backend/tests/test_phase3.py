import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_server import client,login,auth,headers
from test_phase2 import until
from app.home import HomeService,HomeError,validate_layout,footprint,CATALOG_BY_ID
from app.repository import Repository
from app.world import walkable

def home(c,u):return c.get('/api/home',headers=headers(u)).json()
def buy(c,u,item='furniture_plant_001',key=None,**extra):return c.post('/api/shop/purchases',headers=headers(u),json={'item_id':item,'request_id':key or str(uuid.uuid4()),**extra})
def payload(s,placements=None):return {'revision':s['home']['revision'],'placements':[{k:p[k] for k in ('instance_id','grid_x','grid_y','rotation')} for p in (s['placements'] if placements is None else placements)]}
def save(c,u,s,placements=None):return c.put(f"/api/homes/{s['home']['id']}/layout",headers=headers(u),json=payload(s,placements))
def unplaced(s,cat):return next(i for i in s['inventory'] if i['item_id']==f'furniture_{cat}_001' and i['id'] not in {p['instance_id'] for p in s['placements']})

def test_home_identity_seed_and_acl(client):
 a,b=login(client,'A'),login(client,'B');sa,sb=home(client,a),home(client,b)
 assert sa['home']['id']!=sb['home']['id'] and sa['balance']==1000 and len(sa['catalog'])==10
 assert len(sa['inventory'])==8 and len(sa['placements'])==6
 assert not ({i['id'] for i in sa['inventory']}&{i['id'] for i in sb['inventory']})
 assert home(client,a)['inventory']==sa['inventory'] and len(home(client,a)['transactions'])==1
 assert client.get(f"/api/homes/{sa['home']['id']}",headers=headers(b)).status_code==403
 assert client.put(f"/api/homes/{sa['home']['id']}/layout",headers=headers(b),json=payload(sb)).status_code==403
 assert save(client,a,sa).status_code==403 and client.get('/api/home').status_code==401

def test_purchase_idempotency_and_balance(client):
 u=login(client);key=str(uuid.uuid4());first=buy(client,u,key=key).json()
 assert first['state']['balance']==960 and len(first['state']['inventory'])==9
 replay=buy(client,u,key=key).json();assert replay['replayed'] and replay['receipt']['instance_id']==first['receipt']['instance_id']
 assert replay['state']['balance']==960 and len(replay['state']['inventory'])==9 and len(replay['state']['transactions'])==2
 assert buy(client,u,'furniture_chair_001',key).status_code==409
 assert buy(client,u,'fake_item').status_code==404
 assert buy(client,u,price=0).status_code==422 and buy(client,u,balance=999999).status_code==422
 for _ in range(4):assert buy(client,u,'furniture_computer_001').status_code==200
 before=home(client,u);assert before['balance']==160
 assert buy(client,u,'furniture_computer_001').status_code==409
 after=home(client,u);assert after['balance']==160 and len(after['inventory'])==len(before['inventory'])
 assert sum(t['amount'] for t in after['transactions'])==after['balance']

def test_layout_rotate_move_recall_collision_reconnect(client):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);ws.send_json({'type':'room_enter'});until(ws,'scope_changed');s=home(client,u)
  desk=unplaced(s,'desk');p={'instance_id':desk['id'],'grid_x':2,'grid_y':5,'rotation':90}
  r=save(client,u,s,s['placements']+[p]);assert r.status_code==200,r.text
  saved=r.json();assert saved['home']['revision']==1
  m=saved['map'];assert not walkable(u['home_id'],2,5,m) and not walkable(u['home_id'],2,6,m) and walkable(u['home_id'],3,5,m)
  p.update(grid_x=3,grid_y=5,rotation=0)
  moved=save(client,u,saved,s['placements']+[p]);assert moved.status_code==200,moved.text
  recalled=save(client,u,moved.json(),s['placements']);assert recalled.status_code==200
  assert len(recalled.json()['inventory'])==8 and len(recalled.json()['placements'])==6
  assert walkable(u['home_id'],3,5,recalled.json()['map'])
 with client.websocket_connect('/ws') as ws:
  snap=auth(ws,u);assert snap['home_state']['home']['revision']==3

def test_layout_invalid_inputs_rollback_and_owner_checks(client):
 a,b=login(client,'A'),login(client,'B');sa,sb=home(client,a),home(client,b)
 with client.websocket_connect('/ws') as ws:
  auth(ws,a);ws.send_json({'type':'room_enter'});until(ws,'scope_changed')
  base={'instance_id':unplaced(sa,'desk')['id'],'grid_x':2,'grid_y':5,'rotation':0}
  invalid=[sa['placements']+[sa['placements'][0]],sa['placements']+[{**base,'instance_id':sb['inventory'][0]['id']}]]
  for x,y,rotation in [(-1,5,0),(11,5,0),(10,7,0),(10,8,0),(6,7,0),(3,3,0),(2,5,45)]:invalid.append(sa['placements']+[{**base,'grid_x':x,'grid_y':y,'rotation':rotation}])
  for placements in invalid:assert save(client,a,sa,placements).status_code in (403,422)
  assert home(client,a)['home']['revision']==0 and len(home(client,a)['placements'])==6
  body=payload(sa);body['placements'][0]['owner_id']=b['user']['id']
  assert client.put(f"/api/homes/{sa['home']['id']}/layout",headers=headers(a),json=body).status_code==422
  assert client.put('/api/homes/office/layout',headers=headers(a),json=payload(sa)).status_code==403

def test_avatar_overlap_revision_and_spectator(client):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);ws.send_json({'type':'room_enter'});until(ws,'scope_changed');s=home(client,u)
  import app.main as mod
  mod.hub.peers[u['user']['id']].player.update(x=2,y=5)
  p={'instance_id':unplaced(s,'desk')['id'],'grid_x':2,'grid_y':5,'rotation':0}
  assert save(client,u,s,s['placements']+[p]).status_code==422
  assert save(client,u,s).status_code==200 and save(client,u,s).status_code==409
  ws.send_json({'type':'status','work_status':'after_work','message':''});until(ws,'status')
  assert save(client,u,home(client,u)).status_code==403

def test_dynamic_movement_collision_and_exit(client):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);ws.send_json({'type':'room_enter'});until(ws,'scope_changed')
  import app.main as mod
  peer=mod.hub.peers[u['user']['id']];peer.player.update(x=4,y=3);peer.moved-=1;peer.move_credit=.8
  ws.send_json({'type':'move','scope':u['home_id'],'zone':'personal','x':4.6,'y':3,'direction':'east','moving':True})
  assert until(ws,'correction')['x']==4
  peer.player.update(x=10,y=7);ws.send_json({'type':'interact','object_id':'home-exit'});assert until(ws,'scope_changed')['player']['scope']=='office'

def test_connectivity_and_rotated_footprint():
 item=CATALOG_BY_ID['furniture_desk_001'];assert footprint(item,2,5,90)=={(2,5),(2,6)}
 instances={str(i):CATALOG_BY_ID['furniture_chair_001'] for i in range(12)}
 placements=[{'instance_id':str(i),'grid_x':x,'grid_y':4,'rotation':0} for i,x in enumerate(range(12))]
 with pytest.raises(HomeError,match='통로'):validate_layout(placements,instances)

def test_concurrent_retries_and_insufficient_balance(tmp_path):
 repo=Repository(str(tmp_path/'race.sqlite3'));repo.initialize();svc=HomeService(repo,100);svc.initialize();_,user=repo.create_user('Concurrent');uid=user['id'];svc.ensure(uid);key=str(uuid.uuid4())
 with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:svc.purchase(uid,'furniture_plant_001',key),range(8)))
 assert len({r['receipt']['instance_id'] for r in results})==1 and svc.state(uid)['balance']==60
 def attempt(_):
  try:return svc.purchase(uid,'furniture_plant_001',str(uuid.uuid4()))
  except HomeError:return None
 with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(8)))
 assert sum(r is not None for r in results)==1 and svc.state(uid)['balance']==20 and len(svc.state(uid)['inventory'])==10

def test_phase3_backup_and_persistence(tmp_path):
 path=tmp_path/'old.sqlite3';repo=Repository(str(path));repo.initialize();svc=HomeService(repo);svc.initialize();token,u=repo.create_user('Legacy');svc.ensure(u['id']);svc.purchase(u['id'],'furniture_plant_001',str(uuid.uuid4()))
 with repo.connect() as c:c.execute('DELETE FROM schema_migrations WHERE version=3')
 repo.initialize();svc=HomeService(repo);svc.initialize();s=svc.state(u['id'])
 assert s['balance']==960 and len(s['inventory'])==9 and repo.user_for(token)['id']==u['id']
 assert path.with_name('old.sqlite3.pre-phase3.bak').exists()
 with repo.connect() as c:assert c.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=3').fetchone()[0]==1

def test_purchase_failure_rolls_back_charge_and_item(tmp_path):
 import sqlite3
 repo=Repository(str(tmp_path/'rollback.sqlite3'));repo.initialize();svc=HomeService(repo);svc.initialize();_,u=repo.create_user('Rollback');uid=u['id'];before=svc.state(uid)
 with repo.connect() as c:c.execute("CREATE TRIGGER fail_purchase BEFORE INSERT ON shop_purchases BEGIN SELECT RAISE(ABORT,'injected write failure'); END")
 with pytest.raises(sqlite3.IntegrityError):svc.purchase(uid,'furniture_plant_001',str(uuid.uuid4()))
 after=svc.state(uid);assert after['balance']==before['balance'] and after['inventory']==before['inventory'] and len(after['transactions'])==1

def test_network_burst_uses_accumulated_move_credit(client):
 from test_server import place
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);place(u,5,10,'focus')
  for x in (5.3,5.6):
   ws.send_json({'type':'move','scope':'office','zone':'focus','x':x,'y':10,'direction':'east','moving':True});assert until(ws,'moved')['player']['x']==x
  # Receiving a short network burst must not bypass the aggregate speed limit.
  ws.send_json({'type':'move','scope':'office','zone':'focus','x':19.3,'y':10,'direction':'east','moving':True});assert until(ws,'correction')['x']==5.6
