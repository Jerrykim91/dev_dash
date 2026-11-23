import Phaser from 'phaser';
import {lobbyObjectFrames} from './LobbyCatalog';
import type {MapObject} from '../types';
import {furniture as fallbackFurniture} from '../art/PlaceholderArt';
import {frameAvailable} from './AssetLoader';
import {manifest,furnitureFrames,frameScale,type VisualFrame} from './catalog';
import type {CoordinateSystem} from '../systems/CoordinateSystem';
/** 프레임별 기준점(원점 칸 중심). 큰 가구(회의 테이블 3×5 등)는 프레임에 기준점을 적는다 */
export const frameOrigin=(f:VisualFrame)=>(f as VisualFrame&{origin?:{x:number;y:number}}).origin??manifest.furniture.origin;
import {wallDoorFrames} from './WallVisual';
// Both parts are separately depth-sorted world objects with the same ground anchor.
export class FurnitureVisual extends Phaser.GameObjects.Container{
 upper?:Phaser.GameObjects.Image;lower?:Phaser.GameObjects.Image;
 upperScale=1;
 constructor(scene:Phaser.Scene,frames:ReturnType<typeof furnitureFrames>){super(scene,0,0);const o0=frameOrigin(frames.lower);this.lower=scene.add.image(0,0,frames.lower.atlas,frames.lower.frame).setOrigin(o0.x,o0.y).setScale(frameScale(frames.lower));this.upperScale=frameScale(frames.upper);this.add(this.lower);this.upper=scene.add.image(0,0,frames.upper.atlas,frames.upper.frame).setOrigin(frameOrigin(frames.upper).x,frameOrigin(frames.upper).y).setScale(this.upperScale);scene.add.existing(this);this.setData('visual-source','atlas');}
 preUpdate(){if(this.upper){this.upper.setPosition(this.x,this.y).setAlpha(this.alpha).setVisible(this.visible);this.upper.setScale(this.scaleX*this.upperScale,this.scaleY*this.upperScale);}}
 setPosition(x=0,y=x,z?:number,w?:number):this{super.setPosition(x,y,z,w);this.upper?.setPosition(x,y);for(const s of this.slices??[])s.setPosition(x,y);return this;}
 /** 큰 가구: 월드 폭 32px 세로 띠로 잘라, 띠마다 그 띠에 걸친 칸 중 가장 앞 칸의 깊이를 준다(앉거나 지나가는 캐릭터와 앞뒤가 맞게). */
 slices:Phaser.GameObjects.Image[]=[];
 sliceByFootprint(o:{x:number;y:number;width?:number;height?:number},coords:CoordinateSystem){
  const img=this.lower;if(!img)return this;const w=o.width??1,h=o.height??1;if(w*h<4)return this;
  const f=img.frame,k=img.scaleX,left=this.x-img.originX*f.realWidth*k,tiles:{x:number;y:number}[]=[];for(let i=0;i<w;i++)for(let j=0;j<h;j++)tiles.push({x:o.x+i,y:o.y+j});
  for(let sx=Math.floor(left/32)*32;sx<left+f.realWidth*k;sx+=32){
   const cover=tiles.filter(t=>{const c=coords.toWorld(t).x;return c+32>sx&&c-32<sx+32;});if(!cover.length)continue;
   const depth=Math.max(...cover.map(t=>coords.depth(t)))-.15,cx=Math.max(0,(sx-left)/k),cw=Math.min(f.realWidth-cx,32/k);if(cw<=0)continue;
   this.slices.push(this.scene.add.image(this.x,this.y,img.texture.key,f.name).setOrigin(img.originX,img.originY).setScale(k).setCrop(cx,0,cw,f.realHeight).setDepth(depth));
  }
  if(this.slices.length)img.setVisible(false);return this;
 }
 // 깊이 규칙 v2: lower −0.15 < 앉은 캐릭터 +0.10 < upper +0.20 (등받이가 앉은 사람 앞)
 setDepth(value:number):this{super.setDepth(value-.15);this.upper?.setDepth(value+.2);return this;}
 setAlpha(topLeft=1,topRight?:number,bottomLeft?:number,bottomRight?:number):this{super.setAlpha(topLeft);this.upper?.setAlpha(topLeft);for(const s of this.slices??[])s.setAlpha(topLeft);return this;}
 highlight(on:boolean){for(const t of [this.lower,this.upper,...(this.slices??[])]){if(!t)continue;if(on)t.setTint(0xffebc7);else t.clearTint();}}
 destroy(fromScene?:boolean){this.upper?.destroy();this.upper=undefined;for(const s of this.slices)s.destroy();this.slices=[];super.destroy(fromScene);}
}
export function furniture(scene:Phaser.Scene,o:MapObject,room='plain'){const wallDoor=wallDoorFrames(o,room);if(wallDoor&&frameAvailable(scene,wallDoor.lower)&&frameAvailable(scene,wallDoor.upper))return new FurnitureVisual(scene,wallDoor as ReturnType<typeof furnitureFrames>);const hd=o.visual_asset?{lower:(manifest.frames as Record<string,VisualFrame>)[`lobby-object/${o.visual_asset}/lower`],upper:(manifest.frames as Record<string,VisualFrame>)[`lobby-object/${o.visual_asset}/upper`]}:undefined;const custom=hd&&frameAvailable(scene,hd.lower)&&frameAvailable(scene,hd.upper)?hd:o.visual_asset?lobbyObjectFrames(o.visual_asset):undefined;const frames=custom&&frameAvailable(scene,custom.lower)&&frameAvailable(scene,custom.upper)?custom:furnitureFrames(o);return frameAvailable(scene,frames.lower)&&frameAvailable(scene,frames.upper)?new FurnitureVisual(scene,frames as ReturnType<typeof furnitureFrames>):fallbackFurniture(scene,o).setData('visual-source','fallback');}
export type FurnitureObject=ReturnType<typeof furniture>;
