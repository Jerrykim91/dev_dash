import {useState} from 'react';
export function DashboardLink({url,onSettings}:{url:string;onSettings:()=>void}){
 const [error,setError]=useState(''),[opened,setOpened]=useState(false);
 function open(){
  setError('');const tab=window.open('about:blank','_blank');
  if(!tab){setError('새 탭이 차단됐습니다. 브라우저의 팝업 허용 설정을 확인한 뒤 다시 열어 주세요.');return;}
  try{tab.opener=null;const meta=tab.document.createElement('meta');meta.name='referrer';meta.content='no-referrer';tab.document.head.append(meta);tab.location.replace(url);setOpened(true);}catch{tab.close();setError('대시보드 주소를 열지 못했습니다. 연결 주소를 확인해 주세요.');}
 }
 return <><a className="primary external-dashboard" href={url} target="_blank" rel="noopener noreferrer" onClick={e=>{e.preventDefault();open();}}>DevNest 새 탭에서 열기 ↗</a>{error&&<p role="alert" className="error">{error}</p>}{opened&&<p role="status" className="field-note">별도 탭을 열었습니다. 탭을 닫으면 현재 위치로 돌아옵니다.</p>}<details className="dashboard-help"><summary>대시보드가 열리지 않나요?</summary><p>새 탭의 연결 오류·네트워크 상태·서버 주소를 확인해 주세요. 다른 도메인의 연결 성공 여부는 이 화면에서 자동 판별하지 않습니다.</p><button onClick={open}>다시 열기</button><button onClick={onSettings}>연결 주소 설정</button></details></>;
}
