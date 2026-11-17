import importlib
import json
from contextlib import ExitStack
import pytest
from fastapi.testclient import TestClient
from test_server import client,login,auth,headers,place
from test_phase2 import until,drain
from app.social import SocialService,SocialError
from app.cli import main as cli

def module():return importlib.import_module('app.main')
def super_user(c):
 u=login(c,'Super');module().social.bootstrap(u['user']['id']);return u

def channel(c,admin,cid='ch2',capacity=15):
 r=c.post('/api/admin/channels',headers=headers(admin),json={'id':cid,'name':cid,'capacity':capacity,'enabled':True});assert r.status_code==200,r.text

def frames(ws):
 ws.send_json({'type':'ping'});result=[]
 while True:
  m=ws.receive_json()
  if m['type']=='pong':return result
  result.append(m)

def move_channel(ws,cid):ws.send_json({'type':'world_channel_move','channel_id':cid});return until(ws,'snapshot')

def test_channel_avatar_position_and_zone_isolation(client):
 admin=super_user(client);channel(client,admin);a,b,c=login(client,'A'),login(client,'B'),login(client,'C')
 with ExitStack() as stack:
  wa,wb,wc=[stack.enter_context(client.websocket_connect('/ws')) for _ in range(3)]
  for ws,u in [(wa,a),(wb,b),(wc,c)]:auth(ws,u)
  for ws in (wa,wb,wc):frames(ws)
  snap=move_channel(wb,'ch2');assert [p['id'] for p in snap['players']]==[b['user']['id']]
  assert until(wa,'left')['id']==b['user']['id'];frames(wa);frames(wc);frames(wb)
  place(b,5,10,'focus');wb.send_json({'type':'move','channel_id':'ch2','scope':'office','zone':'fake','x':5.2,'y':10,'direction':'east','moving':True});until(wb,'moved')
  assert not any(m['type'] in ('moved','zone_changed') for m in frames(wa))
  assert {p['id'] for p in client.get('/api/users',headers=headers(a)).json()}=={a['user']['id'],c['user']['id']}
  wa.send_json({'type':'chat','channel':'zone:ch2:focus','text':'forbidden'});until(wa,'error')
  place(a,5,10,'focus');wa.send_json({'type':'chat','channel':'zone:focus','text':'channel1 only'});until(wa,'chat');assert not any(m['type']=='chat' for m in frames(wb))
  wb.send_json({'type':'chat','channel':'channel:ch1','text':'cross-channel write'});until(wb,'error')

def test_channel_capacity_atomic_switch_and_saved_reconnect(client):
 admin=super_user(client);channel(client,admin,capacity=1);a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);frames(wa);move_channel(wb,'ch2');frames(wa)
  place(a,5,10,'focus');wa.send_json({'type':'world_channel_move','channel_id':'ch2'});until(wa,'error');assert module().hub.peers[a['user']['id']].player['channel_id']=='ch1'
  assert module().repository.presence_for(a['user']['id'])['channel_id']=='ch1'
  channels=client.get('/api/world-channels',headers=headers(a)).json();assert next(c for c in channels if c['id']=='ch2')['online']==1
  assert client.put('/api/admin/channels/ch2',headers=headers(admin),json={'id':'ch2','name':'ch2','capacity':1,'enabled':False}).status_code==409
  move_channel(wb,'ch1');wa.send_json({'type':'status','work_status':'focusing','message':'saved'});until(wa,'status')
  snap=move_channel(wa,'ch2');p=next(p for p in snap['players'] if p['id']==a['user']['id']);assert p['work_status']=='focusing'
  snap=move_channel(wa,'ch1');p=next(p for p in snap['players'] if p['id']==a['user']['id']);assert (p['x'],p['y'])==(5,10)
  move_channel(wa,'ch2')
 with client.websocket_connect('/ws') as ws:
  s=auth(ws,a);assert s['world_channel_id']=='ch2' and s['players'][0]['message']=='saved'

def test_whisper_cross_channel_private_only_and_offline_reconnect(client):
 admin=super_user(client);channel(client,admin);a,b,c=login(client,'Alice'),login(client,'Bob'),login(client,'Other')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb,client.websocket_connect('/ws') as wc:
  auth(wa,a);auth(wb,b);auth(wc,c);frames(wa);frames(wb);move_channel(wb,'ch2');frames(wa);frames(wc)
  wa.send_json({'type':'private_message','text':'@Bob cross-channel secret','recipient_id':b['user']['id']})
  m=until(wa,'private_message')['chat'];assert m['delivery']=='delivered' and m['text']=='cross-channel secret'
  assert until(wb,'private_message')['chat']['id']==m['id']
  assert not any('secret' in str(m) for m in frames(wc))
  assert client.get('/api/private-messages',headers=headers(c)).json()==[]
  assert len(client.get('/api/private-messages',headers=headers(b)).json())==1
 with client.websocket_connect('/ws') as wa:
  auth(wa,a);wa.send_json({'type':'private_message','text':'@Bob offline letter'})
  msg=until(wa,'private_message')['chat'];assert msg['delivery']=='stored'
  with client.websocket_connect('/ws') as wb:
   s=auth(wb,b);assert any(m['id']==msg['id'] and m['delivery']=='delivered' for m in s['private_messages'])
   assert until(wa,'private_delivered')['id']==msg['id']

def test_whisper_unknown_duplicate_and_explicit_recipient(client):
 a,b,c=login(client,'Sender'),login(client,'Same'),login(client,'Same')
 with client.websocket_connect('/ws') as ws:
  auth(ws,a)
  for text in ['@Unknown body','@Same ambiguous']:
   ws.send_json({'type':'private_message','text':text});until(ws,'error')
  assert client.get('/api/private-messages',headers=headers(a)).json()==[]
  ws.send_json({'type':'private_message','recipient_id':b['user']['id'],'text':'@Same exact ID'});m=until(ws,'private_message')['chat'];assert m['recipient_id']==b['user']['id']
  assert client.get('/api/private-messages',headers=headers(c)).json()==[]

def test_chat_bubble_preferences_zone_rules_and_privacy(client):
 a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);frames(wa);frames(wb)
  assert client.put('/api/chat-preferences',headers=headers(a),json={'chat_bubbles_enabled':True}).status_code==200;until(wa,'chat_preferences')
  for zone,pos,expected in [('cafe',(10,10),True),('focus',(5,10),False),('meeting',(3,3),False)]:
   place(a,*pos,zone);pa=module().hub.peers[a['user']['id']].player;module().hub.peers[b['user']['id']].player.update(module().rooms.plan(module().hub.peers[b['user']['id']].player,zone,pa['room_id'] if zone=='meeting' else None)) if zone!='meeting' else None
   if zone=='meeting':
    module().repository.invite(pa['room_id'],a['user']['id'],b['user']['id']);module().repository.accept(pa['room_id'],b['user']['id']);module().hub.peers[b['user']['id']].player.update(module().rooms.plan(module().hub.peers[b['user']['id']].player,zone,pa['room_id']))
   module().hub.peers[a['user']['id']].chatted=0
   wa.send_json({'type':'chat','channel':'world','text':zone+' public'});until(wa,'chat');data=frames(wb)
   bubbles=[m for m in data if m['type']=='chat_bubble'];assert bool(bubbles)==expected
   frames(wa)
  place(a,10,10,'cafe');module().hub.peers[a['user']['id']].chatted=0
  wa.send_json({'type':'private_message','recipient_id':b['user']['id'],'text':'@B no bubble'});until(wa,'private_message');assert not any(m['type']=='chat_bubble' for m in frames(wb))
  client.put('/api/chat-preferences',headers=headers(a),json={'chat_bubbles_enabled':False});until(wa,'chat_preferences');frames(wa);frames(wb);module().hub.peers[a['user']['id']].chatted=0
  wa.send_json({'type':'chat','channel':'world','text':'off'});until(wa,'chat');assert not any(m['type']=='chat_bubble' for m in frames(wb))
 assert client.get('/api/chat-preferences',headers=headers(a)).json()['chat_bubbles_enabled'] is False

def test_global_channel_announcements_and_history_separation(client):
 admin=super_user(client);channel(client,admin);a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);frames(wa);move_channel(wb,'ch2');frames(wa);frames(wb)
  assert client.post('/api/admin/announcements',headers=headers(a),json={'title':'fake','text':'bad'}).status_code==403
  client.post('/api/admin/announcements',headers=headers(admin),json={'title':'All','text':'global'})
  assert until(wa,'announcement')['announcement']['title']=='All';assert until(wb,'announcement')['announcement']['title']=='All'
  client.post('/api/admin/announcements',headers=headers(admin),json={'title':'Only 2','text':'target','target_channel_id':'ch2'})
  assert until(wb,'announcement')['announcement']['title']=='Only 2';assert not any(m['type']=='announcement' for m in frames(wa))
  assert len(client.get('/api/announcements',headers=headers(a)).json())==1 and len(client.get('/api/announcements',headers=headers(b)).json())==2
  assert not any('global' in m['text'] for m in module().repository.history('world'))

def test_rbac_role_escalation_last_super_and_audits(client):
 s=super_user(client);a,m,u=login(client,'Admin'),login(client,'Mod'),login(client,'User')
 assert client.put(f"/api/admin/users/{a['user']['id']}/role",headers=headers(s),json={'role':'admin'}).status_code==200
 assert client.put(f"/api/admin/users/{m['user']['id']}/role",headers=headers(a),json={'role':'moderator'}).status_code==200
 assert client.put(f"/api/admin/users/{u['user']['id']}/role",headers=headers(a),json={'role':'admin'}).status_code==403
 assert client.put(f"/api/admin/users/{u['user']['id']}/role",headers=headers(m),json={'role':'moderator'}).status_code==403
 assert client.put(f"/api/admin/users/{s['user']['id']}/role",headers=headers(s),json={'role':'user'}).status_code==409
 for section in ['dashboard','online','channels','announcements','users','roles','logs','reports','messages']:assert client.get('/api/admin/'+section,headers=headers(u)).status_code==403
 assert client.get('/api/admin/reports',headers=headers(m)).status_code==200 and client.get('/api/admin/users',headers=headers(m)).status_code==403
 logs=client.get('/api/admin/logs',headers=headers(s)).json();assert sum(r['action']=='role_changed' for r in logs)==2 and any(r['action']=='bootstrap_super_admin' for r in logs)
 assert client.post('/api/dev-login',json={'nickname':'Injection','role':'super_admin'}).json()['user']['role']=='user'

def test_reports_mute_delete_and_disabled_account(client):
 admin=super_user(client);u=login(client,'User')
 client.post('/api/reports',headers=headers(u),json={'target_id':admin['user']['id'],'reason':'test report'})
 reports=client.get('/api/admin/reports',headers=headers(admin)).json();assert len(reports)==1
 assert client.put('/api/admin/reports/'+reports[0]['id'],headers=headers(admin),json={'status':'resolved'}).status_code==200
 with client.websocket_connect('/ws') as ws:
  auth(ws,u);ws.send_json({'type':'chat','channel':'world','text':'moderate this'});mid=until(ws,'chat')['chat']['id']
  assert client.delete('/api/admin/messages/'+mid,headers=headers(admin)).status_code==200;until(ws,'message_deleted')
  assert client.put(f"/api/admin/users/{u['user']['id']}/mute",headers=headers(admin),json={'minutes':10,'reason':'test'}).status_code==200
  ws.send_json({'type':'chat','channel':'world','text':'muted'});until(ws,'error')
  assert client.put(f"/api/admin/users/{u['user']['id']}/mute",headers=headers(admin),json={'minutes':0,'reason':'release'}).status_code==200
 assert client.put(f"/api/admin/users/{u['user']['id']}/disabled",headers=headers(admin),json={'disabled':True}).status_code==200
 assert client.get('/api/me',headers=headers(u)).status_code==401

def test_cli_bootstrap_production_login_backup_restore(tmp_path,monkeypatch,capsys):
 path=tmp_path/'operator.sqlite3';monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('DEV_AUTH_ENABLED','false');monkeypatch.setenv('DATABASE_PATH',str(path));monkeypatch.setenv('TEST_OPERATOR_PASSWORD','a sufficiently long test password')
 cli(['--database',str(path),'create-user','--nickname','Operator','--password-env','TEST_OPERATOR_PASSWORD']);uid=json.loads(capsys.readouterr().out)['user_id']
 cli(['--database',str(path),'list-users']);listed=json.loads(capsys.readouterr().out);assert listed[0]['user_id']==uid and 'password_hash' not in listed[0]
 cli(['--database',str(path),'bootstrap-admin','--user-id',uid]);assert json.loads(capsys.readouterr().out)['role']=='super_admin'
 with pytest.raises(SystemExit):cli(['--database',str(path),'bootstrap-admin','--user-id',uid])
 backup=tmp_path/'backup.sqlite3';cli(['--database',str(path),'backup','--output',str(backup)])
 dest=tmp_path/'restored.sqlite3';cli(['--database',str(dest),'restore','--source',str(backup)])
 from app.repository import Repository
 assert SocialService(Repository(str(dest))).role(uid)=='super_admin'
 mod=importlib.reload(module())
 with TestClient(mod.app) as c:
  assert c.post('/api/dev-login',json={'nickname':'No','admin_key':'test-key'}).status_code==403
  assert c.post('/api/login',json={'user_id':uid,'password':'wrong'}).status_code==401
  response=c.post('/api/login',json={'user_id':uid,'password':'a sufficiently long test password'});assert response.status_code==200
  assert c.get('/api/admin/session',headers={'Authorization':'Bearer '+response.json()['token']}).json()['role']=='super_admin'

def test_critical_settings_super_only_and_audit(client):
 s=super_user(client);a=login(client,'Admin',admin_key='test-key')
 assert client.get('/api/admin/system-settings',headers=headers(a)).status_code==403
 assert client.put('/api/admin/system-settings',headers=headers(a),json={'world_name':'No','max_channels':32}).status_code==403
 r=client.put('/api/admin/system-settings',headers=headers(s),json={'world_name':'NOBIS Test World','max_channels':2});assert r.status_code==200
 assert r.json()['world_name']=='NOBIS Test World'
 assert client.get('/api/admin/logs',headers=headers(s)).json()[0]['action']=='system_settings_changed'

def test_development_sessions_invalid_in_production_and_password_reset(tmp_path,monkeypatch,capsys):
 path=tmp_path/'session.sqlite3';monkeypatch.setenv('DATABASE_PATH',str(path));monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('DEV_AUTH_ENABLED','false');monkeypatch.setenv('TEST_RESET_PASSWORD','new long operator password')
 from app.repository import Repository
 repo=Repository(str(path));repo.initialize();SocialService(repo).initialize();token,u=repo.create_user('Existing dev user')
 cli(['--database',str(path),'set-password','--user-id',u['id'],'--password-env','TEST_RESET_PASSWORD']);assert repo.user_for(token) is None
 # Even a fresh development-kind token must not be accepted in production.
 dev_token,_=repo.issue_session(u['id'],'dev')
 mod=importlib.reload(module())
 with TestClient(mod.app) as c:
  assert c.get('/api/me',headers={'Authorization':'Bearer '+dev_token}).status_code==401
  response=c.post('/api/login',json={'user_id':u['id'],'password':'new long operator password'});assert response.status_code==200

def test_private_rooms_and_admin_announcements_never_create_bubbles(client):
 admin=super_user(client);a,b=login(client,'A'),login(client,'B')
 client.put('/api/chat-preferences',headers=headers(a),json={'chat_bubbles_enabled':True})
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);frames(wa);frames(wb);place(a,10,10,'cafe')
  for kind in ('cafe','meeting'):
   cid=module().repository.create_channel(a['user']['id'],kind,kind);module().hub.peers[a['user']['id']].chatted=0
   wa.send_json({'type':'chat','channel':cid,'text':'private '+kind});until(wa,'chat')
   assert not any(m['type']=='chat_bubble' for m in frames(wb))
  client.post('/api/admin/announcements',headers=headers(admin),json={'title':'Notice','text':'not a bubble'})
  assert not any(m['type']=='chat_bubble' for m in frames(wb))

def test_first_super_admin_bootstrap_concurrent_requests(tmp_path):
 from concurrent.futures import ThreadPoolExecutor
 from app.repository import Repository
 repo=Repository(str(tmp_path/'bootstrap.sqlite3'));repo.initialize();svc=SocialService(repo);svc.initialize();_,a=repo.create_user('A');_,b=repo.create_user('B')
 def attempt(uid):
  try:svc.bootstrap(uid);return True
  except SocialError:return False
 with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(attempt,[a['id'],b['id']]))
 assert sum(result)==1
 with repo.connect() as c:
  assert c.execute("SELECT COUNT(*) FROM user_roles WHERE role='super_admin'").fetchone()[0]==1
  assert c.execute("SELECT COUNT(*) FROM admin_audit_logs WHERE action='bootstrap_super_admin'").fetchone()[0]==1
