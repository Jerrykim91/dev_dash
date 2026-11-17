import {useEffect,useState} from 'react';
import {useOfficeStore} from '../stores/officeStore';
import {ChannelManager} from './ChannelManager';
export function MeetingRoomLobby({send}:{send:(message:unknown)=>boolean}){
 const {session,channels}=useOfficeStore();const[rows,setRows]=useState<any[]>([]),[error,setError]=useState('');
 useEffect(()=>{let active=true;fetch('/api/rooms',{headers:{Authorization:`Bearer ${session!.token}`}}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{if(active)setRows(data.filter((r:any)=>r.room_type==='meeting'));}).catch(()=>setError('회의실 목록을 불러오지 못했어요.'));return()=>{active=false;};},[session,channels]);
 return <section className="meeting-room-lobby"><p>초대를 수락한 참석자만 열린 회의실에 들어갈 수 있어요.</p>{rows.length===0&&<p>참여 중인 회의가 없습니다. 아래에서 회의를 만들거나 초대를 수락해 주세요.</p>}{rows.map(row=><article className="channel-card" key={row.room_instance_id}><div><strong>{row.name}</strong><small>{row.status==='closed'?'종료된 회의':`${row.occupancy} / ${row.max_occupancy}명 · ${row.membership==='active'?'참석자':'초대 대기'}`}</small><small>회의 ID · {row.room_id}</small></div><button disabled={!row.can_enter||row.occupancy>=row.max_occupancy} onClick={()=>send({type:'meeting_enter',meeting_id:row.room_id})}>회의실 입장</button></article>)}<details><summary>회의 만들기 · 초대 관리</summary><ChannelManager send={send} initialKind="meeting" onClose={()=>{}}/></details><p role="alert" className="error">{error}</p></section>;
}
