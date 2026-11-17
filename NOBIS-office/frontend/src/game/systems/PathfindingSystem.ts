import type {Point} from '../types';
import {CollisionSystem,key} from './CollisionSystem';
export const distance=(a:Point,b:Point)=>Math.abs(a.x-b.x)+Math.abs(a.y-b.y);
export class PathfindingSystem {
 constructor(public collision:CollisionSystem){}
 find(start:Point,goal:Point):Point[]|null {
  if(!this.collision.walkable(start)||!this.collision.walkable(goal))return null;
  const open:Point[]=[start],cost=new Map([[key(start),0]]),previous=new Map<string,Point>(),closed=new Set<string>();
  while(open.length){open.sort((a,b)=>(cost.get(key(a))!+distance(a,goal))-(cost.get(key(b))!+distance(b,goal)));const current=open.shift()!;
   if(key(current)===key(goal)){const path=[current];while(previous.has(key(path[0])))path.unshift(previous.get(key(path[0]))!);return path;}
   if(closed.has(key(current)))continue;closed.add(key(current));
   for(const next of this.collision.neighbors(current)){const c=cost.get(key(current))!+1;if(c<(cost.get(key(next))??Infinity)){cost.set(key(next),c);previous.set(key(next),current);open.push(next);}}
  }return null;
 }
 nearestReachable(start:Point,target:Point):Point[]|null {
  // Search only the connected component containing the player, then A* to the nearest tile.
  const queue=[start],seen=new Set([key(start)]);let best=start;
  for(let i=0;i<queue.length;i++){const p=queue[i];if(distance(p,target)<distance(best,target))best=p;for(const n of this.collision.neighbors(p))if(!seen.has(key(n))){seen.add(key(n));queue.push(n);}}
  return this.find(start,best);
 }
}
