import {useEffect,useState} from 'react';
import {useOfficeStore} from '../stores/officeStore';
import {Modal} from './Modal';
export function AnnouncementBanner(){
 const {announcementQueue,announcements,dismissAnnouncement}=useOfficeStore(),[history,setHistory]=useState(false),current=announcementQueue[0];
 useEffect(()=>{if(!current)return;const timer=setTimeout(dismissAnnouncement,current.duration_seconds*1000);return()=>clearTimeout(timer);},[current?.id,dismissAnnouncement]);
 return <>{current&&<div className="world-announcement-toast" role="status"><span aria-hidden="true">📣</span><div><strong>{current.title}</strong><small>{current.target_channel_id?'채널 공지':'전체 공지'}</small><p>{current.text}</p>{announcementQueue.length>1&&<small>대기 {announcementQueue.length-1}개</small>}</div><button aria-label="공지 닫기" onClick={dismissAnnouncement}>×</button></div>}<button className="announcement-history-button" onClick={()=>setHistory(true)}>공지 기록 {announcements.length}</button>{history&&<Modal title="공지 기록" onClose={()=>setHistory(false)}><div className="announcement-history">{announcements.length===0?<p>등록된 공지가 없습니다.</p>:announcements.map(a=><article key={a.id}><h3>📣 {a.title}</h3><small>{a.target_channel_id?'채널 공지':'전체 공지'} · {new Date(a.time).toLocaleString('ko-KR')}</small><p>{a.text}</p></article>)}</div></Modal>}</>;
}
