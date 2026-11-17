import Phaser from 'phaser';
import {lobbyObjectFrames} from './LobbyCatalog';
import type {MapObject} from '../types';
import {furniture as fallbackFurniture} from '../art/PlaceholderArt';
import {frameAvailable} from './AssetLoader';
import {manifest,furnitureFrames} from './catalog';
// Both parts are separately depth-sorted world objects with the same ground anchor.
export class FurnitureVisual extends Phaser.GameObjects.Container{
 upper?:Phaser.GameObjects.Image;lower?:Phaser.GameObjects.Image;
 constructor(scene:Phaser.Scene,frames:ReturnType<typeof furnitureFrames>){super(scene,0,0);this.lower=scene.add.image(0,0,frames.lower.atlas,frames.lower.frame).setOrigin(manifest.furniture.origin.x,manifest.furniture.origin.y);this.add(this.lower);this.upper=scene.add.image(0,0,frames.upper.atlas,frames.upper.frame).setOrigin(manifest.furniture.origin.x,manifest.furniture.origin.y);scene.add.existing(this);this.setData('visual-source','atlas');}
 preUpdate(){if(this.upper){this.upper.setPosition(this.x,this.y).setAlpha(this.alpha).setVisible(this.visible);this.upper.setScale(this.scaleX,this.scaleY);}}
 setPosition(x=0,y=x,z?:number,w?:number):this{super.setPosition(x,y,z,w);this.upper?.setPosition(x,y);return this;}
 setDepth(value:number):this{super.setDepth(value-.15);this.upper?.setDepth(value+.15);return this;}
 setAlpha(topLeft=1,topRight?:number,bottomLeft?:number,bottomRight?:number):this{super.setAlpha(topLeft);this.upper?.setAlpha(topLeft);return this;}
 highlight(on:boolean){if(on){this.lower?.setTint(0xffebc7);this.upper?.setTint(0xffebc7);}else{this.lower?.clearTint();this.upper?.clearTint();}}
 destroy(fromScene?:boolean){this.upper?.destroy();this.upper=undefined;super.destroy(fromScene);}
}
export function furniture(scene:Phaser.Scene,o:MapObject){const custom=o.visual_asset?lobbyObjectFrames(o.visual_asset):undefined;const frames=custom&&frameAvailable(scene,custom.lower)&&frameAvailable(scene,custom.upper)?custom:furnitureFrames(o);return frameAvailable(scene,frames.lower)&&frameAvailable(scene,frames.upper)?new FurnitureVisual(scene,frames as ReturnType<typeof furnitureFrames>):fallbackFurniture(scene,o).setData('visual-source','fallback');}
export type FurnitureObject=ReturnType<typeof furniture>;
