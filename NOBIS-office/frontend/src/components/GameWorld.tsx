import {useEffect,useRef,useState} from 'react';
import Phaser from 'phaser';
import {HomeScene} from '../game/scenes/HomeScene';
import {OfficeScene} from '../game/scenes/OfficeScene';
import type {Model} from '../game/bridge';
import {bridge,emit} from '../game/bridge';
import {DPR} from '../game/systems/DisplayScale';
// HiDPI·4K: 그리기 버퍼는 장치 픽셀(CSS × DPR), 화면 표시는 CSS 크기(zoom 1/DPR). 입력 좌표는 Phaser displayScale이 환산한다.
function resizeGame(game:Phaser.Game,host:HTMLDivElement){
 const width=host.clientWidth,height=host.clientHeight;if(width<=0||height<=0)return;
 game.scale.resize(Math.round(width*DPR),Math.round(height*DPR));
 game.canvas.style.width=width+'px';game.canvas.style.height=height+'px';
 // updateBounds()만으로는 입력 환산 비율(displayScale)이 다시 계산되지 않는다 → 크기 변경 후 클릭이 어긋남(사이드바 접기 등). refresh로 재계산.
 game.scale.refresh();
}
export function GameWorld({model,paused}:{model:Model;paused:boolean}) {
 const[loading,setLoading]=useState(true);
 const root=useRef<HTMLDivElement>(null),latest=useRef(model),sleeping=useRef(paused),gameRef=useRef<Phaser.Game|null>(null);
 latest.current=model;sleeping.current=paused;
 useEffect(()=>{
  const host=root.current;if(!host)return;let active=true;setLoading(true);
  const key=model.scope.startsWith('personal:')?'HomeScene':'OfficeScene';
  const scene=key==='HomeScene'?new HomeScene():new OfficeScene();
  const ready=()=>{if(active)setLoading(false);};bridge.addEventListener('world-ready',ready);
  const game=new Phaser.Game({type:Phaser.AUTO,parent:host,backgroundColor:'#201b30',pixelArt:true,antialias:false,roundPixels:true,
   scale:{mode:Phaser.Scale.NONE,width:Math.round((host.clientWidth||800)*DPR),height:Math.round((host.clientHeight||600)*DPR),zoom:1/DPR},scene:[],input:{activePointers:3},audio:{noAudio:true},
   callbacks:{postBoot:g=>{g.scene.add(key,scene,true,{model:latest.current});if(sleeping.current){emit('freeze',true);g.loop.sleep();}}}});
  gameRef.current=game;
  const observer=new ResizeObserver(()=>resizeGame(game,host));observer.observe(host);
  if(import.meta.env.DEV)(window as unknown as {__NOBIS_GAME__:Phaser.Game}).__NOBIS_GAME__=game;
  return()=>{active=false;bridge.removeEventListener('world-ready',ready);observer.disconnect();game.scene.stop(key);game.loop.wake();const canvas=game.canvas;game.destroy(true);canvas.remove();gameRef.current=null;};
 },[model.session.user.id,model.scope,model.channelId,model.worldRevision,model.roomInstanceId]);
 useEffect(()=>emit('model',model),[model]);
 useEffect(()=>{
  const game=gameRef.current;if(!game)return;
  emit('freeze',paused);
  if(paused)game.loop.sleep();else {game.loop.wake();if(root.current)resizeGame(game,root.current);}
 },[paused]);
 return <div className="game-canvas" ref={root} aria-label="클릭 또는 터치로 이동하는 아이소메트릭 월드">{loading&&<span className="room-loading" role="status">룸을 준비하고 있어요…</span>}</div>;
}
