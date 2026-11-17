import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CoordinateSystem} from './CoordinateSystem';
import {CollisionSystem} from './CollisionSystem';
import {PathfindingSystem} from './PathfindingSystem';
import {MovementSystem} from './MovementSystem';
import {InteractionSystem} from './InteractionSystem';
import type {MapData} from '../types';
const map:MapData={width:6,height:6,spawn:{x:0,y:0},objects:[{id:'pc',kind:'computer',x:2,y:2,label:'PC'},{id:'wall',kind:'wall',x:2,y:1,label:'wall'}]};
const collision=new CollisionSystem(map),paths=new PathfindingSystem(collision);
test('isometric coordinates round trip including nonzero origin',()=>{const c=new CoordinateSystem(64,32,{x:120,y:50});for(let x=0;x<14;x++)for(let y=0;y<12;y++)assert.deepEqual(c.toTile(c.toWorld({x,y})),{x,y});});
test('A* takes shortest four-neighbor route around furniture',()=>{const p=paths.find({x:1,y:2},{x:3,y:2})!;assert.equal(p.length,5);assert(p.every(n=>collision.walkable(n)));for(let i=1;i<p.length;i++)assert.equal(Math.abs(p[i].x-p[i-1].x)+Math.abs(p[i].y-p[i-1].y),1);});
test('bounds, blocked and disconnected destinations',()=>{assert.equal(paths.find({x:0,y:0},{x:2,y:2}),null);assert.equal(collision.walkable({x:-1,y:0}),false);const c=new CollisionSystem({...map,width:3,height:3,objects:[0,1,2].map(y=>({id:`${y}`,kind:'wall',x:1,y,label:'wall'}))});const p=new PathfindingSystem(c);assert.equal(p.find({x:0,y:0},{x:2,y:0}),null);assert.deepEqual(p.nearestReachable({x:0,y:0},{x:2,y:0})?.at(-1),{x:0,y:0});});
test('blocked target resolves to reachable floor',()=>{const p=paths.nearestReachable({x:0,y:0},{x:2,y:2})!;assert(p.length);assert(collision.walkable(p.at(-1)!));});
test('new route cancels pending interaction and tracks new path',()=>{let old=false,arrived=false;const m=new MovementSystem({x:0,y:0});m.follow([{x:1,y:0}],()=>{old=true;});m.update(.1);m.follow([{x:0,y:0},{x:0,y:1}],()=>{arrived=true;});for(let i=0;i<30;i++)m.update(.05);assert.equal(old,false);assert.equal(arrived,true);assert.deepEqual(m.position,{x:0,y:1});assert.equal(m.direction,'south');});
test('object approach stops on an accessible adjacent tile',()=>{const p=new InteractionSystem(paths).approach({x:0,y:0},map.objects[0])!;const end=p.at(-1)!;assert(collision.walkable(end));assert.equal(Math.abs(end.x-2)+Math.abs(end.y-2),1);});
test('delta is capped and arrival fires only once',()=>{const m=new MovementSystem({x:0,y:0});let calls=0;m.follow([{x:1,y:0}],()=>calls++);m.update(10);assert(m.position.x<=.3200001);for(let i=0;i<20;i++)m.update(.1);assert.equal(calls,1);});


import {officeWorld,roomWorlds,roomDefinitions} from '../maps';
import {zoneAt,worldZones} from './ZoneSystem';
test('each hybrid room is navigable independently and lobby portals reference valid definitions',()=>{
 for(const [type,map]of Object.entries(roomWorlds)){const c=new CollisionSystem(map),p=new PathfindingSystem(c);for(const o of map.objects.filter(o=>o.interaction))assert(new InteractionSystem(p).approach(map.spawn,o)?.length,type+'/'+o.id);}
 for(const d of roomDefinitions)assert(roomWorlds[d.room_type]);assert(!officeWorld.objects.some(o=>o.id==='desk-0'));
});
test('room zone compatibility retains office and personal fallbacks',()=>{assert.equal(zoneAt(officeWorld.spawn).id,'office');assert.equal(zoneAt(roomWorlds.cafe.spawn,[worldZones.find(z=>z.id==='cafe')!]).id,'cafe');});

import {footprint,placementError,layoutMap} from './PlacementSystem';
import catalogData from '../../../../shared/furniture-catalog.json';
import type {FurnitureItem,FurniturePlacement} from '../types';
const homeMap:MapData={width:12,height:10,spawn:{x:6,y:7},objects:[{id:'home-exit',kind:'door',label:'Exit',x:10,y:8}]};
const catalog=catalogData as FurnitureItem[],desk=catalog.find(i=>i.category==='desk')!,rug=catalog.find(i=>i.category==='rug')!;
const stock=[{id:'desk1',owner_id:'me',item_id:desk.item_id,acquired_at:''},{id:'rug1',owner_id:'me',item_id:rug.item_id,acquired_at:''}];
const placement:FurniturePlacement={instance_id:'desk1',grid_x:2,grid_y:5,rotation:90};
test('rotated footprint updates all occupied grid cells and interaction approach',()=>{
 assert.deepEqual(footprint(desk,placement),[{x:2,y:5},{x:2,y:6}]);
 const map=layoutMap(homeMap,[placement],stock,catalog),collision=new CollisionSystem(map);
 assert(!collision.walkable({x:2,y:5}));assert(!collision.walkable({x:2,y:6}));assert(collision.walkable({x:3,y:5}));
 const route=new InteractionSystem(new PathfindingSystem(collision)).approach({x:6,y:7},map.objects[0]);assert(route?.length);
});
test('placement preview rejects ownership duplicates overlap entry walls and avatar',()=>{
 assert.equal(placementError([placement],stock,catalog,homeMap),'');
 for(const p of [{...placement,grid_x:-1},{...placement,grid_x:10,grid_y:7},{...placement,instance_id:'foreign'}])assert(placementError([p],stock,catalog,homeMap));
 assert(placementError([placement,placement],stock,catalog,homeMap));
 assert(placementError([placement],stock,catalog,homeMap,{x:2,y:6}));
});
test('floor rug is visible while retaining walkable collision',()=>{
 const map=layoutMap(homeMap,[{instance_id:'rug1',grid_x:3,grid_y:5,rotation:0}],stock,catalog),collision=new CollisionSystem(map);
 assert(collision.walkable({x:3,y:5}));assert(collision.walkable({x:4,y:6}));
});
test('client preview rejects disconnected floor',()=>{
 const chairs=Array.from({length:12},(_,i)=>({id:String(i),owner_id:'me',item_id:'furniture_chair_001',acquired_at:''}));
 assert(placementError(chairs.map((c,i)=>({instance_id:c.id,grid_x:i,grid_y:4,rotation:0})),chairs,catalog,homeMap).includes('통로'));
});

import {GestureSystem} from './GestureSystem';
import {screenToWorld,worldToScreen,zoomAt,boundScroll,type CameraView} from './CameraSystem';
import {layoutLabels,overlaps} from './BubbleLayoutSystem';
import {formatKoreanTime,auditSummary} from '../../services/adminPresentation';
test('tap, drag, pinch and reset keep camera gestures separate from walking',()=>{
 const g=new GestureSystem();g.down(1,{x:10,y:10});assert(g.up(1,{x:12,y:13}));
 g.down(1,{x:10,y:10});assert.equal(g.move(1,{x:30,y:10})?.kind,'pan');assert(!g.up(1,{x:30,y:10}));
 g.down(1,{x:20,y:20});g.down(2,{x:40,y:20});const pinch=g.move(2,{x:60,y:20});assert(pinch?.kind==='pinch'&&pinch.scale===2);assert(!g.up(2,{x:60,y:20}));assert(!g.up(1,{x:20,y:20}));
 g.down(1,{x:0,y:0});g.reset();assert(!g.up(1,{x:0,y:0}));g.down(1,{x:0,y:0});assert(g.up(1,{x:0,y:0}));
});
test('screen world round trip and anchored zoom work with scroll viewport and zoom',()=>{
 const bounds={x:-1000,y:-1000,width:5000,height:5000};
 for(const zoom of [.4,1,1.8]){const c:CameraView={x:12,y:30,width:700,height:600,scrollX:140,scrollY:250,zoom},point={x:230,y:190},world=screenToWorld(point,c),screen=worldToScreen(world,c);assert(Math.hypot(screen.x-point.x,screen.y-point.y)<1e-9);const next=zoomAt(c,bounds,1.2,point),anchor=screenToWorld(point,next);assert(Math.hypot(world.x-anchor.x,world.y-anchor.y)<1e-9);}
 const c={x:0,y:0,width:600,height:400,scrollX:-10000,scrollY:10000,zoom:1},b={x:0,y:0,width:1000,height:800};assert.deepEqual(boundScroll(c,b),{x:0,y:400});assert.equal(zoomAt(c,b,99,{x:0,y:0}).zoom,1.8);
});
test('dense bubble labels stay within canvas without overlaps or unsafe HTML handling',()=>{
 const view={x:8,y:8,width:374,height:500},labels=Array.from({length:35},(_,i)=>({id:String(i),x:i%2?350:-20,y:20,width:150,height:30,priority:i}));const result=layoutLabels(labels,view),visible=result.filter(v=>v.visible);assert(visible.length>5);for(let i=0;i<visible.length;i++){const a=visible[i];assert(a.x>=view.x&&a.y>=view.y&&a.x+a.width<=view.x+view.width&&a.y+a.height<=view.y+view.height);for(const b of visible.slice(i+1))assert(!overlaps(a,b));}assert(result.some(v=>!v.visible));
});
test('audit presentation shows named actor and KST while retaining UTC input',()=>{
 assert.match(formatKoreanTime('2026-11-06 00:00:00'),/9:00:00/);assert.equal(formatKoreanTime('bad'),'알 수 없는 시각');assert.match(auditSummary({action:'role_changed',actor_name:'관리자',target_name:'나래',details:'{"before":"user","after":"moderator"}'}),/나래님의 권한을 user → moderator/);
});

test('camera adapter preserves inherited Phaser accessor dimensions during zoom',()=>{
 class Camera {get x(){return 0;}get y(){return 0;}get width(){return 700;}get height(){return 600;}get scrollX(){return 140;}get scrollY(){return 250;}get zoom(){return 1;}}
 const c=new Camera(),p={x:250,y:250},next=zoomAt(c,{x:-1000,y:-1000,width:5000,height:5000},1.2,p);assert(Number.isFinite(next.scrollX)&&Number.isFinite(next.scrollY));const a=screenToWorld(p,next),b=screenToWorld(p,c);assert(Math.hypot(a.x-b.x,a.y-b.y)<1e-9);
});

import {GameSession} from '../../games/core/GameSession';
import type {GameState} from '../../games/core/GameResult';
import {WhackAMoleGame} from '../../games/whack-a-mole/WhackAMoleGame';
test('arcade out-of-order poll responses cannot restore consumed targets or completed sessions',()=>{
 const api=new GameSession('test'),base={session_id:'game',server_now:10,status:'active',score:10} as GameState;api.accept(base);assert.equal(api.accept({...base,server_now:9,score:0}).score,10);api.accept({...base,status:'completed',server_now:11});assert.equal(api.accept({...base,server_now:12}).status,'completed');assert.equal(api.accept({...base,session_id:'new-game',server_now:12}).status,'active');
});
test('arcade timer uses monotonic elapsed time and one pointer action at a time',()=>{
 const game=new WhackAMoleGame();game.sync(30000,100);assert.equal(game.remaining(10100),20000);assert.equal(game.remaining(50000),0);assert(game.allowInput(1000));assert(!game.allowInput(1001));assert(game.allowInput(1100));
});
