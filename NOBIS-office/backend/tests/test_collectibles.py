import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_server import client,login,headers
from test_social import super_user,module

def get(c,u):return c.get('/api/collectibles/attendance',headers=headers(u)).json()
def claim(c,u,**kw):return c.post('/api/collectibles/attendance',headers=headers(u),json=kw)
def draw(c,u,n=1,key=None,**kw):
 banners=c.get('/api/collectibles/banners',headers=headers(u)).json();version=banners[0]['current_version'] if banners else 1
 return c.post('/api/collectibles/draws',headers=headers(u),json={'banner_id':'daily-coins','pool_version':version,'count':n,'request_id':key or str(uuid.uuid4()),**kw})
def grant(c,a,u,n=5,key=None):return c.post('/api/admin/collectibles/grants',headers=headers(a),json={'user_id':u['user']['id'],'tickets':n,'request_id':key or str(uuid.uuid4())})
@pytest.fixture
def clock(client):
 t=[datetime.fromisoformat('2026-11-06T23:59:59+09:00').timestamp()];module().collectibles.clock=lambda:t[0];return t

def test_attendance_kst_once_streak_and_gap(client,clock):
 u=login(client);assert get(client,u)['balance']==0
 assert claim(client,u,attendance_date='2026-11-07').status_code==422
 assert claim(client,u).json()['state']['balance']==1
 assert claim(client,u).json()['replayed'] and get(client,u)['total_days']==1
 clock[0]+=2;s=claim(client,u).json()['state'];assert s['today']=='2026-11-07' and s['streak']==2 and s['balance']==2
 clock[0]+=2*86400;assert get(client,u)['streak']==0;s=claim(client,u).json()['state'];assert s['streak']==1 and s['total_days']==3
 clock[0]=datetime.fromisoformat('2026-12-01T00:00:00+09:00').timestamp();assert claim(client,u).json()['state']['month']=='2026-12'
 assert len(client.get('/api/collectibles/attendance?month=2026-11',headers=headers(u)).json()['calendar'])==3
 assert client.get('/api/collectibles/attendance').status_code==401

def test_concurrent_claim_once(client,clock):
 u=login(client)
 with ThreadPoolExecutor(max_workers=8) as p:rows=list(p.map(lambda _:claim(client,u),range(8)))
 assert all(r.status_code==200 for r in rows) and sum(not r.json()['replayed'] for r in rows)==1 and get(client,u)['balance']==1

def test_single_draw_coin_credit_inventory_unchanged_and_ownership(client,clock):
 u=login(client);home=client.get('/api/home',headers=headers(u)).json();assert draw(client,u).status_code==409;claim(client,u);key=str(uuid.uuid4());r=draw(client,u,key=key);assert r.status_code==200,r.text;d=r.json()['draw'];assert len(d['items'])==1 and get(client,u)['balance']==0
 after=client.get('/api/home',headers=headers(u)).json();assert after['inventory']==home['inventory'] and after['balance']==home['balance']+d['total_coins'] and 10<=d['total_coins']<=1000
 assert draw(client,u,key=key).json()['replayed'] and draw(client,u,5,key).status_code==409 and draw(client,u,winner='fake').status_code==422
 other=login(client,'other');assert client.get('/api/collectibles/draws/'+d['id'],headers=headers(other)).status_code==404

@pytest.mark.parametrize('same_key',[True,False])
def test_five_draws_concurrency_and_idempotency(client,clock,same_key):
 a=super_user(client);u=login(client);grant(client,a,u);before=client.get('/api/home',headers=headers(u)).json();key=str(uuid.uuid4())
 with ThreadPoolExecutor(max_workers=8) as p:rows=list(p.map(lambda _:draw(client,u,5,key if same_key else None),range(8)))
 good=[r for r in rows if r.status_code==200];assert len(good)==(8 if same_key else 1) and len({r.json()['draw']['id'] for r in good})==1
 assert len(good[0].json()['draw']['items'])==5 and get(client,u)['balance']==0 and client.get('/api/home',headers=headers(u)).json()['inventory']==before['inventory'] and client.get('/api/home',headers=headers(u)).json()['balance']==before['balance']+good[0].json()['draw']['total_coins']

def test_pool_weights_versions_duplicate_items_and_rbac(client,clock,monkeypatch):
 a=super_user(client);u=login(client);b=client.get('/api/collectibles/banners',headers=headers(u)).json()[0];assert sum(i['weight_bps'] for i in b['items'])==10000 and b['rarity_weights']=={'coin':10000} and len(b['items'])==100
 body={k:b[k] for k in ('name','description','rarity_weights')};body.update(enabled=True,items=[{k:i[k] for k in ('coin_amount','weight_bps')} for i in b['items']]);path='/api/admin/collectibles/banners/daily-coins'
 assert client.put(path,headers=headers(u),json=body).status_code==403
 bad={**body,'items':[{**i,'weight_bps':i['weight_bps']+1} for i in body['items']]};assert client.put(path,headers=headers(a),json=bad).status_code==422
 grant(client,a,u,6);monkeypatch.setattr('app.collectibles.service.secrets.randbelow',lambda n:n-1);d=draw(client,u).json()['draw']
 body['items']=[{'coin_amount':1000,'weight_bps':10000}];body['rarity_weights']={'coin':10000};assert client.put(path,headers=headers(a),json=body).status_code==200
 assert draw(client,u,pool_version=1).status_code==409 and get(client,u)['balance']==5
 r=draw(client,u,5).json()['draw'];assert r['pool_version']==2 and all(i['coin_amount']==1000 for i in r['items']) and len({i['coin_transaction_id'] for i in r['items']})==5 and r['total_coins']==5000
 old=client.get('/api/collectibles/draws/'+d['id'],headers=headers(u)).json();assert old['pool_version']==1 and old['rarity_weights']=={'coin':10000} and len(old['probabilities'])==100
 body['enabled']=False;client.put(path,headers=headers(a),json=body);assert draw(client,u).status_code==404
 assert client.get('/api/admin/collectibles',headers=headers(u)).status_code==403

def test_reward_settings_grant_retry_and_service_restart(client,clock):
 from app.repository import Repository
 from app.home import HomeService
 from app.collectibles.service import CollectibleService
 a=super_user(client);u=login(client);key=str(uuid.uuid4());grant(client,a,u,5,key);grant(client,a,u,5,key);assert get(client,u)['balance']==5 and grant(client,a,u,6,key).status_code==409
 client.put('/api/admin/collectibles/attendance',headers=headers(a),json={'reward_tickets':2});assert claim(client,u).json()['state']['balance']==7
 client.put('/api/admin/collectibles/attendance',headers=headers(a),json={'reward_tickets':10});assert claim(client,u).json()['state']['balance']==7
 repo=Repository(module().repository.path);repo.initialize();h=HomeService(repo);h.initialize();svc=CollectibleService(repo,h,module().social,clock=lambda:clock[0]);svc.initialize();assert svc.status(u['user']['id'])['balance']==7
 assert {'tickets_granted','attendance_reward_changed','attendance_ticket_issued'}<={l['action'] for l in client.get('/api/admin/logs',headers=headers(a)).json()}

@pytest.mark.parametrize('kind',['draw','attendance'])
def test_failure_rolls_back_entire_transaction(client,clock,kind):
 a=super_user(client);u=login(client);grant(client,a,u,5);before=client.get('/api/home',headers=headers(u)).json();table='gacha_coin_draw_items' if kind=='draw' else 'ticket_transactions'
 if module().repository.kind=='sqlite':
  import sqlite3
  with module().repository.connect() as c:c.execute('CREATE TRIGGER fail_collectibles BEFORE INSERT ON '+table+" BEGIN SELECT RAISE(ABORT,'injected failure'); END")
  expected=sqlite3.IntegrityError
 else:
  import psycopg
  with module().repository.connect() as c:c.execute('ALTER TABLE '+table+" ADD CONSTRAINT injected_failure CHECK ("+('position<0' if kind=='draw' else "kind<>'attendance'")+')')
  expected=psycopg.errors.CheckViolation
 with pytest.raises(expected):
  if kind=='draw':module().collectibles.draw(u['user']['id'],'daily-coins',5,str(uuid.uuid4()))
  else:module().collectibles.claim(u['user']['id'])
 assert get(client,u)['balance']==5 and not get(client,u)['claimed_today'] and client.get('/api/home',headers=headers(u)).json()['inventory']==before['inventory'] and client.get('/api/home',headers=headers(u)).json()['balance']==before['balance']


def test_normal_distribution_exact_symmetric_and_rng_endpoints(client,clock,monkeypatch):
 from app.collectibles.service import COIN_POOL
 assert len(COIN_POOL)==100 and sum(i['weight_bps'] for i in COIN_POOL)==10000
 assert [i['coin_amount'] for i in COIN_POOL]==list(range(10,1001,10))
 w=[i['weight_bps'] for i in COIN_POOL];assert w==list(reversed(w)) and all(a<=b for a,b in zip(w[:49],w[1:50]))
 assert w[0]==3 and w[49]==242 and sum(i['coin_amount']*i['weight_bps'] for i in COIN_POOL)==5050000
 a=super_user(client);u=login(client);grant(client,a,u,2)
 monkeypatch.setattr('app.collectibles.service.secrets.randbelow',lambda n:0);assert draw(client,u).json()['draw']['total_coins']==10
 monkeypatch.setattr('app.collectibles.service.secrets.randbelow',lambda n:n-1);r=draw(client,u).json()['draw'];assert r['total_coins']==1000
 home=client.get('/api/home',headers=headers(u)).json();tx=[t for t in home['transactions'] if t['kind']=='gacha_reward'];assert sorted(t['amount'] for t in tx)==[10,1000]
 assert draw(client,u,coin_amount=1000).status_code==422

@pytest.mark.parametrize('amount',[0,11,1001])
def test_coin_config_amount_constraints(client,amount):
 a=super_user(client);body={'name':'invalid','description':'','enabled':True,'rarity_weights':{'coin':10000},'items':[{'coin_amount':amount,'weight_bps':10000}]}
 assert client.put('/api/admin/collectibles/banners/invalid',headers=headers(a),json=body).status_code==422


def test_legacy_furniture_receipt_preserved_and_banner_closed(client):
 import time,json
 from app.collectibles.service import CollectibleService
 u=login(client);uid=u['user']['id'];svc=module().collectibles;svc.homes.ensure(uid);iid=str(uuid.uuid4());did=str(uuid.uuid4())
 with module().repository.connect() as c:
  c.execute('BEGIN IMMEDIATE');c.execute("INSERT INTO gacha_banners VALUES ('legacy-furniture','이전 가구','',1,1,?)",(time.time(),))
  c.execute("INSERT INTO gacha_pool_versions VALUES ('legacy-furniture',1,?,?)",(json.dumps({'common':10000}),time.time()))
  c.execute("INSERT INTO gacha_pool_items VALUES ('legacy-furniture',1,'furniture_chair_001','common',10000)")
  c.execute("INSERT INTO furniture_instances(id,owner_id,item_id) VALUES (?,?,'furniture_chair_001')",(iid,uid))
  c.execute("INSERT INTO gacha_draws VALUES (?,?,'legacy-furniture',1,1,?,?)",(did,uid,str(uuid.uuid4()),time.time()))
  c.execute("INSERT INTO gacha_draw_items VALUES (?,0,'furniture_chair_001',?,'common')",(did,iid))
 before=svc.homes.state(uid)
 svc.initialize();r=svc.receipt(uid,did);assert r['reward_type']=='furniture' and r['items'][0]['instance_id']==iid
 assert all(b['reward_type']=='coin' for b in svc.banners()) and svc.homes.state(uid)['inventory']==before['inventory']
 assert draw(client,u,banner_id='legacy-furniture').status_code==404
