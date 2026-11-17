import json,time,uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_server import client,login,auth,headers,place,near_object
from test_social import super_user,module,frames,channel
from test_phase2 import until
from app.games.service import GameService
from app.home import HomeService
from app.repository import Repository

def post(c,u,path,data=None):return c.post('/api/games'+path,headers=headers(u),json={} if data is None else data)
def state(c,u,sid):return c.get('/api/games/sessions/'+sid,headers=headers(u)).json()
def launch(c,u):
 place(u,*near_object('arcade'));r=post(c,u,'/sessions',{'game_id':'whack_a_mole','request_id':str(uuid.uuid4())});assert r.status_code==200,r.text;return r.json()
def body(s,**extra):
 m=s['mole'];return {'event_id':str(uuid.uuid4()),'cell':m['cell'] if m else 0,'wave':m['wave'] if m else -1,'challenge':m['challenge'] if m else '',**extra}
@pytest.fixture
def clock(client):
 value=[time.time()];module().games.clock=lambda:value[0];return value

def hits(c,u,s,clock,count):
 for i in range(count):
  clock[0]=s['started_at']+i*.8+.1;r=post(c,u,f"/sessions/{s['session_id']}/inputs",body(state(c,u,s['session_id'])));assert r.status_code==200 and r.json()['hit'],r.text
 clock[0]=s['expires_at']+.01
 return post(c,u,f"/sessions/{s['session_id']}/finish")

def test_catalog_entry_permission_and_single_active(client,clock):
 u=login(client);catalog=client.get('/api/games',headers=headers(u)).json();assert len(catalog)==3 and catalog[0]['available'] and not catalog[1]['available']
 assert post(client,u,'/sessions',{'game_id':'whack_a_mole','request_id':str(uuid.uuid4())}).status_code==403
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);place(u,*near_object('arcade'));ws.send_json({'type':'interact','object_id':'arcade'});assert until(ws,'interaction')['interaction']['kind']=='arcade'
  s=launch(client,u);assert s['config']['duration_ms']==30000 and 'seed' not in json.dumps(s)
  assert post(client,u,'/sessions',{'game_id':'whack_a_mole','request_id':str(uuid.uuid4())}).status_code==409
  assert module().hub.peers[u['user']['id']].player['minigame']['session_id']==s['session_id']

def test_forged_score_invalid_hits_duplicate_inputs_and_rate(client,clock):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);s=launch(client,u);sid=s['session_id'];b=body(s)
  assert post(client,u,f'/sessions/{sid}/inputs',{**b,'score':999999}).status_code==422
  assert post(client,u,f'/sessions/{sid}/finish',{'score':999999,'reward':999999}).status_code==422
  assert post(client,u,f'/sessions/{sid}/finish').status_code==409
  assert post(client,u,f'/sessions/{sid}/inputs',{**b,'challenge':'f'*56}).status_code==422
  hit=post(client,u,f'/sessions/{sid}/inputs',b);assert hit.status_code==200 and hit.json()['session']['score']==10
  replay=post(client,u,f'/sessions/{sid}/inputs',b).json();assert replay['replayed'] and replay['session']['score']==10
  assert post(client,u,f'/sessions/{sid}/inputs',{**b,'cell':(b['cell']+1)%9}).status_code==409
  assert post(client,u,f'/sessions/{sid}/inputs',{**b,'event_id':str(uuid.uuid4())}).status_code==429
  clock[0]+=.1;miss=post(client,u,f'/sessions/{sid}/inputs',{**b,'event_id':str(uuid.uuid4()),'cell':(b['cell']+1)%9}).json();assert not miss['hit'] and miss['session']['score']==10
  clock[0]+=.1;assert post(client,u,f'/sessions/{sid}/inputs',{**b,'wave':99,'event_id':str(uuid.uuid4())}).status_code==422
  clock[0]=s['expires_at']+.1;assert post(client,u,f'/sessions/{sid}/inputs',body(s)).status_code==409
  assert state(client,u,sid)['score']==10

@pytest.mark.parametrize('count,coins',[(0,0),(4,0),(5,10),(10,20),(15,30)])
def test_reward_thresholds_and_existing_wallet(client,clock,count,coins):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);s=launch(client,u);r=hits(client,u,s,clock,count);assert r.status_code==200,r.text;r=r.json();assert r['score']==count*10 and r['hits']==count and r['reward']==coins and r['balance']==1000+coins and r['reward_settled']
  assert post(client,u,f"/sessions/{s['session_id']}/finish").json()['balance']==1000+coins
  h=client.get('/api/games/history',headers=headers(u)).json();assert len(h['recent'])==1 and h['statistics'][0]['best_score']==count*10 and h['statistics'][0]['total_rewards']==coins
  home=client.get('/api/home',headers=headers(u)).json();assert len([t for t in home['transactions'] if t['kind']=='minigame_reward'])==1

def test_concurrent_finish_and_shop_spending(client,clock):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);s=launch(client,u);sid=s['session_id']
  for i in range(15):
   clock[0]=s['started_at']+.8*i+.1;assert post(client,u,f'/sessions/{sid}/inputs',body(state(client,u,sid))).json()['hit']
  clock[0]=s['expires_at']+.1
  with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:post(client,u,f'/sessions/{sid}/finish'),range(8)))
  assert all(r.status_code==200 and r.json()['reward']==30 and r.json()['balance']==1030 for r in results)
  p=client.post('/api/shop/purchases',headers=headers(u),json={'item_id':'furniture_plant_001','request_id':str(uuid.uuid4())});assert p.status_code==200 and p.json()['state']['balance']==990
  with module().repository.connect() as c:
   assert c.execute('SELECT COUNT(*) FROM game_reward_transactions WHERE session_id=?',(sid,)).fetchone()[0]==1
   assert c.execute("SELECT COUNT(*) FROM admin_audit_logs WHERE action='game_reward_paid' AND target_id=?",(sid,)).fetchone()[0]==1

def test_cancel_cooldown_owner_isolation(client,clock):
 a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as ws:
  auth(ws,a);s=launch(client,a);sid=s['session_id']
  for suffix in ('inputs','finish','cancel'):assert post(client,b,f'/sessions/{sid}/'+suffix,body(s) if suffix=='inputs' else {}).status_code==404
  assert client.get('/api/games/sessions/'+sid,headers=headers(b)).status_code==404
  r=post(client,a,f'/sessions/{sid}/cancel').json();assert r['status']=='cancelled' and r['reward']==0 and r['balance']==1000
  assert post(client,a,'/sessions',{'game_id':'whack_a_mole','request_id':str(uuid.uuid4())}).status_code==429
  clock[0]+=2.1;assert launch(client,a)['status']=='active'
  assert client.get('/api/games/history',headers=headers(b)).json()['recent']==[]

def test_world_freeze_chat_and_presence(client,clock):
 administrator=super_user(client);channel(client,administrator)
 a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);frames(wa);frames(wb);place(b,*near_object('arcade'));s=launch(client,a);assert any(m['type']=='status' and m['player'].get('minigame') for m in frames(wb))
  ax,ay,_=near_object('arcade');wa.send_json({'type':'move','scope':'office','zone':'lounge','channel_id':'ch1','x':ax+.1,'y':ay,'direction':'east','moving':True});assert until(wa,'correction')['x']==ax
  for message in [{'type':'room_enter'},{'type':'world_channel_move','channel_id':'ch2'},{'type':'interact','object_id':'arcade'}]:wa.send_json(message);until(wa,'error')
  from starlette.websockets import WebSocketDisconnect
  with client.websocket_connect('/ws') as denied:
   denied.send_json({'token':a['token'],'channel_id':'ch2'});assert denied.receive_json()['type']=='admission_denied'
   with pytest.raises(WebSocketDisconnect):denied.receive_json()
  assert module().hub.peers[a['user']['id']].player['channel_id']=='ch1'
  wb.send_json({'type':'chat','channel':'world','text':'게임 중에도 채팅'});assert until(wa,'chat')['chat']['text']=='게임 중에도 채팅'
  post(client,a,f"/sessions/{s['session_id']}/cancel");assert module().hub.peers[a['user']['id']].player['minigame'] is None

def test_admin_policy_rbac_cap_disabled_snapshot_and_audit(client,clock):
 admin=super_user(client);u=login(client,'player');setting={'enabled':True,'daily_cap':15,'rewards':[{'min_score':0,'coins':0},{'min_score':50,'coins':10},{'min_score':100,'coins':20},{'min_score':150,'coins':30}]}
 assert client.put('/api/admin/games/whack_a_mole',headers=headers(u),json=setting).status_code==403
 for path in ('games','game-rewards','game-sessions','game-alerts'):assert client.get('/api/admin/'+path,headers=headers(u)).status_code==403
 module().social.change_role(admin['user']['id'],u['user']['id'],'moderator')
 assert client.get('/api/admin/games',headers=headers(u)).status_code==200
 assert client.put('/api/admin/games/whack_a_mole',headers=headers(u),json=setting).status_code==403
 assert client.put('/api/admin/games/whack_a_mole',headers=headers(admin),json=setting).status_code==200
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);s=launch(client,u);r=hits(client,u,s,clock,15).json();assert r['reward']==15 and r['reward_reason']=='daily_cap'
  s=launch(client,u);r=hits(client,u,s,clock,15).json();assert r['reward']==0 and r['balance']==1015
  setting['enabled']=False;assert client.put('/api/admin/games/whack_a_mole',headers=headers(admin),json=setting).status_code==200
  assert post(client,u,'/sessions',{'game_id':'whack_a_mole','request_id':str(uuid.uuid4())}).status_code==409
 assert len(client.get('/api/admin/game-rewards',headers=headers(admin)).json())==2
 assert any(l['action']=='game_settings_changed' for l in client.get('/api/admin/logs',headers=headers(admin)).json())

def test_restart_expiry_and_idempotent_start(client,clock):
 admin=super_user(client);u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);place(u,*near_object('arcade'));b={'game_id':'whack_a_mole','request_id':str(uuid.uuid4())};s=post(client,u,'/sessions',b).json();assert post(client,u,'/sessions',b).json()['session_id']==s['session_id'];sid=s['session_id']
  repo=Repository(module().repository.path);repo.initialize();homes=HomeService(repo);homes.initialize();rebuilt=GameService(repo,homes,module().social,clock=lambda:clock[0]);rebuilt.initialize();assert rebuilt.active(u['user']['id'])['id']==sid
  setting={'enabled':False,'daily_cap':300,'rewards':[{'min_score':0,'coins':99}]};assert client.put('/api/admin/games/whack_a_mole',headers=headers(admin),json=setting).status_code==200
  assert hits(client,u,s,clock,5).json()['reward']==10
  assert rebuilt.state(u['user']['id'],sid)['reward']==10

def test_expired_claim_and_transaction_rollback(client,clock):
 u=login(client)
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);s=launch(client,u);sid=s['session_id'];clock[0]=s['expires_at']+301;assert state(client,u,sid)['status']=='expired' and module().games.active(u['user']['id']) is None
  s=launch(client,u);sid=s['session_id'];clock[0]=s['expires_at']+.1
  if module().repository.kind=='sqlite':
   import sqlite3
   with module().repository.connect() as c:c.execute("CREATE TRIGGER fail_reward BEFORE INSERT ON game_reward_transactions BEGIN SELECT RAISE(ABORT,'injected failure'); END")
   expected=sqlite3.IntegrityError
  else:
   import psycopg
   with module().repository.connect() as c:c.execute("ALTER TABLE game_reward_transactions ADD CONSTRAINT injected_failure CHECK (reason='never-valid')")
   expected=psycopg.errors.CheckViolation
  with pytest.raises(expected):module().games.finish(u['user']['id'],sid)
  with module().repository.connect() as c:
   assert c.execute('SELECT status FROM game_sessions WHERE id=?',(sid,)).fetchone()[0]=='active'
   assert c.execute('SELECT COUNT(*) FROM game_results WHERE session_id=?',(sid,)).fetchone()[0]==0
   assert c.execute("SELECT COUNT(*) FROM coin_transactions WHERE kind='minigame_reward'").fetchone()[0]==0
  assert module().homes.state(u['user']['id'])['balance']==1000
