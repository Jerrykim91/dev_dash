import {useEffect,useRef,useState} from 'react';
import {useOfficeStore} from '../stores/officeStore';
import {bridge,emit} from '../game/bridge';
import {layoutMap,placementError} from '../game/systems/PlacementSystem';
import type {FurnitureItem,FurniturePlacement,HomeState,Point} from '../game/types';
import {FurniturePreview} from './FurniturePreview';
import {Modal} from './Modal';
const categories:Record<string,string>={all:'전체',desk:'책상',chair:'의자',bed:'침대',sofa:'소파',bookshelf:'책장',plant:'화분',lamp:'스탠드',rug:'러그',computer:'컴퓨터',decoration:'장식'};
export function HomeTools(){
 const {session,scope,viewMode,connected,players,homeState:state,setHomeState,decorating,setDecorating}=useOfficeStore();
 const own=players.find(p=>p.id===session?.user.id),isHome=scope===`personal:${session?.user.id}`;
 const [draft,setDraft]=useState<FurniturePlacement[]>([]),[selected,setSelected]=useState(''),[point,setPoint]=useState<Point>({x:2,y:6}),[rotation,setRotation]=useState(0),[shop,setShop]=useState(false),[category,setCategory]=useState('all'),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[pending,setPending]=useState<{item:FurnitureItem;request:string}|null>(null),[history,setHistory]=useState(false);
 const revision=useRef(0);
 async function api(path:string,method='GET',body?:unknown){
  const r=await fetch(path,{method,headers:{Authorization:`Bearer ${session?.token}`,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
  const result=await r.json();if(!r.ok)throw new Error(typeof result.detail==='string'?result.detail:'요청을 처리하지 못했어요.');return result;
 }
 useEffect(()=>{
  if(!isHome||viewMode==='chat'||!connected||own?.participation_mode!=='normal'){setDecorating(false);setSelected('');}
 },[isHome,viewMode,connected,own?.participation_mode,setDecorating]);
 useEffect(()=>()=>{setDecorating(false);emit('decorate',{active:false});},[setDecorating]);
 useEffect(()=>{
  if(!decorating)return;
  const tile=(e:Event)=>setPoint((e as CustomEvent<Point>).detail);
  const select=(e:Event)=>{const id=(e as CustomEvent<string>).detail,p=draft.find(p=>p.instance_id===id);if(!p)return;setSelected(id);setPoint({x:p.grid_x,y:p.grid_y});setRotation(p.rotation);setMessage('가구를 옮길 바닥을 클릭한 뒤 배치 확정을 눌러 주세요.');};
  bridge.addEventListener('home-tile',tile);bridge.addEventListener('home-hover',tile);bridge.addEventListener('home-select',select);
  return()=>{bridge.removeEventListener('home-tile',tile);bridge.removeEventListener('home-hover',tile);bridge.removeEventListener('home-select',select);};
 },[decorating,draft]);
 const instance=state?.inventory.find(i=>i.id===selected),item=state?.catalog.find(i=>i.item_id===instance?.item_id);
 const candidate={instance_id:selected,grid_x:point.x,grid_y:point.y,rotation};
 const proposal=selected?[...draft.filter(p=>p.instance_id!==selected),candidate]:draft;
 const error=state?placementError(proposal,state.inventory,state.catalog,state.map,own):'';
 useEffect(()=>{
  if(!state||!isHome)return;
  const map=decorating?layoutMap(state.map,draft,state.inventory,state.catalog):state.map;
  const preview=decorating&&item?layoutMap(state.map,[candidate],state.inventory,state.catalog).objects.find(o=>o.id===selected):undefined;
  emit('decorate',{active:decorating,map,preview,valid:!error});
 },[decorating,draft,selected,point.x,point.y,rotation,state,isHome,error]);
 if(!isHome||!state||!session||viewMode==='chat')return null;
 function begin(){if(!state)return;revision.current=state.home.revision;setDraft(state.placements.map(p=>({...p})));setSelected('');setMessage('가구 선택 → 바닥 클릭 → 배치 확정 → 배치 저장');setDecorating(true);}
 function select(id:string){const p=draft.find(p=>p.instance_id===id);setSelected(id);setRotation(p?.rotation??0);if(p)setPoint({x:p.grid_x,y:p.grid_y});setMessage('초록색은 배치 가능, 빨간색은 배치 불가예요.');}
 async function save(){
  if(!state)return;setBusy(true);setMessage('');
  try{const result:HomeState=await api(`/api/homes/${encodeURIComponent(state.home.id)}/layout`,'PUT',{revision:revision.current,placements:draft.map(({instance_id,grid_x,grid_y,rotation})=>({instance_id,grid_x,grid_y,rotation}))});setHomeState(result);revision.current=result.home.revision;setDecorating(false);setSelected('');setMessage('배치를 저장했어요.');}
  catch(e){setMessage((e as Error).message);}finally{setBusy(false);}
 }
 async function buy(){
  if(!pending)return;setBusy(true);setMessage('');
  try{const result=await api('/api/shop/purchases','POST',{item_id:pending.item.item_id,request_id:pending.request});setHomeState(result.state);setMessage(`${pending.item.name} 구매 완료 · 인벤토리에 추가했어요.`);setPending(null);}
  catch(e){setMessage((e as Error).message);}finally{setBusy(false);}
 }
 const items=state.catalog.filter(i=>category==='all'||i.category===category);
 return <>
  <div className="home-toolbar"><span className="coin-balance" aria-label="NOBIS Coin 잔액">◉ {state.balance.toLocaleString()} <small>NOBIS Coin</small></span><button disabled={!connected||own?.participation_mode!=='normal'||busy} onClick={()=>decorating?undefined:begin()}>{decorating?'꾸미는 중':'집 꾸미기'}</button><button disabled={decorating||busy||!connected} onClick={()=>{setShop(true);setCategory('all');setMessage('');}}>가구 상점</button><button onClick={()=>setHistory(true)}>코인 내역</button></div>
  {decorating&&<section className="home-editor" aria-label="집 꾸미기"><div className="editor-heading"><strong>나의 가구</strong><span>선택 · 회전 · 배치</span></div><p className="field-note">미리보기는 저장 전까지 임시 배치예요.<br/>초록: 가능 · 빨강: 불가 · 이동은 일시 정지</p><label>가구 카테고리<select aria-label="인벤토리 카테고리" value={category} onChange={e=>setCategory(e.target.value)}>{Object.entries(categories).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label>
   <div className="inventory-grid">{items.map(i=>{const instances=state.inventory.filter(v=>v.item_id===i.item_id),installed=instances.filter(v=>draft.some(p=>p.instance_id===v.id));return instances.length>0&&<div key={i.item_id} className="inventory-group"><span>{i.name} · {instances.length}개 <small>설치 {installed.length}</small></span>{instances.map((v,index)=><button key={v.id} aria-label={`${i.name} ${index+1} 선택`} aria-pressed={selected===v.id} onClick={()=>select(v.id)} disabled={busy}><FurniturePreview item={i}/><span>{draft.some(p=>p.instance_id===v.id)?'설치 중':'미설치'} #{index+1}</span></button>)}</div>;})}</div>
   {item&&<div className="placement-controls"><strong>{item.name} · {item.size.width}×{item.size.height}</strong><div className="placement-coordinates"><label>X<input aria-label="배치 X 좌표" type="number" min={0} max={state.map.width-1} value={point.x} onChange={e=>setPoint({...point,x:Number(e.target.value)})}/></label><label>Y<input aria-label="배치 Y 좌표" type="number" min={0} max={state.map.height-1} value={point.y} onChange={e=>setPoint({...point,y:Number(e.target.value)})}/></label></div><p className={error?'error':'placement-valid'} role="status">{error||'배치 가능한 위치예요.'}</p><div className="editor-actions"><button disabled={!item.rotatable||busy} onClick={()=>setRotation((rotation+90)%360)}>회전 {rotation}°</button><button disabled={!!error||busy} onClick={()=>{setDraft(proposal);setSelected('');setMessage('임시 배치 완료. 배치 저장을 눌러 반영하세요.');}}>배치 확정</button><button disabled={busy||!draft.some(p=>p.instance_id===selected)} onClick={()=>{setDraft(draft.filter(p=>p.instance_id!==selected));setSelected('');setMessage('가구를 회수했어요. 배치 저장 후 반영됩니다.');}}>가구 회수</button></div></div>}
   <p role="status" className="editor-message">{message}</p><div className="editor-actions"><button className="primary" disabled={busy||!!placementError(draft,state.inventory,state.catalog,state.map,own)} onClick={save}>{busy?'저장 중…':'배치 저장'}</button><button disabled={busy} onClick={()=>{setDecorating(false);setSelected('');setMessage('');}}>취소 · 종료</button><button disabled={busy} onClick={async()=>{try{const result=await api('/api/home');setHomeState(result);revision.current=result.home.revision;setDraft(result.placements);setSelected('');setMessage('최신 배치를 불러왔어요.');}catch(e){setMessage((e as Error).message);}}}>최신 배치 불러오기</button></div>
  </section>}
  {shop&&<Modal title="NOBIS 가구 상점" onClose={()=>{if(!busy){setShop(false);setPending(null);}}}><p className="shop-balance">◉ {state.balance.toLocaleString()} NOBIS Coin</p><p className="field-note">내 집에 배치할 가구예요. 개발 환경은 최초 1,000코인을 지급합니다.</p>{pending?<div className="purchase-confirm"><FurniturePreview item={pending.item}/><h3>{pending.item.name}</h3><p>{pending.item.price} NOBIS Coin으로 구매할까요?</p><button className="primary" disabled={busy||state.balance<pending.item.price} onClick={buy}>{busy?'구매 중…':'구매 확정'}</button><button disabled={busy} onClick={()=>setPending(null)}>구매 취소</button><p role="status">{message}</p></div>:<><div className="shop-categories" role="tablist" aria-label="상점 카테고리">{Object.entries(categories).map(([id,name])=><button role="tab" aria-selected={category===id} key={id} onClick={()=>setCategory(id)}>{name}</button>)}</div><div className="shop-grid">{items.map(i=><article key={i.item_id}><FurniturePreview item={i}/><h3>{i.name}</h3><p>{i.price} Coin · {i.size.width}×{i.size.height}</p><small>보유 {state.inventory.filter(v=>v.item_id===i.item_id).length}개</small><button aria-label={`${i.name} 구매`} disabled={busy||state.balance<i.price} onClick={()=>{setPending({item:i,request:crypto.randomUUID()});setMessage('');}}>{state.balance<i.price?'잔액 부족':'구매하기'}</button></article>)}</div><p role="status">{message}</p></>}</Modal>}
  {history&&<Modal title="NOBIS Coin 거래 내역" onClose={()=>setHistory(false)}><p>잔액 {state.balance.toLocaleString()} Coin</p><ol className="coin-history">{state.transactions.map(t=><li key={t.id}><span>{t.kind==='gacha_reward'?'티켓 코인 뽑기':t.kind==='minigame_reward'?'미니게임 보상':t.kind==='initial_grant'?'초기 지급':t.kind==='purchase'?'가구 구매':'코인 조정'}</span><b>{t.amount>0?'+':''}{t.amount} Coin</b><small>{t.created_at} · 잔액 {t.balance_after}</small></li>)}</ol></Modal>}
 </>;
}
