import {enterRoom} from './room-fixture';import rooms from '../shared/rooms.json';
import maps from '../shared/maps.json';import zones from '../shared/zones.json';import oldObjects from '../design/world/object-contracts.json';import type {Page} from '../frontend/node_modules/@playwright/test';
// Older regression scenarios describe semantic destinations using their original map coordinates.
// Resolve only those fixtures; the new Phase 7-A tests use the actual map directly.
const anchors=Object.fromEntries(zones.map(z=>[z.id,z.anchor]));
export const spawn=maps.office.spawn;
export async function resolvePoint(p:Page,x:number,y:number,offset=0){
 await p.bringToFront();const personal=await p.evaluate(()=>((window as any).__NOBIS_GAME__?.registry.get('world')?.model.scope??'office').startsWith('personal:'));if(personal)return{x,y};
 if(offset){const old=Object.values(oldObjects).find(o=>o.x===x&&o.y===y);for(const [type,m] of Object.entries(rooms.maps)){const now=old&&m.objects.find(o=>o.id===old.id);if(now){await enterRoom(p,type);return{x:now.x,y:now.y};}}}
 const targetRoom:Record<string,string>={'6,8':'focus','18,8':'cafe','30,8':'lounge','18,23':'garden','30,23':'terrace'};const type=targetRoom[`${x},${y}`];if(type){await enterRoom(p,type);return rooms.maps[type as keyof typeof rooms.maps].spawn;}
 const points:Record<string,{x:number;y:number}>={'6,8':anchors.focus,'18,8':anchors.cafe,'30,8':anchors.lounge,'6,23':anchors.meeting,'18,23':anchors.garden,'30,23':anchors.outside,'20,7':{x:anchors.cafe.x,y:anchors.cafe.y+1},'18,10':{x:anchors.cafe.x,y:anchors.cafe.y+2},'11,15':{x:spawn.x-1,y:spawn.y},'14,13':{x:spawn.x,y:spawn.y-1},'13,13':{x:spawn.x-1,y:spawn.y}};
 return points[`${x},${y}`]??{x,y};
}
