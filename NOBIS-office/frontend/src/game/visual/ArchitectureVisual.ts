import Phaser from 'phaser';
import type {MapData,Point} from '../types';
import {CoordinateSystem} from '../systems/CoordinateSystem';
import {SurfaceSystem} from '../systems/SurfaceSystem';
import palette from './architecture-palette.json';
import {visualLayers} from './catalog';
const color=(s:string)=>parseInt(s.slice(1),16);
const key=(p:Point)=>`${p.x},${p.y}`;
/** Temporary structural renderer. Every opening and stair corresponds to navigation data. */
export function drawArchitecture(scene:Phaser.Scene,map:MapData,coords:CoordinateSystem){
 const surface=new SurfaceSystem(map),floor=new Set(map.walkable_tiles?.map(key)),closed=new Set((map.closed_edges??[]).flatMap(([a,b])=>[key(a)+'>'+key(b),key(b)+'>'+key(a)]));
 const batches=new Map<number,Phaser.GameObjects.Graphics>();
 const batch=(depth:number)=>{let g=batches.get(depth);if(!g){g=scene.add.graphics().setDepth(depth);batches.set(depth,g);}return g;};
 for(const tile of map.walkable_tiles??[]){
  const p=coords.toWorld(tile);
  for(const [dx,dy,a,b]of [[1,0,{x:p.x+32,y:p.y},{x:p.x,y:p.y+16}],[0,1,{x:p.x-32,y:p.y},{x:p.x,y:p.y+16}],[-1,0,{x:p.x,y:p.y-16},{x:p.x-32,y:p.y}],[0,-1,{x:p.x,y:p.y-16},{x:p.x+32,y:p.y}]] as [number,number,Point,Point][]){
   const n={x:tile.x+dx,y:tile.y+dy},boundary=!floor.has(key(n)),blocked=closed.has(key(tile)+'>'+key(n));
   if(!boundary&&!blocked)continue;if(blocked&&(dx<0||dy<0))continue;
   const g=batch(coords.depth(tile)-.25),height=blocked?24:17;
   g.fillStyle(color(blocked?palette.glass:palette.masonryShade),blocked?.34:.9).fillPoints([a,b,{x:b.x,y:b.y-height},{x:a.x,y:a.y-height}],true);
   g.lineStyle(2,color(palette.rail),.9).lineBetween(a.x,a.y-height,b.x,b.y-height);
   g.lineStyle(1,color(palette.woodLight),.6).lineBetween(a.x,a.y,b.x,b.y);
   if(boundary){const z=surface.elevation(tile)+12,base=batch(visualLayers.architectureBack);base.fillStyle(color(palette.masonryShade)).fillPoints([a,b,{x:b.x,y:b.y+z},{x:a.x,y:a.y+z}],true);}
  }
 }
 const base=new CoordinateSystem();
 for(const stair of surface.spec.stairs){
  const a=base.toWorld(stair.from),b=base.toWorld(stair.to),za=surface.elevation(stair.from),zb=surface.elevation(stair.to),dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy),nx=-dy/len*13,ny=dx/len*13,g=batch(visualLayers.stairs);
  for(let i=0;i<4;i++){
   const t=i/4,u=(i+1)/4,z=za+(zb-za)*u,p={x:a.x+dx*t,y:a.y+dy*t-z},q={x:a.x+dx*u,y:a.y+dy*u-z};
   g.fillStyle(color(i%2?palette.wood:palette.woodLight)).fillPoints([{x:p.x+nx,y:p.y+ny},{x:q.x+nx,y:q.y+ny},{x:q.x-nx,y:q.y-ny},{x:p.x-nx,y:p.y-ny}],true);
   g.lineStyle(2,color(palette.masonryShade)).lineBetween(p.x+nx,p.y+ny,p.x-nx,p.y-ny);
  }
 }
 // Subspaces share the existing six zone IDs, with independent visual labels only.
 for(const area of (map.visualAreas??[]).filter(a=>a.id==='entrance')){const p=coords.toWorld(area.anchor);scene.add.text(p.x,p.y-42,area.name,{fontSize:'14px',color:'#f4d7a1',backgroundColor:'#30233de8',padding:{x:8,y:5}}).setOrigin(.5).setDepth(visualLayers.zoneCaption);}
}
