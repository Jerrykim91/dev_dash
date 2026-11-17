import type {MapData,Point,SurfaceSpec} from '../types';
const same=(a:Point,b:Point)=>a.x===b.x&&a.y===b.y;
/** Height is presentation data; only explicit stair edges connect different levels. */
export class SurfaceSystem {
 readonly spec:SurfaceSpec;private heights=new Map<string,number>();
 constructor(public map:MapData){this.spec=map.surface??{regions:[],stairs:[]};for(const r of this.spec.regions)for(const p of r.cells??[])this.heights.set(`${p.x},${p.y}`,r.elevation);}
 elevation(p:Point){const x=Math.round(p.x),y=Math.round(p.y);return this.heights.get(`${x},${y}`)??this.spec.regions.find(r=>!r.cells&&x>=r.tiles.x&&y>=r.tiles.y&&x<r.tiles.x+r.tiles.width&&y<r.tiles.y+r.tiles.height)?.elevation??0;}
 canCross(a:Point,b:Point){return this.elevation(a)===this.elevation(b)||this.spec.stairs.some(s=>same(a,s.from)&&same(b,s.to)||same(a,s.to)&&same(b,s.from));}
 height(p:Point){
  // Interpolate only along actual stair edges, not through adjacent cliffs.
  for(const s of this.spec.stairs){const dx=s.to.x-s.from.x,dy=s.to.y-s.from.y,t=(p.x-s.from.x)*dx+(p.y-s.from.y)*dy;
   if(t>=0&&t<=1&&Math.abs((p.x-s.from.x)*dy-(p.y-s.from.y)*dx)<.001)return this.elevation(s.from)+(this.elevation(s.to)-this.elevation(s.from))*t;
  }return this.elevation(p);
 }
 get levels(){return [...new Set([0,...this.spec.regions.map(r=>r.elevation)])];}
 cell(p:Point,zone_id:string,collision:boolean,interaction?:string,visual_asset?:string){return {map_id:this.map.id??'personal',tile:{x:p.x,y:p.y},zone_id,elevation:this.elevation(p),walkable:!collision,collision,interaction:interaction??null,visual_asset:visual_asset??null};}
}
