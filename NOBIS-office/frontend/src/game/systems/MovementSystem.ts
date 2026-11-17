import type {Direction,Point} from '../types';
export class MovementSystem {
 position:Point;direction:Direction='south';path:Point[]=[];onArrive:(()=>void)|undefined;
 constructor(start:Point,public speed=3.2){this.position={...start};}
 get moving(){return this.path.length>0;}
 cancel(){this.path=[];this.onArrive=undefined;}
 follow(path:Point[],onArrive?:()=>void){this.cancel();this.path=path.map(p=>({...p}));this.onArrive=onArrive;}
 update(delta:number){let remaining=Math.min(delta,.1)*this.speed;
  while(this.path.length){const p=this.path[0],dx=p.x-this.position.x,dy=p.y-this.position.y,d=Math.hypot(dx,dy);
   if(d<.0001){this.path.shift();continue;}
   this.direction=Math.abs(dx)>Math.abs(dy)?(dx>0?'east':'west'):(dy>0?'south':'north');
   const step=Math.min(d,remaining);this.position.x+=dx/d*step;this.position.y+=dy/d*step;remaining-=step;
   if(step===d)this.path.shift();if(remaining<=0)break;
  }
  if(!this.path.length&&this.onArrive){const done=this.onArrive;this.onArrive=undefined;done();}
 }
}
