import {AvatarPortrait} from '../design/AvatarPortrait';
import {characterVariant} from '../game/visual/catalog';
import {useEffect,useState,type FormEvent} from 'react';
import {useOfficeStore} from '../stores/officeStore';
import {workStatusLabels,type WorkStatus} from '../game/types';
export function WorkStatusIndicator({send}:{send:(message:unknown)=>boolean}) {
 const {session,players,connected}=useOfficeStore();const own=players.find(p=>p.id===session?.user.id);
 const [status,setStatus]=useState<WorkStatus>('working'),[message,setMessage]=useState('');
 useEffect(()=>{if(own){setStatus(own.work_status??'working');setMessage(own.message);}},[own?.work_status,own?.message]);
 function submit(e:FormEvent){e.preventDefault();send({type:'status',work_status:status,message});}
 return <section className="status-panel"><p className="panel-label">MY STATUS <span>테스트 상태</span></p><div className="my-profile"><span className="large-avatar" aria-hidden="true"><AvatarPortrait faceOnly variant={own?characterVariant(own.avatar.palette,own.id):0}/></span><div><strong>{session?.user.nickname}</strong><small>{own?.presence==='away'?'자리 비움':'온라인'} · {own?.participation_mode==='spectator'?'관람자':'일반 참여'}</small></div></div><form onSubmit={submit}><label htmlFor="work-status">근무 상태</label><select id="work-status" value={status} onChange={e=>setStatus(e.target.value as WorkStatus)} disabled={!connected}>{Object.entries(workStatusLabels).map(([v,label])=><option key={v} value={v}>{label}</option>)}</select><label htmlFor="status-message">상태 메시지 · 말풍선</label><div className="status-input"><input id="status-message" maxLength={60} value={message} onChange={e=>setMessage(e.target.value)} placeholder="지금의 상태를 알려주세요" disabled={!connected}/><button aria-label="상태 저장" disabled={!connected}>✓</button></div></form><small className="field-note">직접 설정한 테스트 상태예요. 실제 업무 활동을 추정하지 않습니다.</small></section>;
}
