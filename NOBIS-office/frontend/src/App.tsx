import {MeetingRoomLobby} from './components/MeetingRoomLobby';
import {useRef} from 'react';
import {SocialRoot} from './social/SocialRoot';
import {ProfileCard} from './social/ProfileCard';
import {CollectiblesRoot} from './collectibles/CollectiblesRoot';
import {GamePlatform} from './games/components/GamePlatform';
import {useEffect,useState} from 'react';
import {useMediaQuery} from './hooks/useMediaQuery';
import {DashboardLink} from './components/DashboardLink';
import {AdminPage} from './components/AdminPage';
import {AnnouncementBanner} from './components/AnnouncementBanner';
import {HomeTools} from './components/HomeTools';
import {GameWorld} from './components/GameWorld';
import {Modal} from './components/Modal';
import {LoginScreen} from './components/LoginScreen';
import {TopBar} from './components/TopBar';
import {SideNavigation} from './components/SideNavigation';
import {ChatPanel} from './components/ChatPanel';
import {WorkStatusIndicator} from './components/WorkStatusIndicator';
import {MemberList} from './components/MemberList';
import {useOffice} from './useOffice';
import {useOfficeStore} from './stores/officeStore';
import {bridge,emit,type Model} from './game/bridge';
import {workStatusText,type Interaction,type Player,type Session} from './game/types';
import {dashboardLink,readDashboardUrl,validateDashboardUrl} from './services/dashboard';

function Office({session}:{session:Session}) {
 const [arcadeOpen,setArcadeOpen]=useState(false),[socialOpen,setSocialOpen]=useState(false),[collectiblesOpen,setCollectiblesOpen]=useState(false),[socialUnread,setSocialUnread]=useState(0);
 const send=useOffice(session),mobile=useMediaQuery('(max-width: 760px)');
 const [chatCollapsed,setChatCollapsed]=useState(()=>{try{return localStorage.getItem('nobis.ui.chat-collapsed')==='true';}catch{return false;}});
 const toggleChat=()=>setChatCollapsed(v=>{try{localStorage.setItem('nobis.ui.chat-collapsed',String(!v));}catch{}return !v;});
 const [sidebarPinned,setSidebarPinned]=useState(()=>{try{return localStorage.getItem('nobis.ui.sidebar-expanded')==='true';}catch{return false;}}),[mobileMenu,setMobileMenu]=useState(false);
 const toggleSidebar=()=>{if(mobile){setMobileMenu(v=>!v);return;}setSidebarPinned(v=>{try{localStorage.setItem('nobis.ui.sidebar-expanded',String(!v));}catch{}return !v;});};
 useEffect(()=>{if(!mobile)setMobileMenu(false);},[mobile]);

 const {roomInstanceId,roomType,roomCounts,officeMap,worldRevision,players,zones,space,connected,notice,viewMode,setView,notifications,clearNotifications,logout,scope,roomSettings,setRoomSettings,visitedMap,homeState,decorating,worldChannelId,preferences,setPreferences,unread,selectChannel,dashboardConfig}=useOfficeStore();
 const own=players.find(p=>p.id===session.user.id),roomName=scope.startsWith('personal:')?(roomSettings?.name??'개인 작업실'):zones.find(z=>z.id===space)?.name??'오피스 월드';
 const [preferenceSaving,setPreferenceSaving]=useState(false);
 const [reportReason,setReportReason]=useState(''),[reportResult,setReportResult]=useState('');
 const [hint,setHint]=useState('바닥을 클릭하거나 터치해 이동해 보세요.'),[modal,setModal]=useState<''|'settings'|'dashboard'|'notifications'|'travel'|'meeting_rooms'>(''),[profile,setProfile]=useState<Player|null>(null),[interaction,setInteraction]=useState<Interaction|null>(null),[urlInput,setUrlInput]=useState(readDashboardUrl),[nameInput,setNameInput]=useState('나의 방'),[saving,setSaving]=useState(false),[settingsError,setSettingsError]=useState('');
 const defaultDashboardUrl=dashboardConfig.default_url||(dashboardConfig.allow_local?readDashboardUrl():''),rawDashboardUrl=roomSettings?.dashboard_url||defaultDashboardUrl,production=!dashboardConfig.allow_local;
 const dashboardUrl=validateDashboardUrl(rawDashboardUrl,production)?rawDashboardUrl:'';
 useEffect(()=>{if(roomSettings){setUrlInput(roomSettings.dashboard_url||defaultDashboardUrl);setNameInput(roomSettings.name);}},[roomSettings,defaultDashboardUrl]);
 useEffect(()=>{
  const hint=(e:Event)=>setHint((e as CustomEvent<string>).detail);
  const interact=(e:Event)=>{const i=(e as CustomEvent<Interaction>).detail;setInteraction(i);if(i.kind==='meeting_lobby'){setModal('meeting_rooms');}else if(i.kind==='channel'){emit('open-channels',i.channel_kind);setHint(i.message||'대화방을 선택하세요.');}else if(i.kind==='menu'){setTimeout(()=>setModal('travel'),320);}else if(i.kind==='arcade')bridge.dispatchEvent(new Event('open-arcade'));else if(i.kind==='dashboard')setModal('dashboard');else setHint(i.message||'상호작용을 실행했어요.');};
  const profile=(e:Event)=>setProfile((e as CustomEvent<Player>).detail);
  const whisper=(e:Event)=>{const d=(e as CustomEvent).detail;useOfficeStore.getState().selectChannel('private');useOfficeStore.getState().setView('chat');setProfile(null);setModal('');setTimeout(()=>emit('compose-whisper',d),0);};
  bridge.addEventListener('whisper-target',whisper);
  bridge.addEventListener('hint',hint);bridge.addEventListener('interaction',interact);bridge.addEventListener('profile',profile);
  return()=>{bridge.removeEventListener('whisper-target',whisper);bridge.removeEventListener('hint',hint);bridge.removeEventListener('interaction',interact);bridge.removeEventListener('profile',profile);};
 },[]);
 useEffect(()=>{if(socialOpen)setProfile(null);},[socialOpen]);
 const model:Model={roomInstanceId,roomCounts,officeMap:officeMap??undefined,worldRevision,worldZones:zones,session,space,scope,channelId:worldChannelId,players:players.filter(p=>(p.scope??'office')===scope),connected,chat:[],notice,homeMap:scope===`personal:${session.user.id}`?homeState?.map:visitedMap??undefined,canMove:connected&&own?.participation_mode==='normal'&&viewMode==='world'&&!decorating&&!arcadeOpen&&!own?.minigame&&!socialOpen&&!collectiblesOpen};
 const pendingService=useRef<''|'home'|'arcade'>('');
 const driveService=()=>{const s=useOfficeStore.getState();if(s.scope!=='office')return;const target=pendingService.current;if(!target)return;if(target==='home'&&s.roomType==='lobby'){pendingService.current='';emit('object-click','bookshelf');}else if(target==='arcade'&&s.roomType==='lounge'){pendingService.current='';emit('object-click','arcade');}else emit('object-click',s.roomType==='lobby'?'portal-lounge':'room-exit');};
 useEffect(()=>{const ready=()=>driveService();bridge.addEventListener('world-ready',ready);return()=>bridge.removeEventListener('world-ready',ready);},[]);
 useEffect(()=>{setModal('');setInteraction(null);},[roomInstanceId]);
 const latestProfile=profile?players.find(p=>p.id===profile.id)??profile:null;

 return <div className={`app-shell ${viewMode==='chat'?'chat-only':''} ${sidebarPinned?'sidebar-pinned':''} ${mobileMenu?'mobile-menu-open':''} ${chatCollapsed&&viewMode==='world'&&!mobile?'chat-collapsed':''}`}>
  <AnnouncementBanner/>
  <TopBar socialUnread={socialUnread} onSocial={()=>emit('open-social',{tab:'friends'})} onAttendance={()=>emit('open-collectibles',{})} onToggleSidebar={toggleSidebar} sidebarExpanded={mobile?mobileMenu:sidebarPinned} onChannelChange={id=>send({type:'world_channel_move',channel_id:id})} onSettings={()=>setModal('settings')} onNotifications={()=>setModal('notifications')} onProfile={()=>own&&setProfile(own)}/>
  {mobile&&mobileMenu&&<button className="sidebar-scrim" aria-label="메뉴 닫기" onClick={()=>setMobileMenu(false)}/>}
  <SideNavigation onSocial={()=>{setMobileMenu(false);emit('open-social',{tab:'friends'});}} onArcade={()=>{setMobileMenu(false);if(scope==='office'&&viewMode==='world'&&!arcadeOpen)(pendingService.current='arcade',driveService());else setHint('오피스 월드 모드에서 라운지 게임기를 클릭해 주세요.');}} onPersonal={()=>{setMobileMenu(false);if(scope==='office'&&viewMode==='world')(pendingService.current='home',driveService());else setHint('전체 오피스 모드에서 책장을 클릭해 내 집에 들어갈 수 있어요.');}} onReturn={()=>send({type:'room_leave'})} onDashboard={()=>{setMobileMenu(false);setModal('dashboard');}} onSettings={()=>{setMobileMenu(false);setModal('settings');}}><MemberList onProfile={setProfile}/></SideNavigation>
  <main className="center-panel"><div className="world-heading"><h1>{scope==='office'?'Office World':'My Home'} <span>· {roomName}</span></h1><div className="world-tools">{!mobile&&<button className="chat-collapse" aria-label={chatCollapsed?'채팅 패널 펼치기':'채팅 패널 접기'} aria-expanded={!chatCollapsed} aria-controls="office-chat-panel" onClick={toggleChat}>{chatCollapsed?'채팅 열기':'채팅 접기'}</button>}{(scope!=='office'||roomType!=='lobby')&&<button onClick={()=>scope==='office'?emit('object-click','room-exit'):send({type:'room_leave'})}>로비로 돌아가기</button>}<button aria-label="월드 전체 보기" title="월드 전체 보기" onClick={()=>emit('camera-mode','overview')}>전체 보기</button><button aria-label="캐릭터 추적" title="내 캐릭터로 카메라 복귀" onClick={()=>emit('camera-mode','follow')}>내 캐릭터</button></div></div><div className="world-frame"><HomeTools/>{own&&<GameWorld model={model} paused={viewMode==='chat'||arcadeOpen||socialOpen||collectiblesOpen}/>}<GamePlatform token={session.token} onOpen={setArcadeOpen}/><div className="world-overlay"><span className="live-dot"/>{roomName}<small>현재 룸 · 클릭으로 이동</small></div><div className="world-location">NOBIS OFFICE</div>{!connected&&<div className="connection-banner" role="status">{notice}<button onClick={logout}>로그인으로</button></div>}</div>
   <div className="world-footer"><span>클릭·탭 <b>이동 / 상호작용</b></span><span>드래그 <b>맵 탐색</b></span><span>휠·핀치 <b>확대 / 축소</b></span></div><p className="hint" role="status">✧ {hint}</p>
  </main>
  <aside id="office-chat-panel" className="right-panel">{viewMode==='chat'&&!connected&&<div className="chat-connection" role="status">{notice}</div>}{mobile?<details className="mobile-status"><summary>내 상태 설정</summary><WorkStatusIndicator send={send}/></details>:<WorkStatusIndicator send={send}/>}<ChatPanel send={send}/></aside>
  <footer className="bottom-bar"><div className="location-summary"><span className="bottom-zone">{roomName}</span><span>{own?workStatusText(own.work_status):'접속 중'} · {own?.participation_mode==='spectator'?'관람자':'일반 참여'}</span></div>{mobile?<div className="mobile-mode-tabs" role="tablist" aria-label="화면 모드"><button role="tab" aria-label="전체 모드로 돌아가기" aria-selected={viewMode==='world'} onClick={()=>setView('world')}>월드</button><button role="tab" aria-label="채팅 전용 모드" aria-selected={viewMode==='chat'} onClick={()=>setView('chat')}>채팅{(unread.private??0)>0&&<i>{unread.private}</i>}</button></div>:<><button className="view-mode-switch" onClick={()=>setView(viewMode==='world'?'chat':'world')}>{viewMode==='world'?'채팅 전용 모드':'전체 모드로 돌아가기'}</button><button onClick={()=>setModal('settings')}>설정</button></>}</footer>
  {viewMode==='chat'&&<div className="chat-mode-label">채팅 전용 모드 · {roomName}<small>게임 렌더링은 일시 정지하며 위치와 연결은 유지합니다.</small>{!connected&&<span role="status">{notice}</span>}</div>}
  {modal&&<Modal title={modal==='settings'?'설정':modal==='dashboard'?'DevNest 개인 대시보드':modal==='travel'?(interaction?.label??'공간 이동'):modal==='meeting_rooms'?'회의실 목록':'알림'} onClose={()=>setModal('')}>
   {modal==='meeting_rooms'&&<MeetingRoomLobby send={send}/>}
   {modal==='settings'&&<form className="settings-form" onSubmit={async e=>{
    e.preventDefault();if(!validateDashboardUrl(urlInput,production)){setSettingsError('유효한 http(s) 주소를 입력하세요. 운영 환경에서는 로컬 주소를 사용할 수 없습니다.');return;}
    setSaving(true);setSettingsError('');
    try{const response=await fetch('/api/personal-room',{method:'PUT',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({name:nameInput,dashboard_url:urlInput.trim()})});if(!response.ok)throw new Error('설정을 저장하지 못했어요.');setRoomSettings(await response.json());setHint('개인 작업실 설정을 저장했어요.');setModal('');}catch(e){setSettingsError(e instanceof Error?e.message:'설정 저장 실패');}finally{setSaving(false);}
   }}><label className="bubble-setting"><input type="checkbox" disabled={preferenceSaving} checked={preferences.chat_bubbles_enabled} onChange={async e=>{const enabled=e.target.checked,previous=preferences;setPreferences({chat_bubbles_enabled:enabled});setPreferenceSaving(true);try{const r=await fetch('/api/chat-preferences',{method:'PUT',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({chat_bubbles_enabled:enabled})});if(!r.ok)throw Error();setPreferences(await r.json());}catch{setPreferences(previous);setSettingsError('말풍선 설정 저장 실패');}finally{setPreferenceSaving(false);}}}/>공개 채팅 말풍선 ON</label><p className="field-note">집중 업무존·회의실에서는 표시하지 않아요. 상태 말풍선과 별개의 설정입니다.</p><label htmlFor="personal-name">개인 공간 이름</label><input id="personal-name" value={nameInput} onChange={e=>setNameInput(e.target.value)} maxLength={40} required/><label htmlFor="dashboard-url">DevNest 외부 URL</label><input id="dashboard-url" value={urlInput} onChange={e=>setUrlInput(e.target.value)} placeholder={production?'https://대시보드의 실제 주소':'http://127.0.0.1:8001/'}/><p className="field-note">이 사용자 계정의 개인 작업실 설정으로 저장합니다. DevNest 파일과 로그인 정보는 수정하지 않습니다.</p><p className="error" role="alert">{settingsError}</p><button className="primary" disabled={saving}>{saving?'저장 중…':'연결 주소 저장'}</button></form>}

   {modal==='dashboard'&&<div className="dashboard-connect"><p>작업실과 DevNest를 연결하는 메뉴입니다.</p>{dashboardUrl&&own?<><DashboardLink url={dashboardLink(dashboardUrl,location.href,{user:own,avatar:own.avatar})} onSettings={()=>setModal('settings')}/><p className="field-note">새 탭을 닫으면 이 오피스 탭으로 돌아올 수 있어요. 공통 로그인은 아직 연결하지 않았습니다.</p></>:<><p className="dummy-badge">{rawDashboardUrl?'현재 주소는 운영 환경에서 사용할 수 없습니다. 연결 설정을 확인해 주세요.':'연결 주소가 아직 설정되지 않았어요.'}</p><button onClick={()=>setModal('settings')}>DevNest 연결 설정</button></>}<button className="return-office" onClick={()=>setModal('')}>{scope==='office'?'월드로 돌아가기':'작업실로 돌아가기'}</button></div>}
   {modal==='travel'&&<div className="travel-options">{interaction?.personal_entry&&<button onClick={()=>{send({type:'room_enter'});setModal('');}}>내 방 · 작업실 입장 →</button>}{interaction?.personal_exit&&<button onClick={()=>{send({type:'room_leave'});setModal('');}}>오피스로 복귀 →</button>}</div>}
   {modal==='notifications'&&<div className="notification-list">{notifications.length===0?<p>새 알림이 없어요.</p>:notifications.map(n=><p key={n.id}>{n.message}{n.channel==='private'&&<button onClick={()=>{selectChannel('private');setView('chat');setModal('');}}>귓속말 보기</button>}</p>)}<button onClick={()=>{clearNotifications();setModal('');}}>알림 확인 완료</button></div>}
  </Modal>}
  {latestProfile&&<Modal title="멤버 프로필" onClose={()=>setProfile(null)}><ProfileCard userId={latestProfile.id}/></Modal>}
  <SocialRoot onOpen={setSocialOpen} onUnread={setSocialUnread}/><CollectiblesRoot onOpen={setCollectiblesOpen}/>

 </div>;
}
export default function App() {
 const session=useOfficeStore(s=>s.session),logout=useOfficeStore(s=>s.logout),[checking,setChecking]=useState(!!session);
 useEffect(()=>{if(!session){setChecking(false);return;}let active=true;const c=new AbortController();fetch('/api/me',{headers:{Authorization:`Bearer ${session.token}`},signal:c.signal}).then(r=>{if(active){if(r.status===401)logout();setChecking(false);}}).catch(()=>{if(active)setChecking(false);});return()=>{active=false;c.abort();};},[session,logout]);
 if(checking)return <div className="loading">NOBIS Office · 세션 확인 중…</div>;
 return session?(location.pathname==='/admin'?<AdminPage/>:<Office session={session}/>):<LoginScreen/>;
}
