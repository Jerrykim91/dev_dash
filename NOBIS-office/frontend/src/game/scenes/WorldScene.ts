import {isLobby,lobbyManifest} from '../visual/LobbyCatalog';
import {drawLobbyArchitecture} from '../visual/LobbyVisual';
import Phaser from 'phaser';
import {mapForScope} from '../maps';
import type {MapObject,MapData,Player,Point,Zone} from '../types';
import type {Model} from '../bridge';
import {bridge,emit} from '../bridge';
import {CoordinateSystem} from '../systems/CoordinateSystem';
import {SurfaceCoordinates} from '../systems/SurfaceCoordinates';
import {SurfaceSystem} from '../systems/SurfaceSystem';
import {drawArchitecture} from '../visual/ArchitectureVisual';
import {CollisionSystem} from '../systems/CollisionSystem';
import {PathfindingSystem} from '../systems/PathfindingSystem';
import {MovementSystem} from '../systems/MovementSystem';
import {InteractionSystem} from '../systems/InteractionSystem';
import {zoneAt,zonesForScope} from '../systems/ZoneSystem';
import {GestureSystem} from '../systems/GestureSystem';
import {screenToWorld,worldToScreen,boundScroll,zoomAt,type WorldBounds} from '../systems/CameraSystem';
import {layoutLabels,type LabelBox} from '../systems/BubbleLayoutSystem';
import {preloadVisuals} from '../visual/AssetLoader';
import {createCharacter,animateCharacter} from '../visual/CharacterVisual';
import {furniture,FurnitureVisual,type FurnitureObject} from '../visual/FurnitureVisual';
import {drawFloor} from '../visual/FloorVisual';
import {visualLayers} from '../visual/catalog';
import design from '../../design/tokens.json';

type Avatar={labels:Phaser.GameObjects.Container;container:Phaser.GameObjects.Container;sprite:Phaser.GameObjects.Sprite;name:Phaser.GameObjects.Text;bubble:Phaser.GameObjects.Text;chatBubble:Phaser.GameObjects.Text;chatExpires:number;target:Point;ground:Point;player:Player};
export class WorldScene extends Phaser.Scene {
 model!:Model;
 portalLabels=new Map<string,Phaser.GameObjects.Text>();
 map!:MapData;roomZones:Zone[]=[];objectSprites=new Map<string,FurnitureObject>();
 coords=new CoordinateSystem();
 movement!:MovementSystem;
 collision!:CollisionSystem;
 paths!:PathfindingSystem;
 interactions!:InteractionSystem;
 avatars=new Map<string,Avatar>();
 marker!:Phaser.GameObjects.Graphics;
 trail!:Phaser.GameObjects.Graphics;
 lastSend=0;lastPosition='';frozen=false;
 gestures=new GestureSystem();tapTargets=new Map<number,{objectId?:string;playerId?:string}>();
 editing=false;preview?:Phaser.GameObjects.Graphics;ghost?:FurnitureObject;lastHover='';
 cameraMode:'follow'|'overview'|'explore'='follow';
 constructor(key:string){super(key);}
 init(data:{model:Model}){
  this.model=data.model;this.map=data.model.scope.startsWith('personal:')?(data.model.homeMap??mapForScope(data.model.scope)):(data.model.officeMap??mapForScope(data.model.scope));this.editing=false;this.roomZones=data.model.scope==='office'&&data.model.worldZones?.length?data.model.worldZones:zonesForScope(data.model.scope);this.objectSprites=new Map();this.avatars=new Map();this.lastSend=0;this.lastPosition='';this.frozen=false;
 }
 preload(){preloadVisuals(this,isLobby(this.map));}
 create(){
  this.coords=new SurfaceCoordinates(new SurfaceSystem(this.map));
  this.collision=new CollisionSystem(this.map);
  this.paths=new PathfindingSystem(this.collision);
  this.interactions=new InteractionSystem(this.paths);
  this.movement=new MovementSystem(this.model.players.find(p=>p.id===this.model.session.user.id)??this.map.spawn);
  this.drawWorld();
  this.renderObjects();
  this.preview=this.add.graphics().setDepth(visualLayers.effects);
  this.trail=this.add.graphics().setDepth(visualLayers.path);
  this.marker=this.add.graphics().setDepth(visualLayers.destination);
  this.input.addPointer(1);
  this.input.on('pointerdown',(pointer:Phaser.Input.Pointer,objects:Phaser.GameObjects.GameObject[])=>{
   if(pointer.event?.target!==this.game.canvas||this.frozen)return;
   this.gestures.down(pointer.id,{x:pointer.x,y:pointer.y},pointer.middleButtonDown());
   const target=objects.find(o=>o.getData('object-id')||o.getData('player-id'));
   this.tapTargets.set(pointer.id,{objectId:target?.getData('object-id'),playerId:target?.getData('player-id')});
  });
  this.input.on('pointermove',(pointer:Phaser.Input.Pointer)=>{
   if(this.frozen)return;
   const gesture=this.gestures.move(pointer.id,{x:pointer.x,y:pointer.y});
   if(gesture){
    this.cameraMode='explore';const c=this.cameras.main;c.stopFollow();
    if(gesture.kind==='pinch'){const next=zoomAt(c,this.worldBounds(),isLobby(this.map)?Math.max(lobbyManifest.camera.minimumZoom,c.zoom*gesture.scale):c.zoom*gesture.scale,gesture.before,gesture.after);c.setZoom(next.zoom).setScroll(next.scrollX,next.scrollY);}
    else {c.scrollX-=gesture.dx/c.zoom;c.scrollY-=gesture.dy/c.zoom;this.clampCamera();}
   }else if(this.editing&&!this.gestures.fingers.size)this.editTile(pointer,true);
  });
  this.input.on('pointerup',(pointer:Phaser.Input.Pointer)=>{
   const target=this.tapTargets.get(pointer.id);this.tapTargets.delete(pointer.id);
   if(!this.gestures.up(pointer.id,{x:pointer.x,y:pointer.y})||pointer.event?.target!==this.game.canvas||this.frozen)return;
   if(target?.playerId){emit('profile',this.avatars.get(target.playerId)?.player);return;}
   if(target?.objectId){const object=this.map.objects.find(o=>o.id===target.objectId);if(object){if(this.editing)emit('home-select',object.instance_id);else this.approach(object);}return;}
   if(this.editing)this.editTile(pointer);else this.moveTo(this.coords.toTile(screenToWorld({x:pointer.x,y:pointer.y},this.cameras.main)));
  });
  const resetGesture=()=>{this.gestures.reset();this.tapTargets.clear();};
  this.input.on('gameout',resetGesture);
  this.input.on('wheel',(pointer:Phaser.Input.Pointer,_objects:unknown,_dx:number,dy:number)=>{
   if(this.frozen)return;this.cameraMode='explore';const c=this.cameras.main;c.stopFollow();const next=zoomAt(c,this.worldBounds(),isLobby(this.map)?Math.max(lobbyManifest.camera.minimumZoom,c.zoom-dy*.001):c.zoom-dy*.001,{x:pointer.x,y:pointer.y});c.setZoom(next.zoom).setScroll(next.scrollX,next.scrollY);
  });
  const updateModel=(e:Event)=>{
   const next=(e as CustomEvent<Model>).detail;if(next.scope!==this.model.scope||next.channelId!==this.model.channelId)return;const changed=JSON.stringify(next.homeMap)!==JSON.stringify(this.model.homeMap);this.model=next;
   if(changed&&!this.editing&&next.scope.startsWith('personal:')&&next.homeMap)this.applyMap(next.homeMap);
   this.syncAvatars();this.updatePortalCounts();
   if(!this.model.canMove)this.movement.cancel();
  };
  const correction=(e:Event)=>{
   const p=(e as CustomEvent<Point&{scope?:string}>).detail;if(p.scope&&p.scope!==this.model.scope)return;this.movement.cancel();this.movement.position={x:p.x,y:p.y};
  };
  const object=(e:Event)=>{const o=this.map.objects.find(o=>o.id===(e as CustomEvent<string>).detail);if(o)this.approach(o);};
  const move=(e:Event)=>this.moveTo((e as CustomEvent<Point>).detail);
  const freeze=(e:Event)=>{
   this.frozen=(e as CustomEvent<boolean>).detail;
   if(this.frozen){resetGesture();this.movement.cancel();if(this.model.connected&&this.model.players.find(p=>p.id===this.model.session.user.id)?.participation_mode==='normal')this.sendPosition();}
  };
  const camera=(e:Event)=>{if((e as CustomEvent<string>).detail==='overview'){this.cameraMode='overview';this.fitCamera();}else {this.cameras.main.setZoom(Math.max(this.defaultZoom(),this.cameras.main.zoom));this.followPlayer();}};
  const effect=(e:Event)=>{const data=(e as CustomEvent<{object_id:string;scope:string}>).detail;if(data.scope!==this.model.scope)return;const art=this.objectSprites.get(data.object_id),o=this.map.objects.find(o=>o.id===data.object_id);if(art&&o){const p=this.coords.toWorld(o);this.tweens.killTweensOf(art);art.setPosition(p.x,p.y).setAlpha(1);this.tweens.add({targets:art,x:p.x+7,y:p.y+3,alpha:.7,duration:150,yoyo:true,repeat:1,ease:'Sine.easeInOut'});}};
  const decorate=(e:Event)=>{
   const d=(e as CustomEvent<{active:boolean;map?:MapData;preview?:MapObject;valid?:boolean}>).detail;
   if(!this.model.scope.startsWith('personal:'))return;
   if(d.active&&!this.editing){this.movement.cancel();this.sendPosition();this.cameraMode='overview';this.fitCamera();}
   this.editing=d.active;
   if(d.map&&JSON.stringify(d.map)!==JSON.stringify(this.map))this.applyMap(d.map);
   this.preview?.clear();this.ghost?.destroy();this.ghost=undefined;
   if(d.active&&d.preview){
    const o=d.preview,color=d.valid?parseInt(design.colors.success.slice(1),16):parseInt(design.colors.error.slice(1),16);
    for(let dx=0;dx<(o.width??1);dx++)for(let dy=0;dy<(o.height??1);dy++){
     const p=this.coords.toWorld({x:o.x+dx,y:o.y+dy}),points=[{x:p.x,y:p.y-16},{x:p.x+32,y:p.y},{x:p.x,y:p.y+16},{x:p.x-32,y:p.y}];
     this.preview?.fillStyle(color,.4).lineStyle(2,color).fillPoints(points,true).strokePoints(points,true,true);
    }
    const p=this.coords.toWorld(o);this.ghost=furniture(this,o).setPosition(p.x,p.y).setAlpha(.5).setDepth(visualLayers.preview);
   }
  };
  const chatBubble=(e:Event)=>{
   const d=(e as CustomEvent<{user_id:string;channel_id:string;zone:string;text:string;expires_at:number}>).detail;
   if(d.channel_id!==this.model.channelId||this.model.scope!=='office')return;
   const a=this.avatars.get(d.user_id);if(a&&this.roomZones.find(z=>z.id===d.zone)?.chat_bubbles_allowed){a.chatBubble.setText(d.text).setVisible(true);a.chatExpires=d.expires_at*1000;}
  };
  const clearBubble=(e:Event)=>{const a=this.avatars.get((e as CustomEvent<string>).detail);if(a){a.chatBubble.setVisible(false);a.chatExpires=0;}};
  const interaction=(e:Event)=>{const id=(e as CustomEvent<{object_id?:string}>).detail.object_id,art=id?this.objectSprites.get(id):undefined;if(art&&!matchMedia('(prefers-reduced-motion: reduce)').matches){this.tweens.killTweensOf(art);art.setAlpha(1);this.tweens.add({targets:art,alpha:.72,duration:90,yoyo:true});}};
  const bindings:Record<string,(e:Event)=>void>={'chat-bubble':chatBubble,'bubble-clear':clearBubble,'decorate':decorate,'model':updateModel,'correction':correction,'object-click':object,'move-to':move,'freeze':freeze,'camera-mode':camera,'object-effect':effect,'interaction':interaction};
  for(const [name,fn] of Object.entries(bindings))bridge.addEventListener(name,fn);
  const resize=()=>this.fitCamera();this.scale.on('resize',resize);
  const scale=this.scale;
  const cleanup=()=>{for(const [name,fn] of Object.entries(bindings))bridge.removeEventListener(name,fn);scale.off('resize',resize);};
  this.events.once('shutdown',cleanup);this.events.once('destroy',cleanup);
  this.updatePortalCounts();this.syncAvatars();this.fitCamera();
  this.registry.set('world',this);emit('world-ready',{room_instance_id:this.model.roomInstanceId});
 }
 updatePortalCounts(){for(const [type,label]of this.portalLabels)if(type!=='__exit__')label.setText(`${this.map.objects.find(o=>o.interaction?.room_type===type)?.label??type} · ${this.model.roomCounts?.[type]??0}/15`);}
 renderObjects(){
  for(const art of this.objectSprites.values())art.destroy();this.objectSprites.clear();
  for(const label of this.portalLabels.values())label.destroy();this.portalLabels.clear();
  for(const o of this.map.objects){
   const p=this.coords.toWorld(o);
   const art=furniture(this,o).setPosition(p.x,p.y).setDepth(o.kind==='rug'?visualLayers.rug:this.coords.depth({x:o.x+((o.width??1)-1)/2,y:o.y+((o.height??1)-1)/2}));
   this.objectSprites.set(o.id,art);
   if(!o.interaction&&!o.instance_id)continue;
   // Chairs must not capture clicks on the desk behind them through an oversized empty hit box.
   const hit=o.kind==='chair'?new Phaser.Geom.Rectangle(-22,-40,44,52):new Phaser.Geom.Rectangle(-30-32*((o.height??1)-1),-75,60+32*((o.width??1)+(o.height??1)-2),90+16*((o.width??1)+(o.height??1)-2));
   art.setInteractive(hit,Phaser.Geom.Rectangle.Contains);
   art.setData('object-id',o.id);
   if(o.interaction?.room_type||o.interaction?.kind==='public_exit'){const label=this.add.text(p.x,p.y-85,o.label,{fontSize:'13px',color:design.colors.cream,backgroundColor:design.colors.surface,padding:{x:8,y:5}}).setOrigin(.5).setDepth(visualLayers.labels).setInteractive().setData('object-id',o.id);this.portalLabels.set(o.interaction.room_type??'__exit__',label);}
   art.on('pointerover',()=>{if(art instanceof FurnitureVisual)art.highlight(true);this.game.canvas.style.cursor='pointer';emit('hint',`${o.label} · 클릭하면 다가가요`);});
   art.on('pointerout',()=>{if(art instanceof FurnitureVisual)art.highlight(false);this.game.canvas.style.cursor='default';});
  }
 }
 applyMap(map:MapData){
  const goal=this.movement.path.at(-1),approaching=!!this.movement.onArrive;
  this.map=map;this.movement.cancel();this.collision=new CollisionSystem(map);this.paths=new PathfindingSystem(this.collision);this.interactions=new InteractionSystem(this.paths);this.renderObjects();
  if(goal&&!this.editing&&!approaching){const path=this.paths.find(this.startTile(),goal)??this.paths.nearestReachable(this.startTile(),goal);if(path)this.follow(path);}
 }
 editTile(pointer:Phaser.Input.Pointer,hover=false){
  if(pointer.event?.target!==this.game.canvas)return;
  const p=screenToWorld({x:pointer.x,y:pointer.y},this.cameras.main),tile=this.coords.toTile(p),key=`${tile.x},${tile.y}`;
  if(hover&&key===this.lastHover)return;this.lastHover=key;
  emit(hover?'home-hover':'home-tile',tile);
 }
 drawWorld(){drawFloor(this,this.map,this.roomZones,this.coords,this.model.scope.startsWith('personal:'));if(this.model.scope==='office'&&(!isLobby(this.map)||!drawLobbyArchitecture(this,this.map,this.coords)))drawArchitecture(this,this.map,this.coords);}
 worldBounds():WorldBounds{if(this.map.walkable_tiles){const points=this.map.walkable_tiles.map(p=>this.coords.toWorld(p)),xs=points.map(p=>p.x),ys=points.map(p=>p.y),x=Math.min(...xs)-85,y=Math.min(...ys)-110;return{x,y,width:Math.max(...xs)+85-x,height:Math.max(...ys)+85-y};}return{x:-this.map.height*32-80,y:-110,width:(this.map.width+this.map.height)*32+160,height:(this.map.width+this.map.height)*16+220};}
 defaultZoom(){if(isLobby(this.map))return this.scale.width<760?lobbyManifest.camera.mobileZoom:lobbyManifest.camera.desktopZoom;const b=this.worldBounds(),fit=Math.min(this.scale.width/b.width,this.scale.height/b.height,1);return this.scale.width<760?1.05:Math.max(.6,Math.min(1,fit*1.6));}
 clampCamera(){const c=this.cameras.main,p=boundScroll(c,this.worldBounds());c.setScroll(p.x,p.y);}
 fitCamera(){
  const c=this.cameras.main,b=this.worldBounds();c.setBounds(b.x,b.y,b.width,b.height);
  const fit=Math.min(this.scale.width/b.width,this.scale.height/b.height,1);
  if(this.cameraMode==='overview'){c.stopFollow();c.setZoom(fit);c.centerOn(b.x+b.width/2,b.y+b.height/2);}
  else if(this.cameraMode==='follow'){c.setZoom(this.defaultZoom());this.followPlayer();}
  this.clampCamera();
 }
 followPlayer(){this.cameraMode='follow';const own=this.avatars.get(this.model.session.user.id);if(own)this.cameras.main.startFollow(own.container,true,.1,.1);}
 startTile(){return {x:Math.round(this.movement.position.x),y:Math.round(this.movement.position.y)};}
 moveTo(tile:Point){
  if(this.editing)return;
  if(!this.model.canMove||this.frozen){emit('hint','관람 중에는 이동할 수 없어요. 카메라로 월드를 둘러보세요.');return;}
  this.movement.cancel();
  const path=this.paths.find(this.startTile(),tile)??this.paths.nearestReachable(this.startTile(),tile);
  if(path){this.followPlayer();this.follow(path);emit('hint',this.collision.walkable(tile)?'연결된 월드 안에서 목적지로 걷는 중…':'가장 가까운 이동 가능 위치로 이동해요.');}
  else emit('hint','이 위치로 이동할 수 없어요.');
 }
 approach(o:MapObject){
  if(this.editing)return;
  if(!this.model.canMove||this.frozen){emit('hint','관람 중에는 오브젝트를 사용할 수 없어요.');return;}
  this.movement.cancel();const path=this.interactions.approach(this.startTile(),o);
  if(!path){emit('hint','오브젝트에 접근할 수 없어요.');return;}
  this.followPlayer();this.follow(path,()=>{this.sendPosition();emit('interact',o.id);});emit('hint',`${o.label}(으)로 이동 중…`);
 }
 sendPosition(){
  const p=this.movement.position;
  this.lastPosition=`${p.x.toFixed(3)},${p.y.toFixed(3)},${this.movement.moving}`;this.lastSend=this.time.now;
  emit('position',{x:p.x,y:p.y,zone:this.model.space,scope:this.model.scope,channel_id:this.model.channelId,direction:this.movement.direction,moving:this.movement.moving});
 }
 follow(path:Point[],done?:()=>void){
  this.movement.follow(path,done);this.trail.clear().lineStyle(2,parseInt(design.colors.accent.slice(1),16),.65);
  path.forEach((p,i)=>{if(i){const a=this.coords.toWorld(p),b=this.coords.toWorld(path[i-1]);this.trail.lineBetween(a.x,a.y,b.x,b.y);}});
  const last=this.coords.toWorld(path[path.length-1]);this.marker.clear().lineStyle(2,parseInt(design.colors.cream.slice(1),16)).strokeEllipse(last.x,last.y,25,12);
 }
 syncAvatars(){
  const ids=new Set(this.model.players.map(p=>p.id));
  for(const [id,a] of this.avatars)if(!ids.has(id)){a.container.destroy();a.labels.destroy();this.avatars.delete(id);}
  for(const player of this.model.players){
   let a=this.avatars.get(player.id);
   if(!a){
    const p=this.coords.toWorld(player),sprite=createCharacter(this,player);
    const name=this.add.text(0,7,player.nickname,{fontFamily:design.font.display,fontSize:'11px',backgroundColor:design.colors.surface+'e8',padding:{x:5,y:3},color:design.colors.text}).setOrigin(.5,0);
    const bubble=this.add.text(0,-83,'',{fontFamily:design.font.body,fontSize:'10px',backgroundColor:design.colors.text,color:design.colors.ink,padding:{x:8,y:5},wordWrap:{width:140}}).setOrigin(.5,1);
    const chatBubble=this.add.text(0,-118,'',{fontFamily:design.font.body,fontSize:'11px',backgroundColor:design.colors.cream,color:design.colors.ink,padding:{x:9,y:6},wordWrap:{width:160}}).setOrigin(.5,1).setVisible(false);
    const container=this.add.container(p.x,p.y,[sprite]),labels=this.add.container(0,0,[name,bubble,chatBubble]).setDepth(visualLayers.labels);
    if(player.id!==this.model.session.user.id)sprite.setInteractive(new Phaser.Geom.Rectangle(0,0,sprite.width,sprite.height),Phaser.Geom.Rectangle.Contains).setData('player-id',player.id);
    a={labels,container,sprite,name,bubble,chatBubble,chatExpires:0,target:player,ground:{x:player.x,y:player.y},player};this.avatars.set(player.id,a);
   }
   if(!this.roomZones.find(z=>z.id===player.zone)?.chat_bubbles_allowed||this.model.scope!=='office'){a.chatBubble.setVisible(false);a.chatExpires=0;}
   a.target={x:player.x,y:player.y};a.player=player;
   a.name.setText(`${player.participation_mode==='spectator'?'◌':player.presence==='away'?'○':'●'} ${player.nickname}`);
   const text=player.status_text??player.message;a.bubble.setText(text).setVisible(!!text);
   a.sprite.setAlpha(player.participation_mode==='spectator'?.55:1);a.sprite.y=0;
  }
 }
 positionLabels(){
  const c=this.cameras.main,boxes:LabelBox[]=[],texts=new Map<string,Phaser.GameObjects.Text>();
  for(const [id,a] of this.avatars){
   const anchor=worldToScreen(a.container,c),visible=anchor.x>=c.x-20&&anchor.x<=c.x+c.width+20&&anchor.y>=c.y-40&&anchor.y<=c.y+c.height+90;
   a.labels.setVisible(visible);if(!visible)continue;
   const own=id===this.model.session.user.id,head=anchor.y-(a.sprite.displayHeight*a.sprite.originY+4)*c.zoom;
   const put=(kind:string,text:Phaser.GameObjects.Text,y:number,priority:number)=>{text.setScale(1/c.zoom);const key=id+':'+kind;texts.set(key,text);boxes.push({id:key,x:anchor.x-text.width/2,y,width:text.width,height:text.height,priority});};
   put('name',a.name,anchor.y+7,0);
   if(a.bubble.text)put('status',a.bubble,head-a.bubble.height-6,own?4:5);else a.bubble.setVisible(false);
   if(Date.now()<a.chatExpires)put('chat',a.chatBubble,head-a.bubble.height-a.chatBubble.height-12,own?1:2);else a.chatBubble.setVisible(false);
  }
  const reserved:LabelBox[]=[{id:'zone-ui',x:c.x+8,y:c.y+8,width:145,height:30,priority:0}];
  for(const box of layoutLabels(boxes,{x:c.x+6,y:c.y+6,width:Math.max(1,c.width-12),height:Math.max(1,c.height-55)},reserved)){
   const text=texts.get(box.id)!;text.setVisible(box.visible);if(!box.visible)continue;
   const point=screenToWorld({x:box.x+box.width/2,y:box.id.endsWith(':name')?box.y:box.y+box.height},c);text.setPosition(point.x,point.y);
  }
 }
 update(time:number,delta:number){
  if(!this.movement||this.frozen)return;
  if(this.model.canMove)this.movement.update(delta/1000);
  for(const [id,a] of this.avatars){
   a.chatBubble.setVisible(Date.now()<a.chatExpires);
   const local=id===this.model.session.user.id,p=local?this.movement.position:a.target,world=this.coords.toWorld(p);
   const moving=local?this.movement.moving:Phaser.Math.Distance.Between(a.container.x,a.container.y,world.x,world.y)>1;
   if(local)a.ground={...p};
   else {const t=1-Math.exp(-delta/65);a.ground.x=Phaser.Math.Linear(a.ground.x,p.x,t);a.ground.y=Phaser.Math.Linear(a.ground.y,p.y,t);}
   const foot=this.coords.toWorld(a.ground);a.container.setPosition(foot.x,foot.y);a.container.setDepth(this.coords.depth(a.ground)+1);
   const dir=local?this.movement.direction:a.player.direction;
   animateCharacter(this,a.sprite,a.player,moving,dir);
  }
  this.positionLabels();
  if(this.cameraMode==='explore')this.clampCamera();
  if(!this.movement.moving){this.trail.clear();this.marker.clear();}
  const p=this.movement.position,signature=`${p.x.toFixed(3)},${p.y.toFixed(3)},${this.movement.moving}`;
  if(this.model.canMove&&time-this.lastSend>=100&&signature!==this.lastPosition)this.sendPosition();
 }
}
