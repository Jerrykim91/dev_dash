import type {Point} from '../types';
export class CoordinateSystem {
 constructor(public tileWidth=64,public tileHeight=32,public origin:Point={x:0,y:0}){}
 toWorld(p:Point):Point{return {x:this.origin.x+(p.x-p.y)*this.tileWidth/2,y:this.origin.y+(p.x+p.y)*this.tileHeight/2};}
 toGrid(p:Point):Point{const x=(p.x-this.origin.x)/(this.tileWidth/2),y=(p.y-this.origin.y)/(this.tileHeight/2);return {x:(x+y)/2,y:(y-x)/2};}
 toTile(p:Point):Point{const g=this.toGrid(p);return {x:Math.round(g.x),y:Math.round(g.y)};}
 depth(p:Point):number{return (p.x+p.y)*100;}
}
