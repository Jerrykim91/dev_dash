import {AvatarPortrait} from '../design/AvatarPortrait';
import {characterVariant,partsManifest} from '../game/visual/catalog';
import type {AvatarParts} from '../game/types';
import {useEffect,useState,type FormEvent} from 'react';
import {useOfficeStore} from '../stores/officeStore';
import {workStatusLabels,type WorkStatus} from '../game/types';
export function WorkStatusIndicator({send}:{send:(message:unknown)=>boolean}) {
 const {session,players,connected}=useOfficeStore();const own=players.find(p=>p.id===session?.user.id);
 const [status,setStatus]=useState<WorkStatus>('working'),[message,setMessage]=useState('');
 useEffect(()=>{if(own){setStatus(own.work_status??'working');setMessage(own.message);}},[own?.work_status,own?.message]);
 function submit(e:FormEvent){e.preventDefault();send({type:'status',work_status:status,message});}
 return <section className="status-panel"><p className="panel-label">MY STATUS <span>테스트 상태</span></p><div className="my-profile"><span className="large-avatar" aria-hidden="true"><AvatarPortrait faceOnly variant={own?characterVariant(own.avatar.palette,own.id):0}/></span><div><strong>{session?.user.nickname}</strong><small>{own?.presence==='away'?'자리 비움':'온라인'} · {own?.participation_mode==='spectator'?'관람자':'일반 참여'}</small></div></div><form onSubmit={submit}><label htmlFor="work-status">근무 상태</label><select id="work-status" value={status} onChange={e=>setStatus(e.target.value as WorkStatus)} disabled={!connected}>{Object.entries(workStatusLabels).map(([v,label])=><option key={v} value={v}>{label}</option>)}</select><label htmlFor="status-message">상태 메시지 · 말풍선</label><div className="status-input"><input id="status-message" maxLength={60} value={message} onChange={e=>setMessage(e.target.value)} placeholder="지금의 상태를 알려주세요" disabled={!connected}/><button aria-label="상태 저장" disabled={!connected}>✓</button></div></form><small className="field-note">직접 설정한 테스트 상태예요. 실제 업무 활동을 추정하지 않습니다.</small>{partsManifest&&<Wardrobe send={send} parts={own?.avatar.parts} disabled={!connected}/>}</section>;
}

/** 옷 갈아입기: 머리·상의·하의를 고르면 바로 적용(실행 중 겹치기). '기본 외형'은 팔레트로 정해진 완성 캐릭터 */
function Wardrobe({send,parts,disabled}:{send:(message:unknown)=>boolean;parts?:AvatarParts;disabled:boolean}){
 const m=partsManifest!,fallback:AvatarParts={hair:m.hair[0],top:m.tops[0],bottom:m.bottoms[0]};
 // 선택 값은 화면 쪽 상태로 들고 있는다(빠르게 연달아 고를 때 서버 응답 전의 옛 값으로 덮어쓰지 않게). 서버 값이 바뀌면 따라간다
 const [sel,setSel]=useState<AvatarParts>(parts??fallback),key=JSON.stringify(parts??null);
 useEffect(()=>{if(parts)setSel(parts);},[key]);
 const current=sel;
 const apply=(next:AvatarParts|null)=>send({type:'avatar_parts',parts:next});
 const pick=(k:keyof AvatarParts,value:string)=>{const next={...sel,[k]:value};setSel(next);apply(next);};
 const field=(key:keyof AvatarParts,label:string,ids:string[],labels:Record<string,string>)=><label key={key} className="wardrobe-field"><span>{label}</span><select id={`wardrobe-${key}`} value={parts?current[key]:''} disabled={disabled} onChange={e=>pick(key,e.target.value)}>{!parts&&<option value="">선택</option>}{ids.map(id=><option key={id} value={id}>{labels[id]??id}</option>)}</select></label>;
 // 기본은 접힘: 오른쪽 패널(채팅 입력)을 밀어내지 않게
 return <details className="wardrobe"><summary>옷 갈아입기{parts?' · 착용 중':''}</summary><div className="wardrobe-body" role="group" aria-label="옷 갈아입기">{field('hair','머리',m.hair,m.labels.hair)}{field('top','상의',m.tops,m.labels.top)}{field('bottom','하의',m.bottoms,m.labels.bottom)}{parts?<button type="button" className="wardrobe-reset" disabled={disabled} onClick={()=>apply(null)}>기본 외형으로</button>:<button type="button" className="wardrobe-reset" disabled={disabled} onClick={()=>apply(current)}>입어 보기</button>}</div></details>;
}
