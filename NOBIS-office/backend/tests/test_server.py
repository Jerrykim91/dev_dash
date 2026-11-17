import importlib
import math
import sqlite3
import os
import uuid
from urllib.parse import urlsplit,urlunsplit
from contextlib import ExitStack
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.world import valid_move, allowed, map_for, zones_for, zone_at, walkable, WORLD, ZONES, ROOM_DATA
from app.repository import Repository
from app.services.work_status import participation_for

@pytest.fixture(params=['sqlite',pytest.param('postgresql',marks=pytest.mark.skipif(not os.getenv('NOBIS_TEST_POSTGRES_URL'),reason='Set NOBIS_TEST_POSTGRES_URL for real PostgreSQL tests'))])
def client(tmp_path,monkeypatch,request):
    monkeypatch.setenv('APP_ENV','development');monkeypatch.setenv('DEV_AUTH_ENABLED','true');monkeypatch.setenv('DEV_ADMIN_KEY','test-key')
    monkeypatch.setenv('MEDIA_ROOT',str(tmp_path/'media'))
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'test.sqlite3'));monkeypatch.delenv('DATABASE_URL',raising=False)
    admin=None;database=None
    if request.param=='postgresql':
        import psycopg
        from psycopg import sql
        source=os.environ['NOBIS_TEST_POSTGRES_URL'];database='nobis_test_'+uuid.uuid4().hex[:16]
        admin=psycopg.connect(source,autocommit=True)
        app_source=os.getenv('NOBIS_TEST_POSTGRES_APP_URL',source);parsed=urlsplit(app_source)
        admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database),sql.Identifier(parsed.username)));monkeypatch.setenv('DATABASE_URL',urlunsplit(parsed._replace(path='/'+database)))
    try:
        import app.main as module
        importlib.reload(module)
        with TestClient(module.app) as c:yield c
    finally:
        if admin is not None:
            from psycopg import sql
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(database)));admin.close()

def login(c,name='Alice',**extra):
    r=c.post('/api/dev-login',json={'nickname':name,**extra})
    assert r.status_code==200,r.text
    return r.json()

def auth(ws,user):
    original=ws.receive_json
    def receive():
        while True:
            message=original()
            if message['type'] not in ('world_channels','room_counts'):return message
    ws.receive_json=receive
    ws.send_json({'token':user['token']})
    snapshot=ws.receive_json();assert snapshot['type']=='snapshot'
    assert ws.receive_json()['type']=='joined'
    return snapshot

def headers(u): return {'Authorization':f"Bearer {u['token']}"}

def near_object(id):
    scope,m=next((scope,m) for scope,m in ROOM_DATA['maps'].items() if any(o['id']==id for o in m['objects']))
    o=next(o for o in m['objects'] if o['id']==id)
    point=next((x,y) for x,y in [(o['x']+1,o['y']),(o['x'],o['y']+1),(o['x']-1,o['y']),(o['x'],o['y']-1)] if walkable(scope,x,y))
    return (*point,scope)

def place(user,x,y,room_type='lobby'):
    import app.main as module
    p=module.hub.peers[user['user']['id']]
    if room_type=='meeting':
        cid=module.repository.create_channel(user['user']['id'],'meeting','Fixture meeting')
    else:cid=None
    p.player.update(module.rooms.plan(p.player,room_type,cid,position={'x':x,'y':y}))
    p.moved-=1;p.move_credit=.8
    return p

def test_health_auth_and_single_world_definition(client):
    u=login(client)
    assert client.get('/health').json()['max_players']==15
    assert client.get('/api/me').status_code==401
    assert client.get('/api/me',headers=headers(u)).json()['nickname']=='Alice'
    zones=client.get('/api/zones',headers=headers(u)).json()
    assert {z['id'] for z in zones}=={'office','focus','cafe','lounge','meeting','garden','outside'}
    assert len({z['map_id'] for z in zones})==7
    assert client.get('/api/zones/personal:other/users',headers=headers(u)).status_code==403
    assert client.post('/api/dev-login',json={'nickname':'  '}).status_code==422
    assert client.post('/api/dev-login',json={'nickname':'Admin','admin_key':'wrong'}).status_code==403


def test_work_status_spectator_still_independent_of_zone(client):
    u=login(client)
    with client.websocket_connect('/ws') as ws:
        auth(ws,u)
        ws.send_json({'type':'status','work_status':'after_work','message':''})
        assert ws.receive_json()['player']['participation_mode']=='spectator'
        spawn=WORLD['spawn'];ws.send_json({'type':'move','zone':'office','x':spawn['x']+.1,'y':spawn['y'],'direction':'east'})
        assert ws.receive_json()['type']=='correction'
        ws.send_json({'type':'status','work_status':'vacation','message':''})
        p=ws.receive_json()['player'];assert p['participation_mode']=='normal' and p['status_text']=='휴가 중' and p['zone']=='office'
        ws.send_json({'type':'move','zone':'vacation','x':spawn['x']+.1,'y':spawn['y'],'direction':'east'})
        moved=ws.receive_json();assert moved['type']=='moved' and moved['player']['zone']=='office' and moved['player']['status_text']=='휴가 중'
        ws.send_json({'type':'status','work_status':'spectator','message':''})
        assert ws.receive_json()['type']=='error'



def test_no_legacy_teleport_or_client_claimed_zone(client):
    u=login(client)
    with client.websocket_connect('/ws') as ws:
        auth(ws,u)
        ws.send_json({'type':'travel','zone':'cafe'})
        assert ws.receive_json()['type']=='error'
        ws.send_json({'type':'move','zone':'vacation','x':WORLD['spawn']['x']+.1,'y':WORLD['spawn']['y'],'direction':'east'})
        assert ws.receive_json()['player']['zone']=='office'

def test_room_acl_announcements_and_mention_privacy(client):
    import app.main as module
    a,b=login(client),login(client,'Admin',admin_key='test-key')
    cid=module.repository.create_channel(a['user']['id'],'cafe','Private')
    with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
        auth(wa,a);auth(wb,b);wa.receive_json()
        wa.send_json({'type':'chat','channel':'announcements','text':'forbidden'})
        assert wa.receive_json()['type']=='error'
        assert client.post('/api/admin/announcements',headers=headers(b),json={'title':'공지','text':'공지'}).status_code==200
        assert wa.receive_json()['announcement']['title']=='공지'
        assert wb.receive_json()['announcement']['author_id']==b['user']['id']
        wa.send_json({'type':'chat','channel':cid,'text':'SECRET','mentions':[b['user']['id']]})
        assert wa.receive_json()['chat']['text']=='SECRET'
        wb.send_json({'type':'ping'});assert wb.receive_json()['type']=='pong'
        wb.send_json({'type':'chat','channel':cid,'text':'forbidden'})
        assert wb.receive_json()['type']=='error'

def test_interactions_use_shared_world_coordinates(client):
    u=login(client)
    with client.websocket_connect('/ws') as ws:
        auth(ws,u);place(u,*near_object('chair'))
        ws.send_json({'type':'interact','object_id':'chair','action':'vacation'})
        assert ws.receive_json()['player']['action']=='sitting'
        assert ws.receive_json()['interaction']['kind']=='action'
        place(u,*near_object('whiteboard'))
        ws.send_json({'type':'interact','object_id':'whiteboard'})
        assert ws.receive_json()['interaction']['kind']=='menu'

def test_reject_bad_movement_and_payloads(client):
    u=login(client)
    with client.websocket_connect('/ws') as ws:
        auth(ws,u)
        for x,y in [(1000,1000),(-2,13),(float('nan'),13),(3,3)]:
            ws.send_json({'type':'move','zone':'office','x':x,'y':y,'direction':'east'})
            assert ws.receive_json()['type'] in ('error','correction')
        ws.send_text('[]');assert ws.receive_json()['type']=='error'
        ws.send_json({'type':'chat','channel':'world','text':'x'*501});assert ws.receive_json()['type']=='error'
        ws.send_json({'type':'interact','object_id':'chair'});assert ws.receive_json()['type']=='error'

def test_max_fifteen_connections(client):
    with ExitStack() as stack:
        for i in range(15):
            user=login(client,f'user{i}')
            ws=stack.enter_context(client.websocket_connect('/ws'));snapshot=auth(ws,user)
        assert len(snapshot['players'])==15 and len({p['avatar']['palette'] for p in snapshot['players']})==15
        extra=login(client,'sixteenth')
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'token':extra['token']});assert ws.receive_json()['type']=='admission_denied';ws.receive_json()
        assert exc.value.code==4003

def test_chat_sender_identity_cannot_be_forged(client):
    u=login(client,'Real sender')
    with client.websocket_connect('/ws') as ws:
        auth(ws,u);ws.send_json({'type':'chat','channel':'world','text':'hello','user_id':'forged','nickname':'Imposter'})
        chat=ws.receive_json()['chat'];assert chat['user_id']==u['user']['id'] and chat['nickname']=='Real sender'

def test_legacy_sqlite_migration_preserves_users(tmp_path):
    path=tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE users(id TEXT PRIMARY KEY,nickname TEXT,status TEXT,message TEXT)")
        c.execute("INSERT INTO users VALUES ('old','Existing','focus','keep me')")
    repo=Repository(str(path));repo.initialize()
    with repo.connect() as c:
        row=c.execute("SELECT * FROM users WHERE id='old'").fetchone()
        assert row['nickname']=='Existing' and row['message']=='keep me' and row['work_status']=='working'

def test_auth_disabled_outside_development(tmp_path,monkeypatch):
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('DEV_AUTH_ENABLED','true')
    import app.main as module;importlib.reload(module)
    with pytest.raises(RuntimeError,match='forbidden'):
        with TestClient(module.app):pass

def test_invalid_origin_and_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws',headers={'origin':'https://invalid.example'}):pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'token':'invalid'});ws.receive_json()
