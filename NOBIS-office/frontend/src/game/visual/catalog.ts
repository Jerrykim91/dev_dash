import defaults from './manifest.json';
import rawOverrides from './overrides.json';
import type {MapObject,Player} from '../types';
const overrides=rawOverrides as {atlases?:typeof defaults.atlases;frames?:Record<string,VisualFrame>;avatar?:Partial<typeof defaults.avatar>;furniture?:Partial<typeof defaults.furniture>;environment?:Record<string,VisualFrame & {origin?:{x:number;y:number};scale?:number}>;tilesets?:Record<string,VisualFrame>};
export const manifest={...defaults,atlases:[...defaults.atlases.filter(a=>!overrides.atlases?.some(o=>o.key===a.key)),...(overrides.atlases??[])],frames:{...defaults.frames,...overrides.frames},avatar:{...defaults.avatar,...overrides.avatar},furniture:{...defaults.furniture,...overrides.furniture},environment:overrides.environment??{},tilesets:overrides.tilesets??{}};
export type VisualFrame={atlas:string;frame:string;rect:{x:number;y:number;w:number;h:number}};
const frames=manifest.frames as Record<string,VisualFrame>;
export const assetUrl=(path:string)=>import.meta.env.BASE_URL+path;
export function characterVariant(palette:string,id:string){const found=manifest.avatar.palettes.findIndex(p=>p.toLowerCase()===palette.toLowerCase());return found>=0?found:[...id].reduce((a,c)=>(a*31+c.charCodeAt(0))>>>0,0)%manifest.avatar.palettes.length;}
export function characterState(moving:boolean,action:Player['action']){return moving?'walking':['typing','working'].includes(action)?'typing':['sitting','resting'].includes(action)?'sitting':'idle';}
export function characterFrame(variant:number,direction:string,state:string,frame=0){return frames[`avatar/v${variant}/${direction}/${state}/${frame}`];}
export function furnitureFrames(o:Pick<MapObject,'kind'|'width'|'height'|'rotation'|'axis'>){const kind=o.kind==='partition'?`partition-${o.axis??'x'}`:o.kind,key=`furniture/${kind}/${o.width??1}x${o.height??1}/${o.rotation??0}`;return {lower:frames[key+'/lower'],upper:frames[key+'/upper']};}
export const visualLayers={background:-3000,architectureBack:-1003,stairs:-980,wall:-1002,floor:-1000,floorDetail:-990,zoneCaption:-900,rug:-850,path:-800,destination:-700,effects:100000,preview:100001,labels:100010} as const;
