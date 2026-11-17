import {useEffect,useState} from 'react';
import {useOfficeStore,channelId} from '../stores/officeStore';
import {ChatInput} from './ChatInput';
import {ChatMessageList} from './ChatMessageList';
import {Modal} from './Modal';
import type {DirectoryUser} from '../game/types';
import {ChannelManager} from './ChannelManager';
import {bridge,emit} from '../game/bridge';
export function ChatPanel({send}:{send:(message:unknown)=>boolean}) {
 const {roomInstanceId,channel,selectChannel,space,scope,players,session,messages,unread,connected,zones,channels,roomSettings,worldChannelId}=useOfficeStore();
 const [manager,setManager]=useState(false),[kind,setKind]=useState<'cafe'|'meeting'|undefined>(),[inviteId,setInviteId]=useState('');
 const id=channelId(channel,space,scope,worldChannelId,roomInstanceId),own=players.find(p=>p.id===session?.user.id),room=channels.find(c=>c.id===channel);
 const location=scope.startsWith('personal:')?(roomSettings?.name??'개인 작업실'):zones.find(z=>z.id===space)?.name??'공용 통로';
 useEffect(()=>{if(connected)send({type:'history',channel:id});},[id,connected,send]);
 useEffect(()=>{const open=(e:Event)=>{setKind((e as CustomEvent<'cafe'|'meeting'>).detail);setManager(true);};bridge.addEventListener('open-channels',open);return()=>bridge.removeEventListener('open-channels',open);},[]);
 const [directory,setDirectory]=useState<DirectoryUser[]>([]);
 useEffect(()=>{if(!room||!connected)return;const controller=new AbortController();fetch('/api/directory',{headers:{Authorization:`Bearer ${session?.token}`},signal:controller.signal}).then(r=>r.ok?r.json():[]).then(setDirectory).catch(()=>{});return()=>controller.abort();},[room?.id,connected,session?.token]);
 const invites=channels.filter(c=>c.membership==='invited').length;
 const canWrite=connected&&(!room||(room.membership==='active'&&room.status==='open'));
 const candidates=directory.filter(p=>p.id!==session?.user.id&&!room?.members.some(m=>m.user_id===p.id&&m.state!=='left'));
 return <section className="chat-panel"><div className="chat-heading"><h2>실시간 채팅</h2><button className="rooms-button" onClick={()=>{setKind(undefined);setManager(true);}}>대화방 {invites>0&&<span>{invites}</span>}</button></div><div className="chat-tabs" role="tablist" aria-label="채팅 채널">{([['world','월드'],['channel','채널'],['zone','현재 존'],['private','귓속말']] as const).map(([value,label])=><button key={value} role="tab" aria-label={label} aria-selected={value===channel} onClick={()=>selectChannel(value)}>{label}{(unread[channelId(value,space,scope,worldChannelId,roomInstanceId)]??0)>0&&<i>{unread[channelId(value,space,scope,worldChannelId,roomInstanceId)]}</i>}</button>)}</div>
 {room&&<div className="private-channel"><strong>{room.name}</strong><span>{room.kind==='meeting'?'참석자 전용 회의':'카페 비공개'} · {room.status==='closed'?'종료 · 기록만 조회':'참여자 전용'}</span><details><summary>참여자와 초대</summary>{room.members.map(m=><p key={m.user_id}>{m.nickname} · {m.state==='invited'?'초대 대기':m.role==='owner'?'소유자':'참여 중'}</p>)}{room.owner_id===session?.user.id&&room.status==='open'&&<div className="invite-row"><label className="sr-only" htmlFor="invite-user">초대할 사용자</label><select id="invite-user" value={inviteId} onChange={e=>setInviteId(e.target.value)}><option value="">사용자 선택</option>{candidates.map(p=><option value={p.id} key={p.id}>{p.nickname}</option>)}</select><button disabled={!inviteId} onClick={()=>{send({type:'channel_invite',channel_id:room.id,user_id:inviteId});setInviteId('');}}>초대</button></div>}{room.owner_id===session?.user.id?<button disabled={room.status==='closed'} onClick={()=>send({type:'channel_close',channel_id:room.id})}>{room.kind==='meeting'?'회의 종료':'대화 종료'}</button>:<button onClick={()=>send({type:'channel_leave',channel_id:room.id})}>대화 나가기</button>}</details></div>}
 <p className="chat-notice">{room?'초대 수락한 참여자만 메시지와 기록을 볼 수 있어요.':channel==='world'?'다른 존에 있는 사람들과도 대화할 수 있어요.':channel==='zone'?`${location}에 있는 사람들에게만 전달돼요.`:channel==='channel'?'같은 채널의 모든 존에서 대화할 수 있어요.':'@닉네임 메시지는 수신자와 나에게만 표시됩니다.'}</p><ChatMessageList messages={messages.filter(m=>m.channel===id)} userId={session!.user.id} channel={id}/><ChatInput disabled={!canWrite} players={players} onSend={(text,recipients)=>{if(text.startsWith('@')){const ok=send({type:'private_message',text,...(recipients[0]?{recipient_id:recipients[0]}:{})});if(ok)selectChannel('private');return ok;}if(channel==='private'){emit('hint','@닉네임 메시지로 귓속말을 보내세요.');return false;}return send({type:'chat',channel:id,text});}}/><small className="chat-footnote">기록은 접근 권한이 있는 대화에서만 조회할 수 있어요.</small>
 {manager&&<Modal title="대화방 관리" onClose={()=>setManager(false)}><ChannelManager send={send} initialKind={kind} onClose={()=>setManager(false)}/></Modal>}
 </section>;
}
