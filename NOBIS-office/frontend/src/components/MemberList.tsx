import {AvatarPortrait} from '../design/AvatarPortrait';
import {characterVariant} from '../game/visual/catalog';
import {useOfficeStore} from '../stores/officeStore';
import type {Player} from '../game/types';
export function MemberList({onProfile}:{onProfile:(p:Player)=>void}) {
 const {players,zones}=useOfficeStore();
 return <details className="member-list"><summary>접속자 목록 <span>{players.length} / 15</span></summary><div>{players.map(p=><button key={p.id} className="member-row" onClick={()=>onProfile(p)}><span className="mini-avatar" aria-hidden="true"><AvatarPortrait faceOnly variant={characterVariant(p.avatar.palette,p.id)}/></span><span>{p.nickname}<small>{p.profile_location_visible===false?'위치 비공개':zones.find(z=>z.id===p.zone)?.name??'다른 사용자의 개인 방'} · {p.minigame?'미니게임 중':p.participation_mode==='spectator'?'관람자':p.presence==='away'?'자리 비움':'참여 중'}</small></span></button>)}</div></details>;
}
