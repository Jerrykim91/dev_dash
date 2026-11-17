import type {Point} from '../types';
type Finger={point:Point;start:Point;pan:boolean};
export type Gesture={kind:'pan';dx:number;dy:number}|{kind:'pinch';before:Point;after:Point;scale:number};
// Input-independent gesture state. A drag or multi-touch sequence can never become a move tap.
export class GestureSystem {
 fingers=new Map<number,Finger>();dragged=false;suppressed=false;
 constructor(public threshold=8){}
 reset(){this.fingers.clear();this.dragged=false;this.suppressed=false;}
 down(id:number,point:Point,pan=false){if(!this.fingers.size){this.dragged=pan;this.suppressed=pan;}this.fingers.set(id,{point:{...point},start:{...point},pan});if(this.fingers.size>1)this.suppressed=true;}
 move(id:number,point:Point):Gesture|null{
  const finger=this.fingers.get(id);if(!finger)return null;
  const before=[...this.fingers.values()].map(f=>({...f.point})),old={...finger.point};finger.point={...point};
  if(this.fingers.size>1){
   this.dragged=true;const after=[...this.fingers.values()].map(f=>f.point),mid=(v:Point[])=>({x:(v[0].x+v[1].x)/2,y:(v[0].y+v[1].y)/2}),distance=(v:Point[])=>Math.hypot(v[0].x-v[1].x,v[0].y-v[1].y);
   return {kind:'pinch',before:mid(before),after:mid(after),scale:distance(before)>1?distance(after)/distance(before):1};
  }
  if(Math.hypot(point.x-finger.start.x,point.y-finger.start.y)>this.threshold)this.dragged=true;
  return this.dragged||this.suppressed?{kind:'pan',dx:point.x-old.x,dy:point.y-old.y}:null;
 }
 up(id:number,point:Point){const finger=this.fingers.get(id),tap=!!finger&&!this.dragged&&!this.suppressed&&Math.hypot(point.x-finger.start.x,point.y-finger.start.y)<=this.threshold;this.fingers.delete(id);if(!this.fingers.size)this.reset();return tap;}
}
