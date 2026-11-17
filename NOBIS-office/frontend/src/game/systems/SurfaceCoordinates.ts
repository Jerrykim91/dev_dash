import {CoordinateSystem} from './CoordinateSystem';
import {SurfaceSystem} from './SurfaceSystem';
import type {Point} from '../types';
/** Camera transforms still operate in world pixels. Logical network positions stay x/y. */
export class SurfaceCoordinates extends CoordinateSystem {
 constructor(public surface:SurfaceSystem){super();}
 toWorld(p:Point):Point{const out=super.toWorld(p);return {...out,y:out.y-this.surface.height(p)};}
 toGrid(p:Point):Point{
  for(const stair of this.surface.spec.stairs){
   const a=this.toWorld(stair.from),b=this.toWorld(stair.to),dx=b.x-a.x,dy=b.y-a.y,length=dx*dx+dy*dy,t=((p.x-a.x)*dx+(p.y-a.y)*dy)/length;
   if(t>0&&t<1&&Math.abs((p.x-a.x)*dy-(p.y-a.y)*dx)/Math.sqrt(length)<12)return {x:stair.from.x+(stair.to.x-stair.from.x)*t,y:stair.from.y+(stair.to.y-stair.from.y)*t};
  }

  const candidates=this.surface.levels.map(z=>({z,p:super.toGrid({x:p.x,y:p.y+z})})).filter(c=>this.surface.elevation(c.p)===c.z&&(!this.surface.map.walkable_tiles||this.surface.map.walkable_tiles.some(t=>t.x===Math.round(c.p.x)&&t.y===Math.round(c.p.y)))&&c.p.x>=-.5&&c.p.y>=-.5&&c.p.x<this.surface.map.width-.5&&c.p.y<this.surface.map.height-.5);
  // When two projected floors overlap, the frontmost visible surface receives the click.
  candidates.sort((a,b)=>super.depth(b.p)-super.depth(a.p));return candidates[0]?.p??super.toGrid(p);
 }
 depth(p:Point){return super.depth(p)+this.surface.height(p)*.01;}
}
