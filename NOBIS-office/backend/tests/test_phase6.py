import uuid,json,time
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_server import client,login,headers,auth
from test_social import module,super_user,frames,channel,move_channel
from test_phase2 import until

def api(c,u,path,body=None,method=None):return c.request(method or ('POST' if body is not None else 'GET'),'/api/integration'+path,headers=headers(u),json=body)
def friend(c,a,b):
 r=c.post('/api/community/friend-requests',headers=headers(a),json={'user_id':b['user']['id']}).json()['requests'][0]['id'];c.post('/api/community/friend-requests/'+r,headers=headers(b),json={'action':'accept'})
def approve(c,a,b):
 api(c,a,'/home',{'access':'friends','capacity':5},'PUT');r=api(c,b,'/visits',{'user_id':a['user']['id']});assert r.status_code==200,r.text
 r=api(c,a,'/visits/'+r.json()['request_id'],{'accept':True});assert r.status_code==200,r.text

def test_home_approval_sync_acl_layout_chat_kick_and_block(client):
 admin=super_user(client);channel(client,admin);a,b,c=[login(client,n) for n in ('Owner','Visitor','Outsider')];friend(client,a,b)
 assert api(client,b,'/visits',{'user_id':a['user']['id']}).status_code==403
 from app.community.service import CommunityError
 with pytest.raises(CommunityError):module().integration.may_enter(b['user']['id'],a['user']['id'])
 with module().repository.connect() as db:assert db.execute('SELECT COUNT(*) FROM user_wallets WHERE user_id=?',(a['user']['id'],)).fetchone()[0]==0
 approve(client,a,b)
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb,client.websocket_connect('/ws') as wc:
  auth(wa,a);auth(wb,b);auth(wc,c);move_channel(wb,'ch2')
  wa.send_json({'type':'room_enter'});until(wa,'scope_changed')
  origin=module().hub.peers[b['user']['id']].player.copy();r=api(client,b,'/homes/'+a['user']['id']+'/enter',{});assert r.status_code==200,r.text
  until(wb,'scope_changed');scope='personal:'+a['user']['id']
  players=client.get('/api/users',headers=headers(b)).json();assert {p['id'] for p in players}=={a['user']['id'],b['user']['id']};assert next(p for p in players if p['id']==a['user']['id'])['x']!=0
  assert 'balance' not in client.get('/api/homes/'+scope,headers=headers(b)).json()
  assert client.put('/api/homes/'+scope+'/layout',headers=headers(b),json={'revision':0,'placements':[]}).status_code==403
  home=client.get('/api/home',headers=headers(a)).json();r=client.put('/api/homes/'+scope+'/layout',headers=headers(a),json={'revision':home['home']['revision'],'placements':[]});assert r.status_code==200,r.text
  assert until(wb,'home_layout')['map']['objects']
  p=module().hub.peers[b['user']['id']];p.move_credit=.8;wb.send_json({'type':'move','zone':'personal','scope':scope,'channel_id':p.player['channel_id'],'x':p.player['x']+.2,'y':p.player['y'],'moving':True,'direction':'east'});until(wa,'moved')
  wb.send_json({'type':'chat','channel':'zone:'+scope,'text':'집 안의 대화','mentions':[]});home_chat=until(wa,'chat')['chat'];assert home_chat['text']=='집 안의 대화'
  assert not any(m['id']==home_chat['id'] for m in client.get('/api/admin/messages',headers=headers(admin)).json())
  assert client.delete('/api/admin/messages/'+home_chat['id'],headers=headers(admin)).status_code==404
  assert not any(m.get('chat',{}).get('text')=='집 안의 대화' for m in frames(wc))
  api(client,a,'/homes/'+a['user']['id']+'/kick',{'user_id':b['user']['id']});until(wb,'scope_changed');assert p.player['scope']=='office' and p.player['x']==origin['x']
  assert api(client,b,'/homes/'+a['user']['id']+'/enter',{}).status_code==403
  approve(client,a,b);api(client,b,'/homes/'+a['user']['id']+'/enter',{});until(wb,'scope_changed')
  client.put('/api/community/blocks/'+b['user']['id'],headers=headers(a),json={'enabled':True});until(wb,'scope_changed');assert p.player['scope']=='office'


def test_visit_reject_capacity_disconnect_and_reconnect_revalidation(client):
 a,b=login(client,'A'),login(client,'B');friend(client,a,b);api(client,a,'/home',{'access':'invite_only','capacity':1},'PUT')
 rid=api(client,b,'/visits',{'user_id':a['user']['id']}).json()['request_id'];api(client,a,'/visits/'+rid,{'accept':False});assert not api(client,b,'').json()['home']['outgoing']
 approve(client,a,b);api(client,a,'/home',{'access':'friends','capacity':1},'PUT')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);wa.send_json({'type':'room_enter'});until(wa,'scope_changed');assert api(client,b,'/homes/'+a['user']['id']+'/enter',{}).status_code==409
  api(client,a,'/home',{'access':'friends','capacity':2},'PUT');api(client,b,'/homes/'+a['user']['id']+'/enter',{});until(wb,'scope_changed')
 with module().repository.connect() as c:assert c.execute('SELECT connected FROM home_visitors WHERE user_id=?',(b['user']['id'],)).fetchone()[0]==0
 api(client,a,'/home',{'access':'private','capacity':2},'PUT')
 with client.websocket_connect('/ws') as wb:assert next(p for p in auth(wb,b)['players'] if p['id']==b['user']['id'])['scope']=='office'

@pytest.fixture
def game_setup(client):
 a,b=login(client,'A'),login(client,'B');friend(client,a,b);t=[time.time()];module().integration.clock=lambda:t[0]
 return a,b,t

def session(c,a,b):
 r=module().integration.invite_game(a['user']['id'],b['user']['id'],str(uuid.uuid4()));return module().integration.accept_game(b['user']['id'],r['id'],True)
def solve(c,a,b,t,s):
 with module().repository.connect() as db:board=json.loads(db.execute('SELECT board FROM multiplayer_game_sessions WHERE id=?',(s['id'],)).fetchone()[0])
 for face in range(6):
  uid=s['turn_user_id'];u=a if uid==a['user']['id'] else b
  for card in [i for i,v in enumerate(board) if v==face]:
   r=api(c,u,'/games/'+s['id']+'/cards',{'card':card,'revision':s['revision'],'event_id':str(uuid.uuid4())});assert r.status_code==200,r.text;s=r.json()
  t[0]+=2
 return s

def test_server_cooperative_turn_privacy_idempotency_rewards_share_and_cancel(client,game_setup):
 a,b,t=game_setup;other=login(client,'Other');s=session(client,a,b);uid=a['user']['id'];sid=s['id'];before=client.get('/api/home',headers=headers(a)).json()['balance']
 assert s['cards']==[None]*12 and api(client,other,'/games/'+sid).status_code==404
 body={'card':0,'revision':0,'event_id':str(uuid.uuid4())}
 assert api(client,b,'/games/'+sid+'/cards',body).status_code==409
 r=api(client,a,'/games/'+sid+'/cards',body);assert r.status_code==200 and r.json()['cards'][0] is not None
 assert api(client,a,'/games/'+sid+'/cards',body).status_code==200
 assert api(client,a,'/games/'+sid+'/cards',{**body,'event_id':str(uuid.uuid4()),'revision':1}).status_code==409
 api(client,a,'/games/'+sid+'/cancel',{});s=session(client,a,b);t[0]+=10;s=solve(client,a,b,t,s);assert s['status']=='completed' and len(s['matched'])==12 and [r['amount'] for r in s['rewards']]==[25,25]
 assert client.get('/api/home',headers=headers(a)).json()['balance']==before+25
 api(client,a,'/games/'+s['id']+'/cancel',{});assert client.get('/api/home',headers=headers(a)).json()['balance']==before+25
 assert api(client,other,'/share/preview',{'kind':'multiplayer','target_id':s['id']}).status_code==404
 assert api(client,a,'/share/preview',{'kind':'multiplayer','target_id':s['id']}).status_code==200
 with module().repository.connect() as db:assert db.execute('SELECT COUNT(*) FROM multiplayer_game_rewards WHERE session_id=?',(s['id'],)).fetchone()[0]==2

def test_game_disconnect_expiry_reservation_and_day_cap(client,game_setup):
 a,b,t=game_setup;svc=module().integration;s=session(client,a,b)
 with pytest.raises(Exception):svc.invite_game(a['user']['id'],b['user']['id'],str(uuid.uuid4()))
 with pytest.raises(Exception):module().games.start(a['user']['id'],'whack-a-mole',str(uuid.uuid4()))
 svc.connection(b['user']['id'],False);t[0]+=29;assert svc.game_state(a['user']['id'],s['id'])['status']=='active';svc.connection(b['user']['id'],True)
 svc.connection(b['user']['id'],False);t[0]+=31;assert svc.game_state(a['user']['id'],s['id'])['status']=='disconnected'
 totals=[]
 for n in range(5):s=session(client,a,b);t[0]+=10;s=solve(client,a,b,t,s);totals.append(next(r['amount'] for r in s['rewards'] if r['user_id']==a['user']['id']))
 assert totals==[25,25,25,25,0]


def test_collection_coin_shop_flow_cumulative_and_no_direct_items(client):
 a=super_user(client);u=login(client);before=client.get('/api/home',headers=headers(u)).json();module().homes.initial_coins=0
 claim=client.post('/api/collectibles/attendance',headers=headers(u),json={});assert claim.json()['state']['balance']==1
 r=client.post('/api/collectibles/draws',headers=headers(u),json={'banner_id':'daily-coins','pool_version':1,'count':1,'request_id':str(uuid.uuid4())});assert r.status_code==200;r=r.json();assert r['state']['total_earned_coins']==r['draw']['total_coins'] and r['state']['coin_balance']==before['balance']+r['draw']['total_coins']
 after=client.get('/api/home',headers=headers(u)).json();assert after['inventory']==before['inventory']
 item=min(after['catalog'],key=lambda x:x['price']);p=client.post('/api/shop/purchases',headers=headers(u),json={'item_id':item['item_id'],'request_id':str(uuid.uuid4())});assert p.status_code==200
 collected=api(client,u,'/collection').json();entry=next(e for e in collected['entries'] if e['item_id']==item['item_id']);assert '상점 구매' in entry['sources'] and entry['quantity']>=1
 group=client.post('/api/community/groups',headers=headers(u),json={'name':'공유','description':'','visibility':'private','max_members':3}).json()
 count_before=len(client.get('/api/community/groups/'+group['id']+'/logs',headers=headers(u)).json()['items'])
 preview=api(client,u,'/share/preview',{'kind':'furniture','target_id':item['item_id']});assert preview.status_code==200
 assert len(client.get('/api/community/groups/'+group['id']+'/logs',headers=headers(u)).json()['items'])==count_before
 assert api(client,u,'/share',{'kind':'furniture','target_id':item['item_id'],'group_id':group['id']}).status_code==200
 assert api(client,a,'/share',{'kind':'collection','group_id':group['id']}).status_code==403
 assert api(client,u,'/share/preview',{'kind':'furniture','target_id':'fake'}).status_code==403
 assert client.get('/api/admin/integration',headers=headers(u)).status_code==403
 assert client.get('/api/admin/integration',headers=headers(a)).status_code==200


def test_multiplayer_reward_failure_rolls_back_final_pair(client,game_setup):
 a,b,t=game_setup;s=session(client,a,b);svc=module().integration
 with module().repository.connect() as c:
  board=json.loads(c.execute('SELECT board FROM multiplayer_game_sessions WHERE id=?',(s['id'],)).fetchone()[0]);last=[i for i,v in enumerate(board) if v==5];matched=[i for i,v in enumerate(board) if v!=5];c.execute('UPDATE multiplayer_game_sessions SET matched=?,selected=?,revision=11,started_at=? WHERE id=?',(json.dumps(matched),json.dumps([last[0]]),t[0]-20,s['id']))
 before=client.get('/api/home',headers=headers(a)).json()['balance']
 if module().repository.kind=='sqlite':
  import sqlite3
  with module().repository.connect() as c:c.execute("CREATE TRIGGER fail_mp BEFORE INSERT ON multiplayer_game_rewards BEGIN SELECT RAISE(ABORT,'injected'); END")
  exc=sqlite3.IntegrityError
 else:
  import psycopg
  with module().repository.connect() as c:c.execute('ALTER TABLE multiplayer_game_rewards ADD CONSTRAINT injected_failure CHECK (reason=\'never\')')
  exc=psycopg.errors.CheckViolation
 retry_key=str(uuid.uuid4())
 with pytest.raises(exc):svc.choose(a['user']['id'],s['id'],last[1],11,retry_key)
 assert svc.game_state(a['user']['id'],s['id'])['status']=='active' and client.get('/api/home',headers=headers(a)).json()['balance']==before
 with module().repository.connect() as c:
  if module().repository.kind=='sqlite':c.execute('DROP TRIGGER fail_mp')
  else:c.execute('ALTER TABLE multiplayer_game_rewards DROP CONSTRAINT injected_failure')
 assert svc.choose(a['user']['id'],s['id'],last[1],11,retry_key)['status']=='completed'
 assert client.get('/api/home',headers=headers(a)).json()['balance']==before+25
 svc.choose(a['user']['id'],s['id'],last[1],11,retry_key)
 assert client.get('/api/home',headers=headers(a)).json()['balance']==before+25


def test_concurrent_card_input_one_action(client,game_setup):
 a,b,t=game_setup;s=session(client,a,b);body={'card':0,'revision':0,'event_id':str(uuid.uuid4())}
 with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(lambda _:api(client,a,'/games/'+s['id']+'/cards',body),range(5)))
 assert all(r.status_code==200 for r in rows)
 with module().repository.connect() as c:assert c.execute('SELECT COUNT(*) FROM multiplayer_game_actions WHERE session_id=?',(s['id'],)).fetchone()[0]==1
 assert api(client,a,'/games/'+s['id']+'/cards',{**body,'event_id':str(uuid.uuid4())}).status_code==409


def test_cooperative_reconnect_restores_game_lock_and_grace(client,game_setup):
 a,b,t=game_setup;s=session(client,a,b)
 with client.websocket_connect('/ws') as wa:
  me=next(p for p in auth(wa,a)['players'] if p['id']==a['user']['id']);assert me['minigame']['game_id']=='coop-memory'
  assert client.get('/api/games/active',headers=headers(a)).json() is None
  assert module().hub.peers[a['user']['id']].player['minigame']['game_id']=='coop-memory'
 t[0]+=29
 with client.websocket_connect('/ws') as wa:
  me=next(p for p in auth(wa,a)['players'] if p['id']==a['user']['id']);assert me['minigame']['session_id']==s['id']
 t[0]+=31;assert module().integration.game_state(a['user']['id'],s['id'])['status']=='disconnected'
