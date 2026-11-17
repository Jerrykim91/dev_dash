from test_server import near_object
from contextlib import ExitStack
from test_server import client,login,auth,headers,place
from app.repository import Repository
from app.world import map_for,walkable

def until(ws,kind):
    for _ in range(50):
        msg=ws.receive_json()
        if msg['type']==kind:return msg
    raise AssertionError(f'Missing {kind}')

def drain(ws):
    ws.send_json({'type':'ping'});return until(ws,'pong')

def test_private_cafe_invite_accept_history_leave_and_no_leak(client):
    a,b,c=login(client,'Host'),login(client,'Guest'),login(client,'Outsider')
    with ExitStack() as stack:
        wa,wb,wc=[stack.enter_context(client.websocket_connect('/ws')) for _ in range(3)]
        for ws,u in [(wa,a),(wb,b),(wc,c)]:auth(ws,u)
        for ws in (wa,wb,wc):drain(ws)
        place(a,10,10,'cafe');wa.send_json({'type':'channel_create','kind':'cafe','name':'Private cafe'})
        cid=until(wa,'channel_created')['channel_id'];drain(wb);drain(wc)
        wa.send_json({'type':'chat','channel':cid,'text':'secret before invitation','mentions':[c['user']['id']]})
        assert until(wa,'chat')['chat']['text']=='secret before invitation'
        wc.send_json({'type':'ping'});assert wc.receive_json()['type']=='pong'
        assert client.get(f'/api/channels/{cid}/messages',headers=headers(c)).status_code==403
        wa.send_json({'type':'channel_invite','channel_id':cid,'user_id':b['user']['id']})
        invitation=until(wb,'notification')['notification'];assert invitation['kind']=='invite' and 'secret' not in str(invitation)
        until(wb,'channels');assert client.get(f'/api/channels/{cid}/messages',headers=headers(b)).status_code==403
        wb.send_json({'type':'history','channel':cid});assert until(wb,'error')['type']=='error'
        wb.send_json({'type':'channel_accept','channel_id':cid});until(wb,'channel_accepted')
        assert client.get(f'/api/channels/{cid}/messages',headers=headers(b)).json()[0]['text']=='secret before invitation'
        drain(wa);drain(wc);wb.send_json({'type':'chat','channel':cid,'text':'approved guest'})
        assert until(wb,'chat')['chat']['nickname']=='Guest';assert until(wa,'chat')['chat']['text']=='approved guest'
        wc.send_json({'type':'ping'});assert wc.receive_json()['type']=='pong'
        wc.send_json({'type':'channel_accept','channel_id':cid});assert until(wc,'error')['type']=='error'
        wb.send_json({'type':'channel_leave','channel_id':cid});until(wb,'channel_revoked');until(wb,'channels')
        assert client.get(f'/api/channels/{cid}/messages',headers=headers(b)).status_code==403
        wb.send_json({'type':'chat','channel':cid,'text':'revoked'});assert until(wb,'error')['type']=='error'

def test_meeting_attendance_end_and_archived_records(client):
    a,b=login(client,'Organizer'),login(client,'Attendee')
    with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
        auth(wa,a);auth(wb,b);drain(wa)
        wa.send_json({'type':'channel_create','kind':'meeting','name':'Wrong position'});assert until(wa,'error')['type']=='error'
        place(a,7,18,'lobby');wa.send_json({'type':'channel_create','kind':'meeting','name':'Weekly review'})
        cid=until(wa,'channel_created')['channel_id'];assert client.get('/api/channels',headers=headers(a)).json()[0]['meeting_id'].startswith('meeting:')
        wa.send_json({'type':'channel_invite','channel_id':cid,'user_id':b['user']['id']});until(wb,'notification');until(wb,'channels')
        wb.send_json({'type':'channel_accept','channel_id':cid});until(wb,'channel_accepted');drain(wa)
        wa.send_json({'type':'chat','channel':cid,'text':'saved meeting record'});until(wa,'chat');until(wb,'chat')
        wa.send_json({'type':'channel_close','channel_id':cid});until(wa,'channels');until(wb,'channels')
        wb.send_json({'type':'chat','channel':cid,'text':'after closing'});assert until(wb,'error')['type']=='error'
        assert client.get(f'/api/channels/{cid}/messages',headers=headers(b)).json()[0]['text']=='saved meeting record'

def test_toggle_interactions_and_status_bubbles(client):
    u=login(client)
    with client.websocket_connect('/ws') as ws:
        auth(ws,u);cx,cy,scope=near_object('chair');place(u,cx,cy,scope);ws.send_json({'type':'interact','object_id':'chair'})
        p=until(ws,'action')['player'];assert p['action']=='sitting' and p['status_text']=='앉아서 쉬는 중';until(ws,'interaction')
        ws.send_json({'type':'move','scope':'office','zone':'focus','x':cx,'y':cy,'direction':'south','moving':False});assert until(ws,'moved')['player']['action']=='sitting'
        ws.send_json({'type':'interact','object_id':'chair'});assert until(ws,'action')['player']['action']=='idle';until(ws,'interaction')
        for object_id,action in [('desk-0','working'),('coffee','drinking'),('sofa-0','resting')]:
            place(u,*near_object(object_id));ws.send_json({'type':'interact','object_id':object_id});assert until(ws,'action')['player']['action']==action;until(ws,'interaction')
        place(u,*near_object('bookshelf'));ws.send_json({'type':'interact','object_id':'bookshelf'});assert until(ws,'object_effect')['object_id']=='bookshelf';assert until(ws,'interaction')['interaction']['personal_entry'] is True
        ws.send_json({'type':'status','work_status':'focusing','message':'내가 설정한 상태'});assert until(ws,'status')['player']['status_text']=='내가 설정한 상태'
        assert client.get('/api/work-status',headers=headers(u)).json()['provider']=='mock'

def test_personal_scope_settings_privacy_return_and_reconnect(client):
    a,b=login(client,'Room owner'),login(client,'Other')
    with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
        auth(wa,a);auth(wb,b);drain(wa);place(a,10,10,'cafe');wa.send_json({'type':'room_enter'})
        own=until(wa,'scope_changed')['player'];assert own['scope']==a['home_id'] and own['zone']=='personal'
        drain(wb);assert len(__import__('app.main',fromlist=['hub']).hub.players_for(b['user']['id']))==1
        wb.send_json({'type':'room_enter','owner_id':a['user']['id']});assert until(wb,'error')['type']=='error'
        wa.send_json({'type':'move','scope':a['home_id'],'zone':'personal','x':6.1,'y':7,'direction':'east'});assert until(wa,'moved')['player']['scope']==a['home_id']
        wa.send_json({'type':'chat','channel':f"zone:{a['home_id']}",'text':'personal chat'});until(wa,'chat');wb.send_json({'type':'ping'});assert wb.receive_json()['type']=='pong'
        assert client.put('/api/personal-room',headers=headers(a),json={'name':'My study','dashboard_url':'http://localhost:8000/'}).status_code==200
        assert client.get('/api/personal-room',headers=headers(b)).json()['dashboard_url']==''
        assert client.put('/api/personal-room',headers=headers(a),json={'name':'Unsafe','dashboard_url':'javascript:alert(1)'}).status_code==422
        wa.send_json({'type':'room_leave'});p=until(wa,'scope_changed')['player'];assert p['scope']=='office' and p['x']==10 and p['y']==10;drain(wb)
    with client.websocket_connect('/ws') as ws:
        snapshot=auth(ws,a);p=next(p for p in snapshot['players'] if p['id']==a['user']['id']);assert p['x']==10 and snapshot['room_settings']['name']=='My study'

def test_schema_version_and_durable_records(tmp_path):
    repo=Repository(str(tmp_path/'durable.sqlite3'));repo.initialize();token,user=repo.create_user('Persist')
    repo.save_avatar(user['id'],'#d2beff');repo.update_status(user['id'],'vacation','휴가');repo.save_settings(user['id'],'Saved room','https://example.org/dashboard')
    cid=repo.create_channel(user['id'],'meeting','Saved meeting');repo.save_chat({'id':'message-1','channel':cid,'user_id':user['id'],'nickname':'Persist','text':'record','time':'2026-11-05T00:00:00Z','mentions':[]});repo.close_channel(cid,user['id']);repo.initialize()
    assert repo.user_for(token)['work_status']=='vacation' and repo.avatar_for(user['id'])['palette']=='#d2beff'
    assert repo.settings_for(user['id'])['name']=='Saved room' and repo.history(cid)[0]['text']=='record' and repo.channel(cid)['status']=='closed'
    with repo.connect() as c:
        tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'users','avatar_profiles','user_status','zone_presence','chat_channels','chat_messages','channel_members','personal_rooms','room_settings'}<=tables
        assert c.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=2').fetchone()[0]==1


def test_unaccepted_invitation_expires_when_owner_closes(client):
    import app.main as module
    a,b=login(client,'Owner'),login(client,'Pending')
    cid=module.repository.create_channel(a['user']['id'],'meeting','Closed before acceptance')
    module.repository.invite(cid,a['user']['id'],b['user']['id'])
    module.repository.close_channel(cid,a['user']['id'])
    assert module.repository.channels_for(b['user']['id'])==[]
    assert client.get(f'/api/channels/{cid}/messages',headers=headers(b)).status_code==403
    with client.websocket_connect('/ws') as ws:
        auth(ws,b);ws.send_json({'type':'channel_accept','channel_id':cid})
        assert until(ws,'error')['type']=='error'


def test_invalid_settings_and_unicode_admin_key_are_rejected(client):
    u=login(client)
    assert client.put('/api/personal-room',headers=headers(u),json={'name':'Room','dashboard_url':'http://['}).status_code==422
    assert client.post('/api/dev-login',json={'nickname':'Admin','admin_key':'잘못된 키'}).status_code==403
