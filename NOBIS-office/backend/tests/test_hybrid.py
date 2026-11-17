from contextlib import ExitStack
import pytest
from test_server import client,login,auth,headers
from app.rooms import instance_id,chat_id
from app.world import ROOM_DATA,walkable

def module():
 import app.main as m
 return m

def receive(ws,kind):
 for _ in range(150):
  m=ws.receive_json()
  if m['type']==kind:return m
  if m['type'] in ['error','correction'] and kind!=m['type']:raise AssertionError(m)
 raise AssertionError('missing '+kind)

def position(user,p):
 peer=module().hub.peers[user['user']['id']];peer.player.update(**p);peer.moved-=1;peer.move_credit=.8

def exit_room(ws,user):
 p=module().hub.peers[user['user']['id']].player
 if p['room_type']=='lobby':return
 position(user,module().rooms.map(p)['spawn']);ws.send_json({'type':'interact','object_id':'room-exit'});receive(ws,'snapshot')

def enter(ws,user,typ):
 exit_room(ws,user);d=module().rooms.defs[typ];position(user,d['lobby_return']);ws.send_json({'type':'interact','object_id':d['portal_id']});return receive(ws,'snapshot')

def test_lobby_cafe_exit_reconnect_and_room_position_privacy(client):
 a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  sa=auth(wa,a);auth(wb,b);assert sa['room_type']=='lobby' and sa['office_map']['room_type']=='lobby'
  ca=enter(wa,a,'cafe');assert ca['room_type']=='cafe' and ca['office_map']['room_type']=='cafe'
  assert [p['id']for p in client.get('/api/users',headers=headers(a)).json()]==[a['user']['id']]
  assert [p['id']for p in client.get('/api/users',headers=headers(b)).json()]==[b['user']['id']]
  cb=enter(wb,b,'cafe');assert len(cb['players'])==2
  p=module().hub.peers[a['user']['id']].player;neighbors=[(p['x']+1,p['y']),(p['x'],p['y']+1),(p['x']-1,p['y'])];tx,ty=next(n for n in neighbors if walkable('office',*n,ROOM_DATA['maps']['cafe']));x=p['x']+(tx-p['x'])*.2;y=p['y']+(ty-p['y'])*.2
  wa.send_json({'type':'move','scope':'office','channel_id':'ch1','zone':'fake','x':x,'y':y,'direction':'east','moving':True});m=receive(wa,'moved');assert m['player']['zone']=='cafe';receive(wb,'moved')
  exit_room(wa,a);p=module().hub.peers[a['user']['id']].player;assert {'x':p['x'],'y':p['y']}==module().rooms.defs['cafe']['lobby_return']
  enter(wa,a,'focus')
 with client.websocket_connect('/ws') as ws:
  s=auth(ws,a);assert s['room_type']=='focus' and s['office_map']['room_type']=='focus'

def test_entry_proximity_capacity_failure_is_atomic(client,monkeypatch):
 a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);wa.send_json({'type':'interact','object_id':'portal-cafe'});assert receive(wa,'error');assert module().hub.peers[a['user']['id']].player['room_type']=='lobby'
  monkeypatch.setitem(module().rooms.defs['cafe'],'max_occupancy',1);enter(wa,a,'cafe');d=module().rooms.defs['cafe'];position(b,d['lobby_return']);before=dict(module().hub.peers[b['user']['id']].player)
  wb.send_json({'type':'interact','object_id':'portal-cafe'});assert receive(wb,'error');after=module().hub.peers[b['user']['id']].player;assert instance_id(before)==instance_id(after) and before['x']==after['x']

def test_world_channel_room_chat_whisper_and_focus_bubble_rules(client):
 a,b=login(client,'A'),login(client,'B')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);enter(wa,a,'cafe');uid=a['user']['id'];p=module().hub.peers[uid].player
  wa.send_json({'type':'chat','channel':'world','text':'all rooms'});receive(wa,'chat');assert receive(wb,'chat')['chat']['text']=='all rooms'
  module().hub.peers[uid].chatted=0;wb.send_json({'type':'chat','channel':chat_id(p),'text':'forged room'});assert receive(wb,'error')
  wa.send_json({'type':'private_message','recipient_id':b['user']['id'],'text':'@B across rooms'});receive(wa,'private_message');assert receive(wb,'private_message')['chat']['text']=='across rooms'
  enter(wa,a,'focus');assert not module().rooms.zones(module().hub.peers[uid].player)[0]['chat_bubbles_allowed']

def test_meeting_acl_closed_eviction_and_home_return_to_same_room(client):
 a,b,c=login(client,'Owner'),login(client,'Member'),login(client,'Outsider');m=module();cid=m.repository.create_channel(a['user']['id'],'meeting','Planning');m.repository.invite(cid,a['user']['id'],b['user']['id']);m.repository.accept(cid,b['user']['id'])
 with ExitStack()as stack:
  wa,wb,wc=[stack.enter_context(client.websocket_connect('/ws'))for _ in range(3)]
  for ws,u in[(wa,a),(wb,b),(wc,c)]:auth(ws,u);position(u,m.rooms.defs['meeting']['lobby_return'])
  wc.send_json({'type':'meeting_enter','meeting_id':cid});receive(wc,'error');assert m.hub.peers[c['user']['id']].player['room_type']=='lobby'
  for ws in[wa,wb]:ws.send_json({'type':'meeting_enter','meeting_id':cid});s=receive(ws,'snapshot');assert s['room_type']=='meeting' and not s['zones'][0]['chat_bubbles_allowed']
  assert len(m.hub.players_for(a['user']['id']))==2
  m.repository.close_channel(cid,a['user']['id']);receive(wa,'snapshot');assert m.hub.peers[a['user']['id']].player['room_type']=='lobby'
  enter(wa,a,'lounge');saved=dict(m.hub.peers[a['user']['id']].player);wa.send_json({'type':'room_enter'});s=receive(wa,'snapshot');assert s['room_type']=='home'
  wa.send_json({'type':'room_leave'});s=receive(wa,'snapshot');assert s['room_type']=='lounge' and s['players'][0]['room_instance_id']==saved['room_instance_id']

def test_each_room_independent_navigation_and_fifteen_seat_maps():
 from app.world import valid_move
 for typ,m in ROOM_DATA['maps'].items():
  floor={(p['x'],p['y'])for p in m['walkable_tiles']if walkable('office',p['x'],p['y'],m)};start=tuple(m['spawn'].values());seen={start};q=[start]
  for p in q:
   for n in[(p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)]:
    if n in floor and n not in seen:seen.add(n);q.append(n)
  assert seen==floor,typ
  assert not valid_move('office',start,(m['width']+1,m['height']+1),.1,m)
 assert len(ROOM_DATA['maps']['focus']['workstations'])==15
 assert len(ROOM_DATA['maps']['meeting']['meeting_seats'])==15

def test_fifteen_focus_seats_and_disconnection_cleanup(client):
 m=module();users=[login(client,'HybridSeat'+str(i))for i in range(15)]
 with ExitStack()as stack:
  sockets=[stack.enter_context(client.websocket_connect('/ws'))for _ in users]
  for ws,u in zip(sockets,users):auth(ws,u)
  for ws,u,station in zip(sockets,users,ROOM_DATA['maps']['focus']['workstations']):
   enter(ws,u,'focus');position(u,station['approach']);ws.send_json({'type':'interact','object_id':station['chair_id']})
   while True:
    data=receive(ws,'action')
    if data['player']['id']==u['user']['id']:break
   assert data['player']['action']=='sitting'
  peers=list(m.hub.peers.values());assert len(peers)==15 and len({p.player['active_object']for p in peers})==15
 assert not m.hub.peers


def test_other_users_home_entry_does_not_resnapshot_or_interrupt_current_room(client):
 from test_social import frames
 a,b=login(client,'Walking'),login(client,'Going home')
 with client.websocket_connect('/ws') as wa,client.websocket_connect('/ws') as wb:
  auth(wa,a);auth(wb,b);frames(wa);frames(wb)
  wb.send_json({'type':'room_enter'});receive(wb,'snapshot')
  messages=frames(wa);assert not any(m['type']=='snapshot' for m in messages)
  assert any(m['type']=='left' and m['id']==b['user']['id'] for m in messages)
  assert not any('player' in m and m['player']['id']==b['user']['id'] for m in messages)


def test_meeting_chat_acl_is_rechecked_immediately_before_presence_eviction(client):
 a=login(client,'Meeting chat owner');m=module();cid=m.repository.create_channel(a['user']['id'],'meeting','Immediate ACL')
 with client.websocket_connect('/ws') as ws:
  auth(ws,a);position(a,m.rooms.defs['meeting']['lobby_return']);ws.send_json({'type':'meeting_enter','meeting_id':cid});receive(ws,'snapshot')
  peer=m.hub.peers[a['user']['id']];key=chat_id(peer.player);assert m.hub.can_read(peer,key)
  m.repository.close_channel(cid,a['user']['id'])
  assert not m.hub.can_read(peer,key) and not m.hub.can_write(peer,key)
  assert client.get('/api/channels/'+key+'/messages',headers=headers(a)).status_code==403
