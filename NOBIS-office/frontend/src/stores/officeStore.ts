import {create} from 'zustand';
import type {Chat,Notification,Player,Session,Zone,PrivateChannel,PersonalRoomSettings,HomeState,WorldChannel,Announcement,ChatPreferences,DashboardConfig,MapData} from '../game/types';
const SESSION_KEY='nobis.v2.session';
function storedSession():Session|null {try{const s=JSON.parse(sessionStorage.getItem(SESSION_KEY)??'null');return s?.token&&s?.user?.id?s:null;}catch{return null;}}
export function channelId(channel:string,space:string,scope:string,worldChannelId='ch1',roomInstanceId=''){return channel==='channel'?`channel:${worldChannelId}`:channel==='zone'&&roomInstanceId.startsWith('meeting:')?'zone:'+roomInstanceId:channel==='zone'?`zone:${scope.startsWith('personal:')?scope:worldChannelId==='ch1'?space:`${worldChannelId}:${space}`}`:channel;}
interface OfficeState {
 roomInstanceId:string;roomType:string;roomCounts:Record<string,number>;setRoom:(id:string,type:string,counts:Record<string,number>)=>void;setRoomCounts:(counts:Record<string,number>)=>void;
 officeMap:MapData|null;worldRevision:string;setOfficeMap:(map:MapData|null,revision:string)=>void;
 dashboardConfig:DashboardConfig;setDashboardConfig:(config:DashboardConfig)=>void;
 worldChannelId:string;worldChannels:WorldChannel[];announcements:Announcement[];announcementQueue:Announcement[];preferences:ChatPreferences;
 setWorldChannels:(c:WorldChannel[])=>void;setWorldChannel:(id:string)=>void;setPreferences:(p:ChatPreferences)=>void;addAnnouncement:(a:Announcement)=>void;setAnnouncements:(a:Announcement[])=>void;dismissAnnouncement:()=>void;delivered:(id:string)=>void;deleteMessage:(id:string)=>void;

 visitedMap:HomeState['map']|null;setVisitedMap:(map:HomeState['map']|null)=>void;
 homeState:HomeState|null;decorating:boolean;setHomeState:(state:HomeState)=>void;setDecorating:(active:boolean)=>void;
 session:Session|null;players:Player[];zones:Zone[];space:string;scope:string;connected:boolean;notice:string;
 viewMode:'world'|'chat';channel:string;messages:Chat[];unread:Record<string,number>;notifications:Notification[];
 channels:PrivateChannel[];roomSettings:PersonalRoomSettings|null;
 login:(s:Session)=>void;logout:()=>void;snapshot:(players:Player[],zones:Zone[],channels?:PrivateChannel[],settings?:PersonalRoomSettings,world?:{room_instance_id:string;room_type:string;room_counts:Record<string,number>;office_map:MapData|null;world_revision:string})=>void;
 upsert:(p:Player)=>void;remove:(id:string)=>void;addChat:(chat:Chat)=>void;history:(channel:string,messages:Chat[])=>void;
 addNotification:(n:Notification)=>void;clearNotifications:()=>void;setChannels:(c:PrivateChannel[])=>void;revokeChannel:(id:string)=>void;
 setRoomSettings:(settings:PersonalRoomSettings)=>void;
 setConnection:(connected:boolean,notice:string)=>void;setView:(mode:'world'|'chat')=>void;selectChannel:(channel:string)=>void;
}
const initial={roomInstanceId:'',roomType:'lobby',roomCounts:{},officeMap:null,worldRevision:'',dashboardConfig:{environment:'unknown',default_url:'',allow_local:false},worldChannelId:'ch1',worldChannels:[],announcements:[],announcementQueue:[],preferences:{chat_bubbles_enabled:false},visitedMap:null,homeState:null,decorating:false,players:[],zones:[],space:'office',scope:'office',connected:false,notice:'서버에 연결 중…',viewMode:'world' as const,channel:'world',messages:[],unread:{},notifications:[],channels:[],roomSettings:null};
export const useOfficeStore=create<OfficeState>()((set,get)=>({
 ...initial,session:storedSession(),setRoom:(roomInstanceId,roomType,roomCounts)=>set(s=>({roomInstanceId,roomType,roomCounts,...(s.roomInstanceId&&s.roomInstanceId!==roomInstanceId?{channel:'zone'}:{})})),setRoomCounts:roomCounts=>set({roomCounts}),setOfficeMap:(officeMap,worldRevision)=>set(s=>({officeMap:officeMap??s.officeMap,worldRevision})),setDashboardConfig:dashboardConfig=>set({dashboardConfig}),
 setWorldChannels:worldChannels=>set({worldChannels}),setWorldChannel:worldChannelId=>set(s=>({worldChannelId,announcementQueue:s.announcementQueue.filter(a=>!a.target_channel_id||a.target_channel_id===worldChannelId)})),setPreferences:preferences=>set({preferences}),
 addAnnouncement:a=>set(s=>({announcements:[a,...s.announcements.filter(v=>v.id!==a.id)].slice(0,100),announcementQueue:s.announcementQueue.some(v=>v.id===a.id)?s.announcementQueue:[...s.announcementQueue,a]})),setAnnouncements:announcements=>set({announcements}),dismissAnnouncement:()=>set(s=>({announcementQueue:s.announcementQueue.slice(1)})),
 delivered:id=>set(s=>({messages:s.messages.map(m=>m.id===id?{...m,delivery:'delivered'}:m)})),deleteMessage:id=>set(s=>({messages:s.messages.map(m=>m.id===id?{...m,text:'[관리자가 삭제한 메시지]'}:m)})),
 setVisitedMap:visitedMap=>set({visitedMap}),setHomeState:homeState=>set({homeState}),setDecorating:decorating=>set({decorating}),
 login:s=>{sessionStorage.setItem(SESSION_KEY,JSON.stringify(s));set({...initial,session:s});},
 logout:()=>{sessionStorage.removeItem(SESSION_KEY);set({...initial,session:null});},
 snapshot:(players,zones,channels=[],settings,world)=>{const own=players.find(p=>p.id===get().session?.user.id);set({players,zones,space:own?.zone??'office',scope:own?.scope??'office',connected:true,notice:'연결됨',channels,...(settings?{roomSettings:settings}:{}),...(world?{roomInstanceId:world.room_instance_id,roomType:world.room_type,roomCounts:world.room_counts,officeMap:world.office_map??get().officeMap,worldRevision:world.world_revision,...(get().roomInstanceId&&get().roomInstanceId!==world.room_instance_id?{channel:'zone'}:{})}:{})});},
 upsert:p=>set(s=>{
  const own=p.id===s.session?.user.id,changed=own&&(p.zone!==s.space||p.scope!==s.scope||p.room_instance_id!==s.roomInstanceId);
  return {players:[...s.players.filter(v=>v.id!==p.id),p],...(own?{space:p.zone,scope:p.scope??'office'}:{}),...(changed?{channel:'zone',unread:{...s.unread,[channelId('zone',p.zone,p.scope??'office',s.worldChannelId,s.roomInstanceId)]:0}}:{})};
 }),
 remove:id=>set(s=>({players:s.players.filter(p=>p.id!==id)})),
 addChat:chat=>set(s=>{if(s.messages.some(c=>c.id===chat.id))return s;const active=channelId(s.channel,s.space,s.scope,s.worldChannelId,s.roomInstanceId),unread={...s.unread};if(chat.channel!==active)unread[chat.channel]=(unread[chat.channel]??0)+1;return {messages:[...s.messages.slice(-299),chat],unread};}),
 history:(channel,messages)=>set(s=>{const byId=new Map([...messages,...s.messages.filter(m=>m.channel===channel)].map(m=>[m.id,m]));const merged=[...byId.values()].sort((a,b)=>((a as Chat&{seq?:number}).seq??0)-((b as Chat&{seq?:number}).seq??0));return {messages:[...s.messages.filter(m=>m.channel!==channel),...merged].slice(-500)};}),
 addNotification:n=>set(s=>({notifications:[...s.notifications.slice(-29),n]})),clearNotifications:()=>set({notifications:[]}),
 setChannels:channels=>set(s=>({channels,...(s.channel.startsWith('room:')&&!channels.some(c=>c.id===s.channel&&c.membership==='active')?{channel:'world'}:{})})),
 revokeChannel:id=>set(s=>({messages:s.messages.filter(m=>m.channel!==id),channels:s.channels.filter(c=>c.id!==id),...(s.channel===id?{channel:'world'}:{})})),
 setRoomSettings:roomSettings=>set({roomSettings}),
 setConnection:(connected,notice)=>set({connected,notice}),setView:viewMode=>set({viewMode}),
 selectChannel:channel=>set(s=>({channel,unread:{...s.unread,[channelId(channel,s.space,s.scope,s.worldChannelId,s.roomInstanceId)]:0}})),
}));
