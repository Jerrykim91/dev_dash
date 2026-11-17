import type {MapObject,Point} from '../types';
import {PathfindingSystem} from './PathfindingSystem';
export class InteractionSystem {
 constructor(public pathfinding:PathfindingSystem){}
 approach(start:Point,object:MapObject):Point[]|null {
  const cells=Array.from({length:(object.width??1)*(object.height??1)},(_,i)=>({x:object.x+i%(object.width??1),y:object.y+Math.floor(i/(object.width??1))}));
  const paths=cells.flatMap(p=>this.pathfinding.collision.neighbors(p)).map(p=>this.pathfinding.find(start,p)).filter((p):p is Point[]=>p!==null);
  paths.sort((a,b)=>a.length-b.length);return paths[0]??null;
 }
}
