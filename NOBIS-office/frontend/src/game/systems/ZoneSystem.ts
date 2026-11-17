import definitions from '../../../../shared/zones.json';
import {personalRoom} from '../maps';
import type {Point,Zone} from '../types';
export const worldZones=definitions as Zone[];
const masks=new WeakMap<Zone,Set<string>>();
export function containsZone(z:Zone,x:number,y:number){if(z.cells){let cells=masks.get(z);if(!cells){cells=new Set(z.cells.map(p=>`${p.x},${p.y}`));masks.set(z,cells);}return cells.has(`${x},${y}`);}return !!z.tiles&&x>=z.tiles.x&&y>=z.tiles.y&&x<z.tiles.x+z.tiles.width&&y<z.tiles.y+z.tiles.height;}
export function zoneAt(position:Point,zones=worldZones.filter(z=>z.id==='office')):Zone {
 const x=Math.floor(position.x+.5),y=Math.floor(position.y+.5);
 return zones.find(z=>z.id!=='office'&&containsZone(z,x,y))??zones[0];
}
export const zoneById=(id:string)=>worldZones.find(z=>z.id===id);

export const personalZone:Zone={id:'personal',name:'개인 작업실',map_id:'personal',private:true,tiles:{x:0,y:0,width:personalRoom.width,height:personalRoom.height},anchor:personalRoom.spawn,floor:'#78677e',accent:'#ebd4ec'};
export const zonesForScope=(scope:string):Zone[]=>scope.startsWith('personal:')?[personalZone]:worldZones.filter(z=>z.id==='office');
