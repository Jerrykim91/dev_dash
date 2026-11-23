import {lobbyManifest,lobbyFrame,lobbyFloor} from './LobbyCatalog';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {manifest,characterVariant,characterState,characterFrame,characterFrameDir,furnitureFrames,frameScale} from './catalog';
import catalog from '../../../../shared/furniture-catalog.json';
import maps from '../../../../shared/maps.json';
const root=fileURLToPath(new URL('../../../',import.meta.url));
test('atlas PNG and JSON content hashes, dimensions and frame bounds are consistent',()=>{
 let memory=0;
 for(const a of [...manifest.atlases,...lobbyManifest.atlases]){const png=fs.readFileSync(root+'public/'+a.image),json=fs.readFileSync(root+'public/'+a.data),atlas=JSON.parse(json.toString());assert.equal(png.readUInt32BE(16),a.width);assert.equal(png.readUInt32BE(20),a.height);assert.ok(a.width<=2048&&a.height<=2048);assert.ok(a.image.includes(createHash('sha256').update(png).digest('hex').slice(0,12)));assert.ok(a.data.includes(createHash('sha256').update(json).digest('hex').slice(0,12)));memory+=a.width*a.height*4;
  for(const f of Object.values(atlas.frames) as any[]){assert.ok(f.frame.x>=0&&f.frame.y>=0);assert.ok(f.frame.x+f.frame.w<=a.width&&f.frame.y+f.frame.h<=a.height);}
 }
 assert.ok(memory<48*1024*1024,`texture memory ${(memory/2**20).toFixed(1)}MB`);assert.ok(manifest.atlases.length>0);assert.equal(new Set(manifest.atlases.map(a=>a.key)).size,manifest.atlases.length);
});
test('all 16 appearances have four directions (south/north drawn, east/west mirrored at runtime) and complete idle/walk/sit/type clips',()=>{
 for(let v=0;v<16;v++){assert.equal(characterVariant(manifest.avatar.palettes[v],'id'),v);for(const d of manifest.avatar.directions)for(const [state,config]of Object.entries(manifest.avatar.animations))for(let i=0;i<config.frames;i++){const r=characterFrameDir(v,d,state,i),f=r.frame;assert.ok(f);if(r.flip)assert.ok(['east','west'].includes(d));assert.equal(f.rect.w*frameScale(f),48);assert.equal(f.rect.h*frameScale(f),64);}}
 assert.equal(manifest.avatar.origin.y*manifest.avatar.height*manifest.avatar.scale,58);assert.equal(characterState(true,'working'),'walking');assert.equal(characterState(false,'working'),'typing');assert.equal(characterState(false,'sitting'),'sitting');assert.equal(characterState(false,'idle'),'idle');
});
test('existing catalog and unchanged world object footprints resolve to lower/upper frames at all four rotations',()=>{
 for(const item of catalog)for(const rotation of [0,90,180,270]){const turned=rotation%180!==0,f=furnitureFrames({kind:item.asset_key,width:turned?item.size.height:item.size.width,height:turned?item.size.width:item.size.height,rotation});assert.ok(f.lower&&f.upper,item.item_id+'/'+rotation);}
 for(const o of maps.office.objects){const f=furnitureFrames(o as any);if((o as any).placeholder)assert.equal(f.lower,undefined);else assert.ok(f.lower&&f.upper,o.id);}
 assert.equal(manifest.furniture.origin.y*manifest.furniture.height,104);
});
test('unknown visual assets resolve as missing for runtime legacy fallback',()=>{assert.equal(furnitureFrames({kind:'unregistered-item'}).lower,undefined);assert.equal(characterFrame(99,'south','idle'),undefined);assert.equal(characterVariant('unknown','same-id'),characterVariant('unknown','same-id'));});
test('all shared UI styles use central tokens instead of literal hex colors',()=>{for(const file of ['style.css','home.css','social.css','phase35.css','social/social.css','games/arcade.css','design/system.css'])assert.equal(/#[\da-f]{3,8}\b/i.test(fs.readFileSync(root+'src/'+file,'utf8')),false,file);});

test('lobby IDs resolve independent asset frames and distinct wood/stone tiles',()=>{for(const key of Object.values(lobbyManifest.objects)){assert(lobbyFrame(key+'/lower'));assert(lobbyFrame(key+'/upper'));}assert.notEqual(lobbyFloor(15,14)?.frame,lobbyFloor(4,8)?.frame);assert.equal(lobbyManifest.pivot.y*160,104);});

test('public lobby manifest and compiled copy stay identical for deployments',()=>{assert.deepEqual(JSON.parse(fs.readFileSync(root+'public/assets/world/lobby/manifest.json','utf8')),lobbyManifest);});
test('every room has back-wall art on both axes and every door can mount on either wall axis',async()=>{
 const {wallTheme,wallFrame,wallDoorFrames}=await import('./WallVisual');
 const rooms=JSON.parse(fs.readFileSync(root+'../shared/rooms.json','utf8'));
 for(const m of Object.values(rooms.maps) as any[]){
  for(const axis of ['x','y'] as const)assert.ok(wallFrame(wallTheme(m),axis),`${m.room_type} wall ${axis}`);
  for(const o of m.objects.filter((o:any)=>o.kind==='door'))for(const axis of ['x','y'] as const){const f=wallDoorFrames({...o,wall_axis:axis});assert.ok(f?.lower&&f.upper,`${m.room_type} ${o.id} ${axis}`);}
 }
});
test('HD atlases draw at their density so every frame keeps its world size',()=>{
 for(const a of manifest.atlases as {key:string;scale?:number}[])if(a.key.startsWith('nobis-aigen')||a.key==='nobis-avatar-0')assert.equal(a.scale,.5);
 const sofa=furnitureFrames({kind:'sofa',width:2,height:1,rotation:0});assert.equal(sofa.lower.rect.w*frameScale(sofa.lower),128);assert.equal(sofa.lower.rect.h*frameScale(sofa.lower),160);
 // 잘린 프레임은 내용 상자가 원래 프레임 안에 있어야 한다(미리보기 잘라내기)
 for(const f of Object.values(manifest.frames) as {rect:{w:number;h:number};trim?:{x:number;y:number;w:number;h:number}}[])if(f.trim){assert.ok(f.trim.x>=0&&f.trim.y>=0&&f.trim.x+f.trim.w<=f.rect.w&&f.trim.y+f.trim.h<=f.rect.h);}
});
test('wardrobe parts: every hair/top/bottom has frames for every state and direction, and a head anchor per frame',async()=>{
 const {partsManifest,partFrame}=await import('./catalog');const m=partsManifest!;assert.ok(m);
 const shared=JSON.parse(fs.readFileSync(root+'../shared/avatar-parts.json','utf8'));
 assert.deepEqual(shared.hair.map((o:any)=>o.id),m.hair);assert.deepEqual(shared.top.map((o:any)=>o.id),m.tops);assert.deepEqual(shared.bottom.map((o:any)=>o.id),m.bottoms);
 for(const state of ['idle','walking','sitting','typing'])assert.ok(m.states[state]?.length,state);
 for(const d of ['south','north']){
  for(const k of Object.values(m.states).flat()){assert.ok(partFrame(`base/${d}/${k}`));for(const t of m.tops)assert.ok(partFrame(`top/${t}/${d}/${k}`));for(const b of m.bottoms)assert.ok(partFrame(`bottom/${b}/${d}/${k}`));}
  for(const h of m.hair){assert.ok(partFrame(`hair/${h}/${d}`));assert.equal(m.anchors[d][h].length,10);for(const [x,y] of m.anchors[d][h])assert.ok(x>0&&x<96&&y>0&&y<128);}
 }
 assert.equal(partFrame('base/south/0')!.rect.w*frameScale(partFrame('base/south/0')),48);
});
