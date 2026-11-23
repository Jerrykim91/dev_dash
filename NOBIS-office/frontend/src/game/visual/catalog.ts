import defaults from './manifest.json';
import rawOverrides from './overrides.json';
import type {MapObject,Player} from '../types';
const overrides=rawOverrides as {atlases?:typeof defaults.atlases;frames?:Record<string,VisualFrame>;avatar?:Partial<typeof defaults.avatar>;furniture?:Partial<typeof defaults.furniture>;environment?:Record<string,VisualFrame & {origin?:{x:number;y:number};scale?:number}>;tilesets?:Record<string,VisualFrame>};
/** 오버라이드가 같은 키로 대체한 아틀라스를 가리키는 기본 프레임은 버린다(그 이름의 프레임이 새 아틀라스에 없다 — 예: 옛 east/west 캐릭터 프레임) */
function replacedOut(f:Record<string,VisualFrame>){const keys=new Set((overrides.atlases??[]).map(a=>a.key));return Object.fromEntries(Object.entries(f).filter(([,v])=>!keys.has(v.atlas)));}
export const manifest={...defaults,atlases:[...defaults.atlases.filter(a=>!overrides.atlases?.some(o=>o.key===a.key)),...(overrides.atlases??[])],frames:{...replacedOut(defaults.frames as Record<string,VisualFrame>),...overrides.frames},avatar:{...defaults.avatar,...overrides.avatar},furniture:{...defaults.furniture,...overrides.furniture},environment:overrides.environment??{},tilesets:overrides.tilesets??{}};
export type VisualFrame={atlas:string;frame:string;rect:{x:number;y:number;w:number;h:number};trim?:{x:number;y:number;w:number;h:number}};
/** 그림 1px의 월드 크기(그림 밀도, docs/visual-standard-v2.md §14). HD 아틀라스는 0.5 */
export function frameScale(f:VisualFrame|undefined){return (manifest.atlases.find(a=>a.key===f?.atlas) as {scale?:number}|undefined)?.scale??1;}
const frames=manifest.frames as Record<string,VisualFrame>;
export const assetUrl=(path:string)=>import.meta.env.BASE_URL+path;
export function characterVariant(palette:string,id:string){const found=manifest.avatar.palettes.findIndex(p=>p.toLowerCase()===palette.toLowerCase());return found>=0?found:[...id].reduce((a,c)=>(a*31+c.charCodeAt(0))>>>0,0)%manifest.avatar.palettes.length;}
/** seated=false(앉은 자리 없음)면 앉는 동작도 선 자세로 — 의자 없는 책상에서 허공에 앉아 타이핑하지 않게 */
export function characterState(moving:boolean,action:Player['action'],seated=true){return moving?'walking':!seated?'idle':['typing','working'].includes(action)?'typing':['sitting','resting'].includes(action)?'sitting':'idle';}
/** 실행 중 좌우 반전(C5): east·west 프레임이 아틀라스에 없으면 south·north를 뒤집어 쓴다(캐릭터 텍스처 메모리 절반). */
export const MIRROR_DIRECTION:Record<string,string>={east:'south',west:'north'};
export function characterFrameDir(variant:number,direction:string,state:string,frame=0):{frame?:VisualFrame;flip:boolean}{const own=characterFrame(variant,direction,state,frame);if(own)return{frame:own,flip:false};const m=MIRROR_DIRECTION[direction],mirrored=m?characterFrame(variant,m,state,frame):undefined;return{frame:mirrored,flip:!!mirrored};}
export function characterFrame(variant:number,direction:string,state:string,frame=0){return frames[`avatar/v${variant}/${direction}/${state}/${frame}`];}
export function furnitureFrames(o:Pick<MapObject,'kind'|'width'|'height'|'rotation'|'axis'>){const kind=o.kind==='partition'?`partition-${o.axis??'x'}`:o.kind,key=`furniture/${kind}/${o.width??1}x${o.height??1}/${o.rotation??0}`;return {lower:frames[key+'/lower'],upper:frames[key+'/upper']};}
/** 옷 갈아입기 파트(docs/visual-standard-v2.md §15): 상태별 프레임 번호, 머리 위치 표(HD px, 프레임 원점 기준), 고를 수 있는 목록 */
export type PartsMeta={states:Record<string,number[]>;anchors:Record<string,Record<string,[number,number][]>>;tops:string[];bottoms:string[];hair:string[];labels:{top:Record<string,string>;bottom:Record<string,string>;hair:Record<string,string>}};
export const partsManifest=(rawOverrides as unknown as {parts?:PartsMeta}).parts;
export const partFrame=(key:string)=>frames[`part/${key}`];
export const visualLayers={background:-3000,architectureBack:-1003,stairs:-980,wall:-1002,floor:-1000,floorDetail:-990,zoneCaption:-900,rug:-850,path:-800,destination:-700,effects:100000,preview:100001,labels:100010} as const;
