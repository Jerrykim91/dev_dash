import {memo,useState} from 'react';
import type {FurnitureItem} from '../game/types';
import {furnitureFrames,manifest,assetUrl,frameScale,type VisualFrame} from '../game/visual/catalog';
/** 아틀라스의 한 프레임을 SVG로: 잘린 프레임은 내용 상자만(이웃 프레임이 비치지 않게), 그림 밀도(scale)만큼 줄여 월드 단위로 */
export function FrameImage({frame,onError}:{frame:VisualFrame;onError:()=>void}){const a=manifest.atlases.find(a=>a.key===frame.atlas)!,k=frameScale(frame),t=frame.trim??{x:0,y:0,w:frame.rect.w,h:frame.rect.h};return <svg x={t.x*k} y={t.y*k} width={t.w*k} height={t.h*k} viewBox={`${frame.rect.x+t.x} ${frame.rect.y+t.y} ${t.w} ${t.h}`} overflow="hidden"><image href={assetUrl(a.image)} width={a.width} height={a.height} onError={onError}/></svg>;}
import {LegacyFurniturePreview} from './LegacyFurniturePreview';
function FurniturePreviewView({item,rotation=0}:{item:FurnitureItem;rotation?:number}){
 const [failed,setFailed]=useState(false),turned=rotation%180!==0,frames=furnitureFrames({kind:item.asset_key,width:turned?item.size.height:item.size.width,height:turned?item.size.width:item.size.height,rotation});
 if(failed||!frames.lower||!frames.upper)return <LegacyFurniturePreview item={item}/>;
 const bounds=(manifest.furniture.previewBounds as Record<string,{x:number;y:number;w:number;h:number}>)[frames.lower.frame.replace('/lower','')];
 return <svg viewBox={bounds?`${bounds.x} ${bounds.y} ${bounds.w} ${bounds.h}`:'0 0 128 160'} className="furniture-preview" role="img" aria-label={item.name} data-visual-source="atlas">{[frames.lower,frames.upper].map((frame,i)=><FrameImage key={i} frame={frame} onError={()=>setFailed(true)}/>)}</svg>;
}

export const FurniturePreview=memo(FurniturePreviewView,(a,b)=>(a.rotation??0)===(b.rotation??0)&&a.item.name===b.item.name&&a.item.asset_key===b.item.asset_key&&a.item.category===b.item.category&&a.item.size.width===b.item.size.width&&a.item.size.height===b.item.size.height);
