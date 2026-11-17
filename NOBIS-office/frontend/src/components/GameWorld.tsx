import {useEffect,useRef,useState} from 'react';
import Phaser from 'phaser';
import {HomeScene} from '../game/scenes/HomeScene';
import {OfficeScene} from '../game/scenes/OfficeScene';
import type {Model} from '../game/bridge';
import {bridge,emit} from '../game/bridge';
function resizeGame(game:Phaser.Game,host:HTMLDivElement){
 const width=host.clientWidth,height=host.clientHeight;if(width<=0||height<=0)return;
 // Phaser RESIZE updates its drawing buffer; stale inline CSS can otherwise retain the old viewport.
 game.canvas.style.width=width+'px';game.canvas.style.height=height+'px';
 // Refresh after CSS so Phaser input displayScale uses the new DOM bounds as well.
 game.scale.setParentSize(width,height);game.scale.updateBounds();
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
  const game=new Phaser.Game({type:Phaser.AUTO,parent:host,backgroundColor:'#201b30',pixelArt:true,antialias:false,
   scale:{mode:Phaser.Scale.RESIZE,width:host.clientWidth||800,height:host.clientHeight||600},scene:[],input:{activePointers:3},audio:{noAudio:true},
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
