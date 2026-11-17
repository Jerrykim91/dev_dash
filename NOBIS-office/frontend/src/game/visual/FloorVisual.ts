import Phaser from 'phaser';
import {isLobby,lobbyFloor} from './LobbyCatalog';
import type {MapData,Zone} from '../types';
import {CoordinateSystem} from '../systems/CoordinateSystem';
import {zoneAt} from '../systems/ZoneSystem';
import tokens from '../../design/tokens.json';
import {frameAvailable} from './AssetLoader';
import {manifest,visualLayers} from './catalog';
const number=(s:string)=>parseInt(s.slice(1),16);
export function drawFloor(scene:Phaser.Scene,map:MapData,zones:Zone[],coords:CoordinateSystem,home:boolean){
 const floor=scene.add.graphics().setDepth(visualLayers.floor),walls=scene.add.graphics().setDepth(visualLayers.wall);const paint=tokens.world as Record<string,string>;
 const tiles=map.walkable_tiles??Array.from({length:map.width*map.height},(_,i)=>({x:i%map.width,y:Math.floor(i/map.width)}));
 for(const {x,y} of tiles){
  const p=coords.toWorld({x,y}),zone=zoneAt({x,y},zones),id=home?'home':zone.id,tile=isLobby(map)?lobbyFloor(x,y):manifest.tilesets[id];
  if(frameAvailable(scene,tile)){scene.add.image(p.x,p.y,tile.atlas,tile.frame).setDisplaySize(coords.tileWidth,coords.tileHeight).setOrigin(.5).setDepth(visualLayers.floor);continue;}
  const c=Phaser.Display.Color.HexStringToColor((id==='outside'?paint.cafe:id==='vacation'?paint.lounge:paint[id])??paint.floor),factor=(x+y)%2?1:.96;
  const points=[{x:p.x,y:p.y-16},{x:p.x+32,y:p.y},{x:p.x,y:p.y+16},{x:p.x-32,y:p.y}];floor.fillStyle(Phaser.Display.Color.GetColor(c.red*factor,c.green*factor,c.blue*factor)).fillPoints(points,true);floor.lineStyle(1,number(tokens.colors.ink),.13).strokePoints(points,true,true);
  if(['cafe','home','outside'].includes(id)){
   floor.lineStyle(1,number(tokens.colors.creamDark),.26);floor.lineBetween(p.x-15,p.y-8,p.x+16,p.y+8);if((x+y)%3===0)floor.lineBetween(p.x-19,p.y+3,p.x-9,p.y-2);
  }else if(id==='focus'||id==='meeting'){
   if((x+y)%3===0){floor.fillStyle(number(tokens.colors.cream),.14);floor.fillRect(p.x-2,p.y-1,3,2);}
  }else if((id==='lounge'||id==='garden')){
   floor.lineStyle(1,number(tokens.colors.successDark),.18);floor.lineBetween(p.x,p.y-11,p.x+22,p.y);floor.lineBetween(p.x,p.y+11,p.x-22,p.y);
  }else if(id==='outside'&&(x+y)%2===0){floor.lineStyle(1,number(tokens.colors.cream),.2);floor.lineBetween(p.x-14,p.y,p.x,p.y-7);}
 }
 if(!map.walkable_tiles){
 const a={x:0,y:-16},b=coords.toWorld({x:map.width-1,y:0}),c=coords.toWorld({x:0,y:map.height-1});
 for(const end of [{x:b.x+32,y:b.y},{x:c.x-32,y:c.y}]){
  walls.fillStyle(number(tokens.world.wallShade));walls.fillPoints([a,end,{x:end.x,y:end.y-56},{x:a.x,y:a.y-56}],true);walls.lineStyle(5,number(tokens.world.wall));walls.lineBetween(a.x,a.y-56,end.x,end.y-56);walls.lineStyle(2,number(tokens.colors.creamDark),.45);walls.lineBetween(a.x,a.y-8,end.x,end.y-8);
 }
 }
 for(const station of map.workstations??[]){
  const xs=station.plot.map(p=>p.x),ys=station.plot.map(p=>p.y),x=Math.min(...xs),y=Math.min(...ys),corners=[{x:x-.5,y:y-.5},{x:x+2.5,y:y-.5},{x:x+2.5,y:y+2.5},{x:x-.5,y:y+2.5}].map(p=>coords.toWorld(p));
  floor.lineStyle(1,number(tokens.colors.cream),.55).strokePoints(corners,true,true);
  const p=coords.toWorld(station.approach);scene.add.text(p.x,p.y+5,station.id.slice(-2),{fontSize:'12px',color:tokens.colors.cream}).setOrigin(.5).setDepth(visualLayers.floorDetail);
 }
 for(const zone of zones){if(!zone.tiles)continue;const p=coords.toWorld(zone.anchor);scene.add.text(p.x,p.y-33,zone.name,{fontFamily:tokens.font.body,fontSize:'15px',color:tokens.colors.text,backgroundColor:tokens.colors.surface+'e8',padding:{x:12,y:6}}).setOrigin(.5).setDepth(visualLayers.zoneCaption);}
}
