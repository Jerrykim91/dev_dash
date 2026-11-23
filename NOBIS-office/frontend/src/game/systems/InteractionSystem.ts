import type {MapObject,Point,Seat} from '../types';
import {PathfindingSystem} from './PathfindingSystem';
export class InteractionSystem {
 constructor(public pathfinding:PathfindingSystem){}
 /** 좌석이 있는 오브젝트(의자·소파·연결된 책상)는 좌석의 진입 칸으로, 나머지는 footprint의 인접 칸으로 간다. */
 seatsFor(object:MapObject,seats:Seat[]=[]):Seat[]{return seats.filter(s=>s.object_id===object.id||s.work_surface_id===object.id);}
 approach(start:Point,object:MapObject,seats:Seat[]=[],taken:Set<string>=new Set()):Point[]|null {
  // 다른 사람이 앉은 자리는 후보에서 제외(전부 찼으면 원래 후보로 가서 서버 안내를 받음)
  const all=this.seatsFor(object,seats),free=all.filter(s=>!taken.has(s.id)),own=free.length?free:all;
  if(own.length){const paths=own.map(s=>this.pathfinding.find(start,s.approach)).filter((p):p is Point[]=>p!==null);paths.sort((a,b)=>a.length-b.length);if(paths[0])return paths[0];}
  const cells=Array.from({length:(object.width??1)*(object.height??1)},(_,i)=>({x:object.x+i%(object.width??1),y:object.y+Math.floor(i/(object.width??1))}));
  const paths=cells.flatMap(p=>this.pathfinding.collision.neighbors(p)).map(p=>this.pathfinding.find(start,p)).filter((p):p is Point[]=>p!==null);
  paths.sort((a,b)=>a.length-b.length);return paths[0]??null;
 }
}
