import importlib
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from starlette.websockets import WebSocketDisconnect
from test_server import client,login,auth,headers,place
from test_social import super_user,channel,frames,module,move_channel
from app.client_config import client_config,valid_dashboard_url
from app.home import HomeError

def test_runtime_dashboard_config_and_production_validation(client,monkeypatch):
 monkeypatch.setenv('DEVNEST_DEV_URL','http://127.0.0.1:8001/');monkeypatch.delenv('DEVNEST_URL',raising=False)
 assert client.get('/api/client-config').json()['allow_local'] is True
 monkeypatch.setenv('APP_ENV','production')
 assert client_config()['default_url']=='' and not client_config()['allow_local']
 for value in ['http://127.0.0.1/','http://localhost/','http://[::1]/','javascript:alert(1)','https://user:password@example.com/','http://0.0.0.0/']:
  assert not valid_dashboard_url(value,True)
 assert valid_dashboard_url('https://dashboard.example.com/work',True)
 monkeypatch.setenv('DEVNEST_URL','http://127.0.0.1/')
 with pytest.raises(RuntimeError):client_config()

def test_readable_audit_source_and_admin_dashboard(client):
 a=super_user(client);u=login(client,'나래');channel(client,a)
 r=client.put('/api/admin/users/'+u['user']['id']+'/role',headers=headers(a),json={'role':'moderator'});assert r.status_code==200
 d=client.get('/api/admin/dashboard',headers=headers(a)).json()
 assert d['users']==2 and d['active_channels']==2 and d['account_origins']['development']==2
 assert d['server']['database'] in ('sqlite','postgresql') and d['server']['database_status']=='ready'
 assert len(d['channel_population'])==2
 l=client.get('/api/admin/logs',headers=headers(a)).json()[0]
 assert l['actor_name']=='Super' and l['target_name']=='나래' and 'moderator' in l['details']
 assert client.get('/api/admin/dashboard',headers=headers(u)).status_code==200 # moderator dashboard only
 assert client.get('/api/admin/logs',headers=headers(u)).status_code==403

def test_disabled_saved_channel_fallback_and_explicit_reconnect(client):
 admin=super_user(client);channel(client,admin);a=login(client,'returning')
 with client.websocket_connect('/ws') as ws:
  auth(ws,a);move_channel(ws,'ch2');place(a,10,10,'cafe')
 assert client.put('/api/admin/channels/ch2',headers=headers(admin),json={'id':'ch2','name':'ch2','capacity':15,'enabled':False}).status_code==200
 with client.websocket_connect('/ws') as ws:
  ws.send_json({'token':a['token'],'channel_id':'ch2'});assert ws.receive_json()['type']=='admission_denied'
  with pytest.raises(WebSocketDisconnect):ws.receive_json()
 with client.websocket_connect('/ws') as ws:
  snap=auth(ws,a);assert snap['world_channel_id']=='ch1';p=snap['players'][0]
  assert (p['x'],p['y'])!=(10,30) # disabled channel coordinates cannot leak into ch1

def test_full_admission_can_retry_another_channel_and_duplicate_session(client):
 admin=super_user(client);channel(client,admin,capacity=1);a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa:
  auth(wa,a);move_channel(wa,'ch2')
  with client.websocket_connect('/ws') as denied:
   denied.send_json({'token':b['token'],'channel_id':'ch2'});m=denied.receive_json();assert m['type']=='admission_denied' and len(m['world_channels'])==2
   with pytest.raises(WebSocketDisconnect) as e:denied.receive_json()
   assert e.value.code==4003
  with client.websocket_connect('/ws') as retry:
   retry.send_json({'token':b['token'],'channel_id':'ch1'});assert retry.receive_json()['world_channel_id']=='ch1'
  frames(wa)
  with client.websocket_connect('/ws') as replacement:
   replacement.send_json({'token':a['token'],'channel_id':'ch2'});assert replacement.receive_json()['world_channel_id']=='ch2'
   with pytest.raises(WebSocketDisconnect) as e:
    while True:wa.receive_json()
   assert e.value.code==4001 and len(module().hub.peers)==1

def test_auth_frame_limit_and_database_failure_redaction(client,monkeypatch):
 with client.websocket_connect('/ws') as ws:
  ws.send_text('x'*4097)
  with pytest.raises(WebSocketDisconnect) as e:ws.receive_json()
  assert e.value.code==1009
 def failed():raise module().repository.errors[0]('postgresql://secret-password@private-host')
 monkeypatch.setattr(module().repository,'ping',failed)
 response=client.get('/health');assert response.status_code==503 and 'secret-password' not in response.text

def test_database_purchase_concurrency_and_persistence(client):
 u=login(client);uid=u['user']['id'];svc=module().homes;key=str(uuid.uuid4())
 with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:svc.purchase(uid,'furniture_plant_001',key),range(8)))
 assert len({r['receipt']['instance_id'] for r in results})==1
 before=svc.state(uid);assert before['balance']==960 and len(before['inventory'])==9
 # Rebuild repository/service against same storage rather than reusing in-memory state.
 from app.repository import Repository
 from app.home import HomeService
 repo=Repository(module().repository.path);repo.initialize();restarted=HomeService(repo,1000);restarted.initialize()
 assert restarted.state(uid)['balance']==960 and len(restarted.state(uid)['inventory'])==9

def test_environment_generator_private_and_no_overwrite(tmp_path):
 script=Path(__file__).parents[2]/'infra/init-env.py';target=tmp_path/'production.env'
 r=subprocess.run([sys.executable,str(script),'--output',str(target),'--devnest-url','https://dashboard.example.com/'],capture_output=True,text=True);assert r.returncode==0
 content=target.read_text();assert target.stat().st_mode&0o777==0o600 and 'APP_ENV=production' in content and 'DEV_AUTH_ENABLED=false' in content
 assert 'POSTGRES_PASSWORD=' in content and content.split('POSTGRES_PASSWORD=')[1].splitlines()[0] not in r.stdout
 assert subprocess.run([sys.executable,str(script),'--output',str(target)],capture_output=True).returncode!=0
 assert target.read_text()==content
 assert subprocess.run([sys.executable,str(script),'--output',str(tmp_path/'bad.env'),'--devnest-url','http://localhost/'],capture_output=True).returncode!=0

def test_sqlite_import_preserves_data_and_refuses_nonempty_target(client,tmp_path):
 repo=module().repository
 if repo.kind!='postgresql':pytest.skip('PostgreSQL migration integration')
 import hashlib
 from app.repository import Repository
 from app.social import SocialService
 from app.home import HomeService
 from app.db_transfer import import_sqlite
 source=tmp_path/'source.sqlite3';old=Repository(str(source));old.initialize();social=SocialService(old);social.initialize();homes=HomeService(old,1000);homes.initialize()
 token,u=old.create_user('Migrated');uid=u['id'];homes.ensure(uid);social.bootstrap(uid);homes.purchase(uid,'furniture_plant_001',str(uuid.uuid4()))
 from app.collectibles.service import CollectibleService
 from app.community.service import CommunityService
 from PIL import Image
 import io
 collectibles=CollectibleService(old,homes,social);collectibles.initialize();collectibles.claim(uid)
 draw=collectibles.draw(uid,'daily-coins',1,str(uuid.uuid4()),1)
 community=CommunityService(old,social,None,media_root=tmp_path/'source-media')
 group=community.save_group(uid,{'name':'이전 그룹','description':'사진 포함','visibility':'private','max_members':4,'cover_media_id':None})
 content=io.BytesIO();Image.new('RGB',(8,8),'purple').save(content,format='PNG');media=community.upload(uid,content.getvalue())
 log=community.write_log(uid,{'group_id':group['id'],'text':'이전되는 기록','visibility':'group','media_ids':[media['id']]})
 from app.rooms import RoomManager
 from app.websocket.hub import Hub
 rm=RoomManager(old,Hub(old),homes);rm.initialize();player={'id':uid,'channel_id':'ch1','scope':'office'};player.update(rm.plan(player,'focus'));rm.persist(player)
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 result=import_sqlite(repo,source);assert result['imported'] and result['counts']['users']==1
 assert result['counts']['room_definitions']==7 and result['counts']['room_presence']==1
 with repo.connect() as c:assert c.execute('SELECT room_type FROM room_presence WHERE user_id=?',(uid,)).fetchone()[0]=='focus'
 assert result['counts']['gacha_coin_draw_items']==1 and result['counts']['shared_logs']==1 and result['counts']['log_media']==1
 assert module().collectibles.receipt(uid,draw['draw']['id'])['pool_version']==1 and module().collectibles.status(uid)['balance']==0
 assert module().community.get_log(uid,log['id'])['text']=='이전되는 기록'
 # Files travel alongside the DB; relative storage_key is retained unchanged.
 import shutil
 shutil.copytree(tmp_path/'source-media',module().community.storage.root,dirs_exist_ok=True)
 path,_=module().community.media(uid,media['id']);assert path.read_bytes()

 assert repo.user_for(token)['id']==uid and module().social.role(uid)=='super_admin'
 state=module().homes.state(uid);assert state['balance']==960+draw['draw']['total_coins'] and len(state['inventory'])==9 and len(state['placements'])==6
 with pytest.raises(ValueError,match='empty'):import_sqlite(repo,source)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 assert module().homes.state(uid)['balance']==960+draw['draw']['total_coins']

@pytest.mark.parametrize('payload',[b'not-a-text-frame','{invalid json'])
def test_malformed_auth_frame_closes_cleanly(client,payload):
 with client.websocket_connect('/ws') as ws:
  if isinstance(payload,bytes):ws.send_bytes(payload)
  else:ws.send_text(payload)
  with pytest.raises(WebSocketDisconnect) as exc:ws.receive_json()
  assert exc.value.code==1003
