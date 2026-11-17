import {memo,useState} from 'react';
import {manifest,characterFrame,assetUrl} from '../game/visual/catalog';
function AvatarPortraitView({variant=0,faceOnly=false}:{variant?:number;faceOnly?:boolean}){const [failed,setFailed]=useState(false),frame=characterFrame(variant,'south','idle'),a=manifest.atlases.find(a=>a.key===frame.atlas)!;return failed?<span className="visual-fallback">◕</span>:<svg className="pixel-portrait" viewBox={faceOnly?`${manifest.avatar.portrait.x} ${manifest.avatar.portrait.y} ${manifest.avatar.portrait.w} ${manifest.avatar.portrait.h}`:`0 0 ${manifest.avatar.width} ${manifest.avatar.height}`} aria-hidden="true"><image href={assetUrl(a.image)} width={a.width} height={a.height} x={-frame.rect.x} y={-frame.rect.y} onError={()=>setFailed(true)}/></svg>;}

export const AvatarPortrait=memo(AvatarPortraitView);
