import Phaser from 'phaser';
import type {Player} from '../types';
import {createAvatarTextures} from '../art/PlaceholderArt';
import {manifest,characterVariant,characterState,characterFrame} from './catalog';
import {frameAvailable} from './AssetLoader';
function legacy(scene:Phaser.Scene){if(!scene.textures.exists('avatar-south-0'))createAvatarTextures(scene);}
export function createCharacter(scene:Phaser.Scene,player:Player){
 const variant=characterVariant(player.avatar.palette,player.id),frame=characterFrame(variant,'south','idle');
 if(!frameAvailable(scene,frame)){legacy(scene);return scene.add.sprite(0,0,'avatar-south-0').setOrigin(.5,1).setScale(1.25).setData('visual-source','fallback');}
 return scene.add.sprite(0,0,frame.atlas,frame.frame).setOrigin(manifest.avatar.origin.x,manifest.avatar.origin.y).setScale(manifest.avatar.scale).setData('visual-source','atlas');
}
export function animateCharacter(scene:Phaser.Scene,sprite:Phaser.GameObjects.Sprite,player:Player,moving:boolean,direction:string){
 const state=characterState(moving,player.action),variant=characterVariant(player.avatar.palette,player.id),config=manifest.avatar.animations[state],frame=characterFrame(variant,direction,state);sprite.setData('visual-state',state).setData('visual-direction',direction);
 const reduced=!!scene.registry.get('visual-reduced-motion'),signature=`${variant}/${direction}/${state}/${reduced}`;if(sprite.getData('visual-animation')===signature)return;
 const sequence=Array.from({length:config.frames},(_,i)=>characterFrame(variant,direction,state,i));
 if(!sequence.every(f=>frameAvailable(scene,f))){
  const idle=characterFrame(variant,direction,'idle');if(frameAvailable(scene,idle)){sprite.stop();sprite.setTexture(idle.atlas,idle.frame).clearTint();sprite.setData('visual-source','atlas-idle-fallback');return;}
  legacy(scene);sprite.setOrigin(.5,1).setScale(1.25).setData('visual-source','fallback');if(moving)sprite.play(`walk-${direction}`,true);else{sprite.stop();sprite.setTexture(`avatar-${direction}-0`);}sprite.setTint(/^#[a-f\d]{6}$/i.test(player.avatar.palette)?parseInt(player.avatar.palette.slice(1),16):0xffffff);return;
 }
 sprite.clearTint().setData('visual-source','atlas');sprite.setOrigin(manifest.avatar.origin.x,manifest.avatar.origin.y).setScale(manifest.avatar.scale);
 sprite.setData('visual-animation',signature);
 if(reduced){sprite.stop();sprite.setTexture(frame.atlas,frame.frame);return;}
 const key=`nobis-v${variant}-${direction}-${state}`;
 if(!scene.anims.exists(key))scene.anims.create({key,frames:sequence.map(f=>({key:f.atlas,frame:f.frame})),frameRate:config.fps,repeat:-1});
 sprite.play(key,true);
}
