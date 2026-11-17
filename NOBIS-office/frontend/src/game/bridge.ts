import type {Chat,Player,Point,Session,MapData,Zone} from './types';
export type Model={session:Session;space:string;scope:string;players:Player[];connected:boolean;chat:Chat[];notice:string;canMove:boolean;channelId:string;roomInstanceId?:string;roomCounts?:Record<string,number>;homeMap?:MapData;officeMap?:MapData;worldRevision?:string;worldZones?:Zone[]};
export const bridge=new EventTarget();
export function emit(type:string,detail:unknown){bridge.dispatchEvent(new CustomEvent(type,{detail}));}
export const commands={move:(p:Point)=>emit('move-to',p),object:(id:string)=>emit('object-click',id)};
