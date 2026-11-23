import Phaser from 'phaser';
import type {MapData,MapObject} from '../types';
import {CoordinateSystem} from '../systems/CoordinateSystem';
import {frameAvailable} from './AssetLoader';
import {manifest,frameScale,type VisualFrame} from './catalog';

/** 방 테마 → 벽 그림 (docs/visual-standard-v2.md §13). 실내 기본 벽, 카페 벽돌, 회의실 패널, 야외는 난간. */
const WALL_THEME:Record<string,string>={cafe:'cafe',meeting:'meeting',garden:'railing',terrace:'railing'};
export const wallTheme=(map:MapData)=>WALL_THEME[(map as MapData&{room_type?:string}).room_type??'']??'plain';
/** 문 그림: 로비 입구는 방 종류, 방 출구는 그 방 벽에 맞춘 문(기본 벽 exit, 카페 exitcafe, 회의실 exitmeeting, 난간 gate) */
export const doorTheme=(o:MapObject,room='plain')=>o.id.startsWith('portal-')?o.id.slice(7):room==='plain'?'exit':room==='railing'?'gate':`exit${room}`;
const frame=(key:string)=>(manifest.frames as Record<string,VisualFrame>)[key];
export const wallFrame=(theme:string,axis:'x'|'y')=>frame(`architecture/wall/${theme}/${axis}`);
export const wallDoorFrames=(o:MapObject,room='plain')=>o.kind==='door'&&o.wall_axis?{lower:frame(`architecture/door/${doorTheme(o,room)}/${o.wall_axis}`)??frame(`architecture/door/${doorTheme(o)}/${o.wall_axis}`),upper:frame('architecture/blank')}:undefined;

/** 뒤쪽 두 벽(-x 이웃 없음 → 좌상 'x', -y 이웃 없음 → 우상 'y')을 칸마다 그린다. 문이 붙은 칸·면은 문이 대신한다.
 * 그림이 없으면 false를 돌려 기존 도형 렌더러가 대신 그리게 한다. */
export function drawWalls(scene:Phaser.Scene,map:MapData,coords:CoordinateSystem):boolean{
 const theme=wallTheme(map),fx=wallFrame(theme,'x'),fy=wallFrame(theme,'y');
 if(!frameAvailable(scene,fx)||!frameAvailable(scene,fy)||!map.walkable_tiles)return false;
 const floor=new Set(map.walkable_tiles.map(p=>`${p.x},${p.y}`)),doors=new Set(map.objects.filter(o=>o.kind==='door'&&o.wall_axis).map(o=>`${o.x},${o.y},${o.wall_axis}`));
 let count=0;
 for(const t of map.walkable_tiles){
  const p=coords.toWorld(t);
  for(const [axis,dx,dy,f] of [['x',-1,0,fx],['y',0,-1,fy]] as const){
   if(floor.has(`${t.x+dx},${t.y+dy}`)||doors.has(`${t.x},${t.y},${axis}`))continue;
   scene.add.image(p.x,p.y,f.atlas,f.frame).setOrigin(manifest.furniture.origin.x,manifest.furniture.origin.y).setScale(frameScale(f)).setDepth(coords.depth(t)-2).setData('visual-layer','wall');count++;
  }
 }
 scene.registry.set('wall-visuals',{theme,segments:count});
 return count>0;
}
