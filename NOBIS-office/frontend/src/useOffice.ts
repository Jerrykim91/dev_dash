import {useCallback,useEffect,useRef} from 'react';
import {useOfficeStore} from './stores/officeStore';
import {bridge,emit} from './game/bridge';
import type {Session} from './game/types';
export function useOffice(session:Session) {
 const socket=useRef<WebSocket|null>(null),requestedChannel=useRef<string|undefined>(undefined),reconnect=useRef<()=>void>(()=>{});
 const send=useCallback((message:unknown)=>{
  if(socket.current?.readyState!==WebSocket.OPEN||!useOfficeStore.getState().connected){const m=message as {type?:string;channel_id?:string};if(m.type==='world_channel_move'&&m.channel_id){requestedChannel.current=m.channel_id;reconnect.current();return true;}return false;}
  socket.current.send(JSON.stringify(message));return true;
 },[]);
 useEffect(()=>{
  let receivedChannels=false;
  let active=true,retry:ReturnType<typeof setTimeout>|undefined,attempt=0;
  const state=()=>useOfficeStore.getState();
  state().setConnection(false,'서버에 연결 중…');
  const connect=()=>{
   if(!active)return;
   const ws=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws`);socket.current=ws;
   ws.onopen=()=>ws.send(JSON.stringify({token:session.token,channel_id:requestedChannel.current}));
   ws.onmessage=event=>{
    if(!active||socket.current!==ws)return;
    let m;try{m=JSON.parse(event.data);}catch{return;}
    if(m.world_channels||m.type==='world_channels')receivedChannels=true;
    if(m.type==='snapshot'){state().setVisitedMap(m.scope_map??null);if(m.dashboard_config)state().setDashboardConfig(m.dashboard_config);if(m.world_channels)state().setWorldChannels(m.world_channels);if(m.world_channel_id){requestedChannel.current=m.world_channel_id;state().setWorldChannel(m.world_channel_id);}if(m.chat_preferences)state().setPreferences(m.chat_preferences);if(m.announcements)state().setAnnouncements(m.announcements);if(m.private_messages)state().history('private',m.private_messages);if(m.home_state)state().setHomeState(m.home_state);attempt=0;state().snapshot(m.players,m.zones,m.channels,m.room_settings,m.room_instance_id?{room_instance_id:m.room_instance_id,room_type:m.room_type,room_counts:m.room_counts??{},office_map:m.office_map??null,world_revision:m.world_revision}:undefined);const p=m.players.find((p:{id:string})=>p.id===session.user.id);if(p)emit('correction',{zone:p.zone,scope:p.scope,x:p.x,y:p.y});}
    if(['joined','moved','status','zone_changed','presence','action','scope_changed'].includes(m.type)){
     state().upsert(m.player);
     if(m.type==='status'&&m.player.id===session.user.id&&m.player.participation_mode==='spectator')emit('correction',{zone:m.player.zone,scope:m.player.scope,x:m.player.x,y:m.player.y});
    }
    if(m.type==='zone_snapshot')for(const player of m.players)state().upsert(player);
    if(m.type==='admission_denied'){state().setWorldChannels(m.world_channels);state().setConnection(false,m.message);emit('hint',m.message);}
    if(m.type==='room_counts')state().setRoomCounts(m.counts);
    if(m.type==='world_channels')state().setWorldChannels(m.channels);
    if(m.type==='chat_preferences')state().setPreferences(m.preferences);
    if(m.type==='home_layout'&&m.scope===state().scope)state().setVisitedMap(m.map);
    if(m.type==='integration_refresh')emit('social-refresh',{});
    if(m.type==='social_refresh')emit('social-refresh',{});
    if(m.type==='private_message'){state().addChat(m.chat);if(m.chat.user_id!==session.user.id)state().addNotification({id:'private-'+m.chat.id,kind:'private',message:`${m.chat.nickname}님의 귓속말`,channel:'private'});}
    if(m.type==='private_delivered')state().delivered(m.id);
    if(m.type==='message_deleted')state().deleteMessage(m.id);
    if(m.type==='announcement')state().addAnnouncement(m.announcement);
    if(m.type==='chat_bubble')emit('chat-bubble',m);
    if(m.type==='bubble_clear')emit('bubble-clear',m.user_id);
    if(m.type==='left')state().remove(m.id);
    if(m.type==='chat'){
     state().addChat(m.chat);

    }
    if(m.type==='notification')state().addNotification(m.notification);
    if(m.type==='home_state')state().setHomeState(m.state);
    if(m.type==='channels')state().setChannels(m.channels);
    if(m.type==='channel_created'||m.type==='channel_accepted')state().selectChannel(m.channel_id);
    if(m.type==='channel_revoked')state().revokeChannel(m.channel_id);
    if(m.type==='history')state().history(m.channel,m.messages);
    if(m.type==='object_effect'&&m.scope===state().scope)emit('object-effect',m);
    if(m.type==='correction')emit('correction',m);
    if(m.type==='interaction')emit('interaction',m.interaction);
    if(m.type==='error'){state().setConnection(true,m.message);emit('hint',m.message);}
   };
   ws.onclose=e=>{
    if(!active||socket.current!==ws)return;
    if(e.code===1008){state().logout();return;}
    if(e.code===4001||e.code===4003){state().setConnection(false,e.reason||'접속할 수 없어요.');return;}
    state().setConnection(false,'연결이 끊겼어요. 다시 연결 중…');retry=setTimeout(connect,Math.min(1000*2**attempt++,10000));
   };
   ws.onerror=()=>state().setConnection(false,'서버에 연결할 수 없어요.');
  };
  reconnect.current=()=>{clearTimeout(retry);const old=socket.current;socket.current=null;old?.close();connect();};
  fetch('/api/world-channels',{headers:{Authorization:`Bearer ${session.token}`}}).then(r=>r.ok?r.json():null).then(channels=>{if(active&&channels&&!receivedChannels)state().setWorldChannels(channels);}).catch(()=>{});
  connect();
  const position=(e:Event)=>send({type:'move',...(e as CustomEvent).detail});
  const interaction=(e:Event)=>send({type:'interact',object_id:(e as CustomEvent).detail});
  bridge.addEventListener('position',position);bridge.addEventListener('interact',interaction);
  const heartbeat=setInterval(()=>send({type:'ping'}),20000);
  const visibility=()=>send({type:'presence',presence:document.hidden?'away':'online'});
  document.addEventListener('visibilitychange',visibility);
  return()=>{active=false;reconnect.current=()=>{};clearTimeout(retry);clearInterval(heartbeat);bridge.removeEventListener('position',position);bridge.removeEventListener('interact',interaction);document.removeEventListener('visibilitychange',visibility);const ws=socket.current;socket.current=null;if(ws?.readyState===WebSocket.CONNECTING)ws.addEventListener('open',()=>ws.close(),{once:true});else ws?.close();};
 },[session,send]);
 return send;
}
