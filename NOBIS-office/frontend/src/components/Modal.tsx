import {useEffect,useRef,useState,type ReactNode} from 'react';
import tokens from '../design/tokens.json';
export function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}){
 const ref=useRef<HTMLDivElement>(null),close=useRef(onClose),pending=useRef(false),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined),[closing,setClosing]=useState(false),activeTitle=useRef(title);close.current=onClose;activeTitle.current=title;
 function requestClose(){if(pending.current)return;if(matchMedia('(prefers-reduced-motion: reduce)').matches){close.current();return;}pending.current=true;setClosing(true);const requestedTitle=activeTitle.current;timer.current=setTimeout(()=>{pending.current=false;setClosing(false);if(activeTitle.current===requestedTitle)close.current();},parseInt(tokens.motion.normal));}
 useEffect(()=>{clearTimeout(timer.current);pending.current=false;setClosing(false);},[title]);
 useEffect(()=>{const before=document.activeElement as HTMLElement|null;ref.current?.querySelector<HTMLElement>('button,input,a')?.focus();
  const key=(e:KeyboardEvent)=>{if(e.key==='Escape')requestClose();if(e.key==='Tab'){const nodes=ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]');if(!nodes?.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){last.focus();e.preventDefault();}else if(!e.shiftKey&&document.activeElement===last){first.focus();e.preventDefault();}}};
  document.addEventListener('keydown',key);return()=>{clearTimeout(timer.current);document.removeEventListener('keydown',key);before?.focus();};},[title]);
 return <div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)requestClose();}}><div className={'modal'+(closing?' modal-closing':'')} role="dialog" aria-modal="true" aria-label={title} ref={ref}><div className="modal-heading"><h2>{title}</h2><button onClick={requestClose} aria-label="닫기">×</button></div>{children}</div></div>;
}
