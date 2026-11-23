import raw from './lobby-manifest.generated.json';
import type {VisualFrame} from './catalog';
export const lobbyManifest=raw;
export const isLobby=(map:{id?:string})=>map.id==='room-lobby';
export function lobbyFrame(id:string):VisualFrame|undefined{return (raw.frames as Record<string,VisualFrame>)[id];}
export function lobbyObjectFrames(id:string){const key=(raw.objects as Record<string,string>)[id]??id;return{lower:lobbyFrame(key+'/lower'),upper:lobbyFrame(key+'/upper')};}
export function lobbyFloorKind(x:number,y:number):'stone'|'wood'{const r=raw.floor.stone;return x>=r.x&&y>=r.y&&x<r.x+r.width&&y<r.y+r.height?'stone':'wood';}
export function lobbyFloor(x:number,y:number){return lobbyFrame('floor/'+lobbyFloorKind(x,y));}
