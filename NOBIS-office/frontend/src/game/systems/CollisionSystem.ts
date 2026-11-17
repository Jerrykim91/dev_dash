import type {MapData,Point} from '../types';
import {SurfaceSystem} from './SurfaceSystem';
export const key=(p:Point)=>`${p.x},${p.y}`;
export class CollisionSystem {
 blocked:Set<string>;surface:SurfaceSystem;floor?:Set<string>;edges:Set<string>;
 constructor(public map:MapData){this.surface=new SurfaceSystem(map);this.floor=map.walkable_tiles?new Set(map.walkable_tiles.map(key)):undefined;this.edges=new Set((map.closed_edges??[]).flatMap(([a,b])=>[key(a)+'>'+key(b),key(b)+'>'+key(a)]));this.blocked=new Set(map.objects.filter(o=>o.blocking!==false).flatMap(o=>Array.from({length:(o.width??1)*(o.height??1)},(_,i)=>key({x:o.x+i%(o.width??1),y:o.y+Math.floor(i/(o.width??1))}))));}
 walkable(p:Point){return Number.isInteger(p.x)&&Number.isInteger(p.y)&&p.x>=0&&p.y>=0&&p.x<this.map.width&&p.y<this.map.height&&(!this.floor||this.floor.has(key(p)))&&!this.blocked.has(key(p));}
 neighbors(p:Point):Point[]{return [{x:p.x+1,y:p.y},{x:p.x-1,y:p.y},{x:p.x,y:p.y+1},{x:p.x,y:p.y-1}].filter(n=>this.walkable(n)&&this.surface.canCross(p,n)&&!this.edges.has(key(p)+'>'+key(n)));}
}
