import Phaser from 'phaser';
import type {Player} from '../types';
import {createAvatarTextures} from '../art/PlaceholderArt';
import {manifest,characterVariant,characterState,characterFrame,MIRROR_DIRECTION,partsManifest,partFrame,type VisualFrame} from './catalog';
import {frameAvailable} from './AssetLoader';
/** 방향 프레임 결정(C5): 해당 방향 프레임이 실제 텍스처에 모두 있으면 그대로, 아니면 반대편(south/north)을 좌우 반전.
 * 매니페스트 병합 결과만 믿으면 안 된다 — 기본 매니페스트의 east/west 항목이 교체된 옛 아틀라스의 프레임 이름을 가리킬 수 있다. */
function resolveDirection(scene:Phaser.Scene,variant:number,direction:string,state:string,count:number):{seq:(VisualFrame|undefined)[];flip:boolean;dir:string}{
 const of=(d:string)=>Array.from({length:count},(_,i)=>characterFrame(variant,d,state,i));
 const own=of(direction);if(own.every(f=>frameAvailable(scene,f)))return{seq:own,flip:false,dir:direction};
 const m=MIRROR_DIRECTION[direction];if(m){const mir=of(m);if(mir.every(f=>frameAvailable(scene,f)))return{seq:mir,flip:true,dir:m};}
 return{seq:own,flip:false,dir:direction};
}
function legacy(scene:Phaser.Scene){if(!scene.textures.exists('avatar-south-0'))createAvatarTextures(scene);}
export function createCharacter(scene:Phaser.Scene,player:Player){
 const variant=characterVariant(player.avatar.palette,player.id),frame=characterFrame(variant,'south','idle');
 if(!frameAvailable(scene,frame)){legacy(scene);return scene.add.sprite(0,0,'avatar-south-0').setOrigin(.5,1).setScale(1.25).setData('visual-source','fallback');}
 const sprite=scene.add.sprite(0,0,frame.atlas,frame.frame).setOrigin(manifest.avatar.origin.x,manifest.avatar.origin.y).setScale(manifest.avatar.scale).setData('visual-source','atlas');
 // 옷 갈아입기 레이어(하의 → 상의 → 머리). 파트를 고르지 않은 사용자는 숨겨 둔다
 const base=partFrame('base/south/0');
 if(partsManifest&&frameAvailable(scene,base)){
  const mk=()=>scene.add.sprite(0,0,base.atlas,base.frame).setOrigin(manifest.avatar.origin.x,manifest.avatar.origin.y).setScale(manifest.avatar.scale).setVisible(false);
  const hair=scene.add.image(0,0,base.atlas,base.frame).setOrigin(.5).setScale(manifest.avatar.scale).setVisible(false);
  sprite.setData('layers',{bottom:mk(),top:mk(),hair} satisfies Layers);
 }
 return sprite;
}
type Layers={bottom:Phaser.GameObjects.Sprite;top:Phaser.GameObjects.Sprite;hair:Phaser.GameObjects.Image};
/** 컨테이너에 함께 넣을 레이어(그리는 순서대로) */
export function characterLayers(sprite:Phaser.GameObjects.Sprite):Phaser.GameObjects.GameObject[]{const l=sprite.getData('layers') as Layers|undefined;return l?[l.bottom,l.top,l.hair]:[];}
type PartsMode={hair:string;top:string;bottom:string;dir:string;flip:boolean;state:string};
/** 고른 파트의 프레임이 모두 있으면 파트 모드(남·북만 그리고 동·서는 반전) */
function partsMode(scene:Phaser.Scene,player:Player,direction:string,state:string):PartsMode|undefined{
 const p=player.avatar.parts;if(!p||!partsManifest)return;const own=direction==='south'||direction==='north',dir=own?direction:MIRROR_DIRECTION[direction];if(!dir)return;
 const ks=partsManifest.states[state]??[],need=[...ks.flatMap(k=>[`base/${dir}/${k}`,`top/${p.top}/${dir}/${k}`,`bottom/${p.bottom}/${dir}/${k}`]),`hair/${p.hair}/${dir}`];
 return need.every(n=>frameAvailable(scene,partFrame(n)))?{...p,dir,flip:!own,state}:undefined;
}
/** 기본 몸의 현재 프레임에 맞춰 하의·상의 프레임과 머리 위치(프레임별 표)를 맞춘다. 매 프레임 호출 */
function syncLayers(sprite:Phaser.GameObjects.Sprite){
 const l=sprite.getData('layers') as Layers|undefined;if(!l)return;const m=sprite.getData('parts-mode') as PartsMode|undefined;
 for(const o of [l.bottom,l.top,l.hair])o.setVisible(!!m&&sprite.visible);if(!m||!partsManifest)return;
 const ks=partsManifest.states[m.state],i=Math.max(0,(sprite.anims.currentFrame?.index??1)-1)%ks.length,k=ks[i];
 const set=(o:Phaser.GameObjects.Sprite|Phaser.GameObjects.Image,key:string)=>{const f=partFrame(key)!;if(o.frame.name!==f.frame||o.texture.key!==f.atlas)o.setTexture(f.atlas,f.frame);};
 set(l.bottom,`bottom/${m.bottom}/${m.dir}/${k}`);set(l.top,`top/${m.top}/${m.dir}/${k}`);set(l.hair,`hair/${m.hair}/${m.dir}`);
 const s=manifest.avatar.scale,[ax,ay]=partsManifest.anchors[m.dir][m.hair][k],ox=manifest.avatar.origin.x*manifest.avatar.width,oy=manifest.avatar.origin.y*manifest.avatar.height,dx=(ax-ox)*s*(m.flip?-1:1),dy=(ay-oy)*s;
 for(const o of [l.bottom,l.top])o.setPosition(sprite.x,sprite.y).setFlipX(m.flip).setAlpha(sprite.alpha);
 l.hair.setPosition(sprite.x+dx,sprite.y+dy).setFlipX(m.flip).setAlpha(sprite.alpha);
}
export function animateCharacter(scene:Phaser.Scene,sprite:Phaser.GameObjects.Sprite,player:Player,moving:boolean,direction:string){
 if(animateParts(scene,sprite,player,moving,direction))return;
 sprite.setData('parts-mode',undefined);syncLayers(sprite);
 const state=characterState(moving,player.action,!!player.seat_id),variant=characterVariant(player.avatar.palette,player.id),config=manifest.avatar.animations[state],{seq:sequence,flip,dir}=resolveDirection(scene,variant,direction,state,config.frames),frame=sequence[0];sprite.setData('visual-state',state).setData('visual-direction',direction);
 const reduced=!!scene.registry.get('visual-reduced-motion'),signature=`${variant}/${direction}/${state}/${reduced}`;if(sprite.getData('visual-animation')===signature)return;
  if(!sequence.every(f=>frameAvailable(scene,f))){
  const r=resolveDirection(scene,variant,direction,'idle',1),idle=r.seq[0],idleFlip=r.flip;if(frameAvailable(scene,idle)){sprite.stop();sprite.setTexture(idle.atlas,idle.frame).clearTint().setFlipX(idleFlip);sprite.setData('visual-source','atlas-idle-fallback');return;}
  legacy(scene);sprite.setFlipX(false).setOrigin(.5,1).setScale(1.25).setData('visual-source','fallback');if(moving)sprite.play(`walk-${direction}`,true);else{sprite.stop();sprite.setTexture(`avatar-${direction}-0`);}sprite.setTint(/^#[a-f\d]{6}$/i.test(player.avatar.palette)?parseInt(player.avatar.palette.slice(1),16):0xffffff);return;
 }
 sprite.clearTint().setFlipX(flip).setData('visual-source','atlas');sprite.setOrigin(manifest.avatar.origin.x,manifest.avatar.origin.y).setScale(manifest.avatar.scale);
 sprite.setData('visual-animation',signature);
 if(reduced){sprite.stop();sprite.setTexture(frame!.atlas,frame!.frame);return;}
 const key=`nobis-v${variant}-${dir}-${state}`;
 if(!scene.anims.exists(key))scene.anims.create({key,frames:sequence.map(f=>({key:f!.atlas,frame:f!.frame})),frameRate:config.fps,repeat:-1});
 sprite.play(key,true);
}

/** 파트 모드 애니메이션: 기본 몸 스프라이트가 애니메이션을 돌고, 레이어는 그 프레임 번호를 따라간다. 파트 모드가 아니면 false */
function animateParts(scene:Phaser.Scene,sprite:Phaser.GameObjects.Sprite,player:Player,moving:boolean,direction:string):boolean{
 const state=characterState(moving,player.action,!!player.seat_id),m=partsMode(scene,player,direction,state);if(!m||!partsManifest)return false;
 const reduced=!!scene.registry.get('visual-reduced-motion'),signature=`parts/${m.hair}/${m.top}/${m.bottom}/${m.dir}/${m.flip}/${state}/${reduced}`;
 sprite.setData('parts-mode',m).setData('visual-state',state).setData('visual-direction',direction).setData('visual-source','parts');
 if(sprite.getData('visual-animation')!==signature){
  sprite.setData('visual-animation',signature);sprite.clearTint().setFlipX(m.flip).setOrigin(manifest.avatar.origin.x,manifest.avatar.origin.y).setScale(manifest.avatar.scale);
  const frames=partsManifest.states[state].map(k=>partFrame(`base/${m.dir}/${k}`)!),config=manifest.avatar.animations[state as keyof typeof manifest.avatar.animations];
  if(reduced){sprite.stop();sprite.setTexture(frames[0].atlas,frames[0].frame);}
  else{const key=`nobis-part-base-${m.dir}-${state}`;if(!scene.anims.exists(key))scene.anims.create({key,frames:frames.map(f=>({key:f.atlas,frame:f.frame})),frameRate:config?.fps??6,repeat:-1});sprite.play(key,true);}
 }
 syncLayers(sprite);
 return true;
}
