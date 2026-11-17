import io
from PIL import Image
import pytest
from test_server import client,login,headers,auth
from test_social import module,super_user,frames,channel,move_channel
from test_phase2 import until

def api(c,u,path,body=None,method=None):return c.request(method or ('POST' if body is not None else 'GET'),'/api/community'+path,headers=headers(u),json=body)
def create(c,u,**extra):
 r=api(c,u,'/groups',{'name':'작은 기록','description':'일상','visibility':'private','max_members':4,**extra});assert r.status_code==200,r.text;return r.json()
def invite(c,a,b,g):
 r=api(c,a,'/groups/'+g['id']+'/invitations',{'user_id':b['user']['id']});assert r.status_code==200,r.text;r=api(c,b,'/invitations/'+r.json()['invitation_id'],{'accept':True});assert r.status_code==200,r.text

def post(c,u,g,**extra):
 r=api(c,u,'/logs',{'group_id':g['id'],'text':'오늘 <script>safe text</script>','visibility':'group','media_ids':[],**extra});assert r.status_code==200,r.text;return r.json()
def image(fmt='PNG',size=(24,24)):
 b=io.BytesIO();Image.new('RGB',size,'purple').save(b,format=fmt);return b.getvalue()
def upload(c,u,data=None):return c.post('/api/community/media',headers={**headers(u),'Content-Type':'text/plain'},content=data or image())

def test_friend_accept_reject_cancel_duplicates_and_block(client):
 a,b=login(client,'A'),login(client,'B');rid=api(client,a,'/friend-requests',{'user_id':b['user']['id']}).json()['requests'][0]['id']
 assert api(client,a,'/friend-requests',{'user_id':b['user']['id']}).status_code==409 and api(client,a,'/friend-requests',{'user_id':a['user']['id']}).status_code==422
 assert api(client,a,'/friend-requests/'+rid,{'action':'accept'}).status_code==403
 api(client,b,'/friend-requests/'+rid,{'action':'accept'});assert api(client,a,'/friends').json()['friends'][0]['user_id']==b['user']['id']
 api(client,a,'/friends/'+b['user']['id'],method='DELETE');rid=api(client,a,'/friend-requests',{'user_id':b['user']['id']}).json()['requests'][0]['id'];api(client,b,'/friend-requests/'+rid,{'action':'reject'});rid=api(client,a,'/friend-requests',{'user_id':b['user']['id']}).json()['requests'][0]['id'];api(client,a,'/friend-requests/'+rid,{'action':'cancel'})
 api(client,b,'/blocks/'+a['user']['id'],{'enabled':True},'PUT');assert api(client,a,'/friend-requests',{'user_id':b['user']['id']}).status_code==403
 with client.websocket_connect('/ws') as wa:
  auth(wa,a);wa.send_json({'type':'private_message','recipient_id':b['user']['id'],'text':'@B blocked'});until(wa,'error')
 api(client,b,'/blocks/'+a['user']['id'],{'enabled':False},'PUT');assert api(client,a,'/friend-requests',{'user_id':b['user']['id']}).status_code==200

def test_profile_privacy_api_and_world(client):
 a,b=login(client,'A'),login(client,'B');privacy={k:'private' for k in ('bio','message','presence','work_status','location')};api(client,a,'/profiles/me',{'bio':'secret','privacy':privacy},'PUT');p=api(client,b,'/profiles/'+a['user']['id']).json();assert all(p[k] is None for k in privacy)
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);s=auth(wb,b);p=next(p for p in s['players'] if p['id']==a['user']['id']);assert p['work_status'] is None and p['message']=='' and p['status_text']=='' and p['presence']=='private'
 assert api(client,a,'/profiles/me').json()['bio']=='secret'
 privacy={k:'friends' for k in privacy};api(client,a,'/profiles/me',{'bio':'friends only','privacy':privacy},'PUT');rid=api(client,b,'/friend-requests',{'user_id':a['user']['id']}).json()['requests'][0]['id'];api(client,a,'/friend-requests/'+rid,{'action':'accept'});assert api(client,b,'/profiles/'+a['user']['id']).json()['bio']=='friends only'

def test_group_roles_capacity_and_admin_independence(client):
 a,b,c,d=[login(client,n) for n in ('A','B','C','D')];g=create(client,a,max_members=3);assert api(client,c,'/groups/'+g['id']).status_code==404
 invite(client,a,b,g);api(client,a,'/groups/'+g['id']+'/members',{'user_id':b['user']['id'],'action':'manager'});invite(client,b,c,g)
 assert api(client,b,'/groups/'+g['id'],{'name':'hijack','description':'','visibility':'public','max_members':3},'PUT').status_code==403 and client.get('/api/admin/users',headers=headers(b)).status_code==403
 iid=api(client,a,'/groups/'+g['id']+'/invitations',{'user_id':d['user']['id']}).json()['invitation_id'];assert api(client,d,'/invitations/'+iid,{'accept':True}).status_code==409
 assert api(client,b,'/groups/'+g['id']+'/members',{'user_id':a['user']['id'],'action':'kick'}).status_code==403
 api(client,c,'/groups/'+g['id']+'/members',{'user_id':c['user']['id'],'action':'leave'});assert api(client,c,'/groups/'+g['id']).status_code==404
 api(client,a,'/groups/'+g['id']+'/members',{'user_id':b['user']['id'],'action':'kick'});assert api(client,b,'/groups/'+g['id']).status_code==404

def test_public_join_approval_delete(client):
 a,b=login(client,'A'),login(client,'B');g=create(client,a,visibility='public');assert api(client,b,'/groups?discover=true').json()['groups'][0]['id']==g['id'];rid=api(client,b,'/groups/'+g['id']+'/join',{}).json()['invitation_id'];assert api(client,b,'/groups/'+g['id']+'/logs').status_code==403
 api(client,a,'/invitations/'+rid,{'accept':True});assert api(client,b,'/groups/'+g['id']).json()['my_role']=='member';api(client,a,'/groups/'+g['id'],method='DELETE');assert api(client,b,'/groups/'+g['id']).status_code==404

def test_log_comment_reaction_private_scope_and_crud(client):
 a,b,c=login(client,'A'),login(client,'B'),login(client,'C');g=create(client,a);invite(client,a,b,g);l=post(client,a,g);private=post(client,a,g,visibility='self',text='only me')
 assert api(client,c,'/logs/'+l['id']).status_code==403 and api(client,b,'/logs/'+private['id']).status_code==404 and len(api(client,b,'/groups/'+g['id']+'/logs').json()['items'])==1
 assert api(client,b,'/logs/'+l['id'],{'group_id':g['id'],'text':'hijack','visibility':'group','media_ids':[]},'PUT').status_code==403
 com=api(client,b,'/logs/'+l['id']+'/comments',{'text':'반가워요'}).json()[0];assert api(client,a,'/logs/'+l['id']+'/comments/'+com['id'],{'text':'hijack'},'PUT').status_code==403
 for kind,target in [('log',l['id']),('comment',com['id'])]:
  for _ in range(2):assert api(client,b,'/reactions/'+kind+'/'+target,{'emoji':'heart','enabled':True},'PUT').json()[0]['count']==1
  assert api(client,b,'/reactions/'+kind+'/'+target,{'emoji':'heart','enabled':False},'PUT').json()==[]
 assert api(client,b,'/logs/'+l['id']+'/comments/'+com['id'],{'text':'수정'},'PUT').json()[0]['text']=='수정'
 api(client,b,'/logs/'+l['id']+'/comments/'+com['id'],method='DELETE');assert api(client,a,'/logs/'+l['id']+'/comments').json()==[]
 api(client,a,'/logs/'+l['id'],method='DELETE');assert api(client,b,'/logs/'+l['id']).status_code==404

@pytest.mark.parametrize('fmt',['PNG','JPEG','WEBP'])
def test_image_content_private_download_revoke_and_cleanup(client,fmt):
 a,b,c=login(client,'A'),login(client,'B'),login(client,'C');g=create(client,a);invite(client,a,b,g);r=upload(client,a,image(fmt));assert r.status_code==200,r.text;mid=r.json()['id'];assert client.get('/api/community/media/'+mid,headers=headers(c)).status_code==404
 l=post(client,a,g,media_ids=[mid]);assert client.get('/api/community/media/'+mid,headers=headers(b)).status_code==200
 assert api(client,b,'/logs',{'group_id':g['id'],'text':'stolen','media_ids':[mid],'visibility':'group'}).status_code==403
 api(client,b,'/groups/'+g['id']+'/members',{'user_id':b['user']['id'],'action':'leave'});assert client.get('/api/community/media/'+mid,headers=headers(b)).status_code==403
 api(client,a,'/logs/'+l['id'],method='DELETE');assert client.get('/api/community/media/'+mid,headers=headers(a)).status_code==404 and module().community.cleanup_media()['removed']==1

def test_upload_validation(client):
 a=login(client)
 for data in (b'<svg onload="alert(1)"/>',b'not a jpg',image()[:20],image(size=(4097,1))):assert upload(client,a,data).status_code==422
 assert upload(client,a,b'x'*(5*1024*1024+1)).status_code==413 and client.post('/api/community/media',content=image()).status_code==401

def test_personal_notifications_cross_channel_and_offline(client):
 admin=super_user(client);channel(client,admin);a,b,c=login(client,'A'),login(client,'B'),login(client,'C');g=create(client,a);invite(client,a,b,g)
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb,client.websocket_connect('/ws') as wc:
  auth(wa,a);auth(wb,b);auth(wc,c);move_channel(wb,'ch2');frames(wa);frames(wb);frames(wc);l=post(client,a,g);assert any(m['type']=='social_refresh' for m in frames(wb)) and not any(m['type']=='social_refresh' for m in frames(wc))
  assert any(n['log_id']==l['id'] for n in api(client,b,'/notifications').json()['items']) and api(client,c,'/notifications').json()['items']==[]
  nid=api(client,b,'/notifications').json()['items'][0]['id'];api(client,a,'/notifications/'+nid+'/read',{});assert api(client,b,'/notifications').json()['unread_count']>0
 l=post(client,a,g,text='offline');assert any(n['log_id']==l['id'] for n in api(client,b,'/notifications').json()['items']);assert api(client,b,'/notifications/read',{}).json()['unread_count']==0

def test_report_scoped_moderation_and_audit(client):
 admin=super_user(client);a,b=login(client,'A'),login(client,'B');g=create(client,a);invite(client,a,b,g);mid=upload(client,a).json()['id'];l=post(client,a,g,media_ids=[mid]);assert api(client,admin,'/logs/'+l['id']).status_code==403
 rid=api(client,b,'/reports',{'target_kind':'log','target_id':l['id'],'reason':'검토 요청'}).json()['report_id'];path='/api/admin/community/reports/'+rid;assert client.get(path,headers=headers(a)).status_code==403
 assert client.get(path,headers=headers(admin)).json()['content']['text']==l['text'] and client.get(path+'/media/'+mid,headers=headers(admin)).status_code==200
 assert client.put(path,headers=headers(admin),json={'hidden':True,'resolution':'정책에 따라 숨김'}).status_code==200 and api(client,b,'/logs/'+l['id']).status_code==404
 assert {'social_report_reviewed','social_report_resolved'}<={l['action'] for l in client.get('/api/admin/logs',headers=headers(admin)).json()}

def test_pagination_restart_and_blocked_feed(client):
 from app.community.service import CommunityService
 a,b=login(client,'A'),login(client,'B');g=create(client,a);invite(client,a,b,g)
 for i in range(12):post(client,a,g,text='record'+str(i))
 first=api(client,b,'/groups/'+g['id']+'/logs?limit=5').json();second=api(client,b,'/groups/'+g['id']+'/logs?limit=5&cursor='+first['next_cursor']).json();assert len(first['items'])==5 and not {r['id'] for r in first['items']}&{r['id'] for r in second['items']}
 mid=upload(client,a).json()['id'];l=post(client,a,g,media_ids=[mid]);rebuilt=CommunityService(module().repository,module().social,module().hub,str(module().community.storage.root));assert rebuilt.media(b['user']['id'],mid)[0].exists() and rebuilt.get_log(b['user']['id'],l['id'])['media'][0]['id']==mid
 api(client,b,'/blocks/'+a['user']['id'],{'enabled':True},'PUT');assert api(client,b,'/groups/'+g['id']+'/logs').json()['items']==[] and api(client,b,'/logs/'+l['id']).status_code==404
