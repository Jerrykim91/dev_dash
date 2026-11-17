import Phaser from 'phaser';
import type {MapData} from '../types';
import {CoordinateSystem} from '../systems/CoordinateSystem';
import {lobbyFrame,lobbyManifest} from './LobbyCatalog';
import {frameAvailable} from './AssetLoader';
import {visualLayers} from './catalog';
import tokens from '../../design/tokens.json';
const color=(s:string)=>parseInt(s.slice(1),16);
/** Separate static architecture/effects. None of these decorative pixels create collision. */
export function drawLobbyArchitecture(scene:Phaser.Scene,map:MapData,coords:CoordinateSystem){
 const floor=new Set(map.walkable_tiles?.map(p=>`${p.x},${p.y}`));let rendered=0;
 for(const tile of map.walkable_tiles??[]){const p=coords.toWorld(tile);for(const [dx,dy,axis]of [[-1,0,'x'],[0,-1,'y']] as const){if(floor.has(`${tile.x+dx},${tile.y+dy}`))continue;const frame=lobbyFrame('wall/'+axis);if(frameAvailable(scene,frame)){scene.add.image(p.x,p.y,frame.atlas,frame.frame).setOrigin(lobbyManifest.pivot.x,lobbyManifest.pivot.y).setDepth(coords.depth(tile)-2).setData('visual-layer','back-architecture');rendered++;}}}
 const glow=scene.add.graphics().setDepth(visualLayers.floorDetail+1).setData('visual-layer','effects');
 for(const o of map.objects.filter(o=>o.kind==='lamp'||o.id==='welcome-desk')){const p=coords.toWorld(o);for(let i=4;i>=1;i--)glow.fillStyle(color(tokens.colors.cream),.015).fillEllipse(p.x,p.y,28*i,14*i);}
 scene.registry.set('lobby-visuals',{architectureSprites:rendered,separateLayers:true,interimArtwork:true});
 return rendered>0;
}
