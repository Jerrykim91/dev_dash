import {memo,useState} from 'react';
import {manifest,characterFrame} from '../game/visual/catalog';
import {FrameImage} from '../components/FurniturePreview';
function AvatarPortraitView({variant=0,faceOnly=false}:{variant?:number;faceOnly?:boolean}){const [failed,setFailed]=useState(false),frame=characterFrame(variant,'south','idle'),k=manifest.avatar.scale??1;return failed?<span className="visual-fallback">◕</span>:<svg className="pixel-portrait" viewBox={faceOnly?`${manifest.avatar.portrait.x} ${manifest.avatar.portrait.y} ${manifest.avatar.portrait.w} ${manifest.avatar.portrait.h}`:`0 0 ${manifest.avatar.width*k} ${manifest.avatar.height*k}`} aria-hidden="true"><FrameImage frame={frame} onError={()=>setFailed(true)}/></svg>;}

export const AvatarPortrait=memo(AvatarPortraitView);
