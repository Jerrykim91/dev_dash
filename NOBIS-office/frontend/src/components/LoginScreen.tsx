import {PixelMark} from '../design/PixelMark';
import {LoginOfficeArt} from '../design/LoginOfficeArt';
import {useState,useEffect,type FormEvent} from 'react';
import {useOfficeStore} from '../stores/officeStore';
export function LoginScreen() {
 const login=useOfficeStore(s=>s.login);
 const [nickname,setNickname]=useState(''),[adminKey,setAdminKey]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[health,setHealth]=useState<{temporary_auth:boolean;dev_admin_login:boolean}|null>(null),[normal,setNormal]=useState(false),[uid,setUid]=useState(''),[password,setPassword]=useState('');
 useEffect(()=>{fetch('/api/health').then(r=>r.json()).then(setHealth).catch(()=>setError('서버에 연결할 수 없습니다.'));},[]);
 const development=health?.temporary_auth&&!normal;
 async function submit(e:FormEvent){
  e.preventDefault();setBusy(true);setError('');
  try{
   const r=await fetch(development?'/api/dev-login':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(development?{nickname,admin_key:adminKey}:{user_id:uid,password})});
   if(!r.ok){const data=await r.json();throw new Error(typeof data.detail==='string'?data.detail:'입력한 정보를 확인해 주세요.');}
   login(await r.json());
  }catch(e){setError(e instanceof Error?e.message:'서버 연결 실패');}finally{setBusy(false);}
 }
 return <main className="login-page"><div className="login-decoration" aria-hidden="true"><LoginOfficeArt/><span>YOUR SPACE TO CONNECT.</span></div><form className="login-card" onSubmit={submit}><span className="wordmark"><PixelMark/>NOBIS<span> Office</span></span><p className="eyebrow">A LITTLE CLOSER, EVEN FROM AFAR</p><h1>우리의 오늘이<br/>만나는 곳.</h1>{!health?<p>서버 연결 확인 중…</p>:<>{health.temporary_auth&&<button type="button" onClick={()=>{setNormal(!normal);setAdminKey('');}}>{normal?'개발용 닉네임 입장':'기존 계정으로 로그인'}</button>}{development?<><label htmlFor="nickname">개발용 닉네임</label><input id="nickname" autoComplete="nickname" value={nickname} onChange={e=>setNickname(e.target.value)} maxLength={20} required placeholder="닉네임을 입력하세요"/>{health.dev_admin_login&&<details className="admin-login"><summary>운영자 테스트 계정</summary><label htmlFor="admin-key">개발용 운영자 키</label><input id="admin-key" type="password" autoComplete="off" value={adminKey} onChange={e=>setAdminKey(e.target.value)}/></details>}</>:<><label htmlFor="account-id">계정 ID</label><input id="account-id" autoComplete="username" value={uid} onChange={e=>setUid(e.target.value)} required/><label htmlFor="account-password">비밀번호</label><input id="account-password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></>}<button className="primary" disabled={busy||(development?!nickname.trim():!uid||!password)}>{busy?'입장 중…':'오피스 입장하기 →'}</button><small>{development?'개발용 임시 인증 · 공개 서비스 사용 금지. 새 로그인마다 새 계정이 생성됩니다.':'서버 운영자가 생성한 기존 계정 ID로 로그인하세요.'}</small></>}<p className="error" role="alert">{error}</p></form></main>;
}
