import Phaser from 'phaser';
import type {MapObject} from '../types';
// All placeholder art lives here. Replace texture generation with an atlas loader later.
export function createAvatarTextures(scene:Phaser.Scene){
 for(const dir of ['north','south','east','west'])for(let frame=0;frame<3;frame++){
  const key=`avatar-${dir}-${frame}`;if(scene.textures.exists(key))continue;
  const g=scene.make.graphics({x:0,y:0});
  g.fillStyle(0x171024,.35);g.fillEllipse(20,49,27,9);
  const step=frame===1?2:frame===2?-2:0;
  g.fillStyle(0x262137);g.fillRect(11,37,7,10+step);g.fillRect(23,37,7,10-step);
  g.fillStyle(0xebe1ff);g.fillRect(8,46+step,11,4);g.fillRect(23,46-step,11,4);
  g.fillStyle(0x8e79e5);g.fillRect(9,27,24,15);g.fillStyle(0xb9a5ff);g.fillRect(12,27,18,5);
  g.fillStyle(0xf5c6aa);g.fillRect(6,30+step,5,9);g.fillRect(31,30-step,5,9);
  g.fillRect(9,7,24,21);g.fillRect(13,26,16,4);
  g.fillStyle(0x393047);g.fillRect(7,7,28,10);g.fillRect(10,3,22,6);
  if(dir==='north'){g.fillRect(9,13,24,12);}else{
   g.fillRect(7,14,5,11);g.fillRect(30,14,5,8);
   g.fillStyle(0x342c3e);if(dir!=='west')g.fillRect(24,18,3,4);if(dir!=='east')g.fillRect(15,18,3,4);
   g.fillStyle(0xe99ba5);g.fillRect(12,24,5,2);g.fillRect(26,24,4,2);
  }
  g.generateTexture(key,40,56);g.destroy();
 }
 for(const dir of ['north','south','east','west'])if(!scene.anims.exists(`walk-${dir}`))scene.anims.create({key:`walk-${dir}`,frames:[0,1,0,2].map(i=>({key:`avatar-${dir}-${i}`})),frameRate:9,repeat:-1});
}
export function furniture(scene:Phaser.Scene,o:MapObject){
 const g=scene.add.graphics();
 // Visuals are replaceable; catalog footprints drive collision independently.
 const box=(top:number,left:number,right:number,h:number)=>{
  const w=o.width??1,d=o.height??1;
  const a={x:0,y:-14-h},b={x:32*(w-1)+27,y:16*(w-1)-h},c={x:32*(w-d),y:16*(w+d-2)+14-h},e={x:-32*(d-1)-27,y:16*(d-1)-h};
  g.fillStyle(left);g.fillPoints([e,c,{x:c.x,y:c.y+h},{x:e.x,y:e.y+h}],true);
  g.fillStyle(right);g.fillPoints([c,b,{x:b.x,y:b.y+h},{x:c.x,y:c.y+h}],true);
  g.fillStyle(top);g.fillPoints([a,b,c,e],true);
 };
 if(o.kind==='partition'){
  // Each segment spans one projected tile step. Adjacent endpoints coincide
  // on either axis, so a wall reads as a continuous panel rather than a row of gates.
  const a={x:o.axis==='y'?16:-16,y:-8};
  const b={x:-a.x,y:8};
  const height=40;
  g.fillStyle(0xbad8e5,.32);
  g.fillPoints([a,b,{x:b.x,y:b.y-height},{x:a.x,y:a.y-height}],true);
  g.lineStyle(3,0x7a6687);g.lineBetween(a.x,a.y,b.x,b.y);
  g.lineStyle(2,0xb9afcf);g.lineBetween(a.x,a.y-height,b.x,b.y-height);
  g.lineStyle(1,0xe9f3fa,.5);g.lineBetween(a.x,a.y-height+7,b.x,b.y-height+7);
  g.fillStyle(0xe1e0ee);
  for(const p of [a,b])g.fillRect(p.x-1,p.y-height,3,height+1);
 }else if(o.kind==='arcade'){
  box(0xb194db,0x513c6c,0x79608f,58);g.fillStyle(0x211c35);g.fillRect(-18,-64,36,27);g.fillStyle(0xc5dba5);g.fillRect(-12,-59,24,15);g.fillStyle(0xffd199);g.fillRect(-16,-28,32,8);g.fillStyle(0xd7b8ed);g.fillCircle(-7,-25,3);g.fillStyle(0xff9dba);g.fillCircle(8,-25,3);
 }else if(o.kind==='rug'){
  g.fillStyle(0xb89bd0);g.fillPoints([{x:0,y:-14},{x:58,y:15},{x:0,y:44},{x:-58,y:15}],true);g.lineStyle(3,0xe2cfe8);g.strokePoints([{x:0,y:-7},{x:43,y:15},{x:0,y:37},{x:-43,y:15}],true,true);
 }else if(o.kind==='lamp'){
  g.fillStyle(0x88718f);g.fillEllipse(0,5,25,12);g.fillStyle(0xd4b88c);g.fillRect(-3,-50,6,54);g.fillStyle(0xf6deab);g.fillPoints([{x:-13,y:-68},{x:13,y:-68},{x:24,y:-45},{x:-24,y:-45}],true);g.fillStyle(0xffe2a3,.12);g.fillEllipse(0,0,75,32);
 }else if(o.kind==='decoration'){
  box(0xdcc4a6,0xa2828e,0xbe9a9e,10);g.fillStyle(0xf4d9b5);g.fillRect(-16,-35,32,24);g.fillTriangle(-16,-35,-9,-47,-1,-35);g.fillTriangle(2,-35,10,-47,16,-35);g.fillStyle(0x4b3a56);g.fillRect(-9,-28,3,4);g.fillRect(7,-28,3,4);
 }else if(o.kind==='desk'){
  box(0xe1c8a6,0x927086,0xb18b98,22);g.fillStyle(0xf2e7d0);g.fillRect(-17,-30,15,8);g.fillStyle(0x8e749b);g.fillRect(8,-34,8,12);
 }else if(o.kind==='table'){
  box(0xd8bd99,0x876b69,0xaa8580,22);g.fillStyle(0xf7e8cb);g.fillRect(-7,-32,12,8);
 }else if(o.kind==='chair'){
  box(0xb39bcf,0x615071,0x826698,15);g.fillStyle(0xa88ec4);g.fillRect(-17,-43,34,20);g.fillStyle(0x3f354e);g.fillRect(-18,0,5,15);g.fillRect(15,0,5,15);
 }else if(o.kind==='coffee'){
  box(0x9b7d73,0x5b4352,0x765669,25);g.fillStyle(0x302936);g.fillRect(-16,-57,32,32);g.fillStyle(0xd3bbb6);g.fillRect(-12,-53,24,10);g.fillStyle(0xf4e4d4);g.fillRect(-6,-36,12,11);g.fillStyle(0x8ad2ab);g.fillRect(8,-48,4,4);
 }else if(o.kind==='whiteboard'){
  g.fillStyle(0x5b4c69);g.fillRect(-22,-62,5,66);g.fillRect(17,-62,5,66);g.fillStyle(0xded6e9);g.fillRect(-30,-70,60,43);g.fillStyle(0x9180a4);g.fillRect(-25,-62,22,3);g.fillRect(-25,-53,40,3);g.fillStyle(0x9976b8);g.fillRect(-25,-44,15,3);
 }else if(o.kind==='bookshelf'){
  box(0xb9977f,0x61465a,0x866275,62);g.fillStyle(0x443047);g.fillRect(-20,-57,40,45);g.fillStyle(0xa68bbf);for(let i=0;i<5;i++)g.fillRect(-17+i*7,-52,5,17);g.fillStyle(0xd3b18d);g.fillRect(-20,-31,40,4);g.fillStyle(0x91b5a0);for(let i=0;i<4;i++)g.fillRect(-15+i*8,-25,6,13);g.fillStyle(0xffdf8c);g.fillRect(12,-49,4,5);
 }else if(o.kind==='plant'){
  box(0xb68eac,0x75506c,0x9d6e90,15);g.fillStyle(0x417f68);g.fillRect(-5,-57,10,42);g.fillRect(-22,-48,17,12);g.fillRect(5,-56,18,12);g.fillStyle(0x83c9a1);g.fillRect(-18,-51,14,6);g.fillRect(6,-59,13,6);
 }else if(o.kind==='door'){
  g.fillStyle(0x1f182f);g.fillRect(-19,-62,38,66);g.lineStyle(3,0xd3b281);g.strokeRect(-19,-62,38,66);g.fillStyle(0xf2d08b);g.fillRect(9,-28,4,4);g.fillStyle(0xb5a0ee,.15);g.fillEllipse(0,13,61,18);
 }else if(o.kind==='bed'){
  box(0xaaa0db,0x564477,0x78649c,22);g.fillStyle(0xe9dcec);g.fillRect(-18,-29,28,10);g.fillStyle(0x8477b4);g.fillRect(-10,-14,32,10);
 }else if(o.kind==='sofa'){
  box(0xb98aa8,0x614967,0x875a7e,24);g.fillStyle(0xc69ab8);g.fillRect(-25,-40,50,15);g.fillStyle(0x9b749a);g.fillRect(-27,-28,9,26);g.fillRect(20,-28,9,26);
 }else{
  box(0xb58d77,0x66506a,0x8c6c7f,24);g.fillStyle(0x211f39);g.fillRect(-15,-60,30,23);g.fillStyle(0x8ad5d2);g.fillRect(-12,-57,24,17);g.fillStyle(0xd1f3de);g.fillRect(-9,-54,11,2);g.fillRect(-9,-49,17,2);g.fillStyle(0x40344d);g.fillRect(-3,-37,6,9);g.fillRect(-10,-28,20,3);
 }
 return g;
}
