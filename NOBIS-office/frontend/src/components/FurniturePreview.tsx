import {memo,useState} from 'react';
import type {FurnitureItem} from '../game/types';
import {furnitureFrames,manifest,assetUrl} from '../game/visual/catalog';
import {LegacyFurniturePreview} from './LegacyFurniturePreview';
function FurniturePreviewView({item,rotation=0}:{item:FurnitureItem;rotation?:number}){
 const [failed,setFailed]=useState(false),turned=rotation%180!==0,frames=furnitureFrames({kind:item.asset_key,width:turned?item.size.height:item.size.width,height:turned?item.size.width:item.size.height,rotation});
 if(failed||!frames.lower||!frames.upper)return <LegacyFurniturePreview item={item}/>;
 const bounds=(manifest.furniture.previewBounds as Record<string,{x:number;y:number;w:number;h:number}>)[frames.lower.frame.replace('/lower','')];
 return <svg viewBox={bounds?`${bounds.x} ${bounds.y} ${bounds.w} ${bounds.h}`:'0 0 128 160'} className="furniture-preview" role="img" aria-label={item.name} data-visual-source="atlas">{[frames.lower,frames.upper].map((frame,i)=>{const a=manifest.atlases.find(a=>a.key===frame.atlas)!;return <image key={i} href={assetUrl(a.image)} x={-frame.rect.x} y={-frame.rect.y} width={a.width} height={a.height} onError={()=>setFailed(true)}/>;})}</svg>;
}

export const FurniturePreview=memo(FurniturePreviewView,(a,b)=>(a.rotation??0)===(b.rotation??0)&&a.item.name===b.item.name&&a.item.asset_key===b.item.asset_key&&a.item.category===b.item.category&&a.item.size.width===b.item.size.width&&a.item.size.height===b.item.size.height);
