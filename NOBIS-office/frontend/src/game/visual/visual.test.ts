import {lobbyManifest,lobbyFrame,lobbyFloor} from './LobbyCatalog';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {manifest,characterVariant,characterState,characterFrame,furnitureFrames} from './catalog';
import catalog from '../../../../shared/furniture-catalog.json';
import maps from '../../../../shared/maps.json';
const root=fileURLToPath(new URL('../../../',import.meta.url));
test('atlas PNG and JSON content hashes, dimensions and frame bounds are consistent',()=>{
 let memory=0;
 for(const a of [...manifest.atlases,...lobbyManifest.atlases]){const png=fs.readFileSync(root+'public/'+a.image),json=fs.readFileSync(root+'public/'+a.data),atlas=JSON.parse(json.toString());assert.equal(png.readUInt32BE(16),a.width);assert.equal(png.readUInt32BE(20),a.height);assert.ok(a.width<=2048&&a.height<=2048);assert.ok(a.image.includes(createHash('sha256').update(png).digest('hex').slice(0,12)));assert.ok(a.data.includes(createHash('sha256').update(json).digest('hex').slice(0,12)));memory+=a.width*a.height*4;
  for(const f of Object.values(atlas.frames) as any[]){assert.ok(f.frame.x>=0&&f.frame.y>=0);assert.ok(f.frame.x+f.frame.w<=a.width&&f.frame.y+f.frame.h<=a.height);}
 }
 assert.ok(memory<24*1024*1024);assert.ok(manifest.atlases.length>0);assert.equal(new Set(manifest.atlases.map(a=>a.key)).size,manifest.atlases.length);
});
test('all 16 appearances have four existing directions and complete idle/walk/sit/type clips',()=>{
 for(let v=0;v<16;v++){assert.equal(characterVariant(manifest.avatar.palettes[v],'id'),v);for(const d of manifest.avatar.directions)for(const [state,config]of Object.entries(manifest.avatar.animations))for(let i=0;i<config.frames;i++){const f=characterFrame(v,d,state,i);assert.ok(f);assert.equal(f.rect.w,48);assert.equal(f.rect.h,64);}}
 assert.equal(manifest.avatar.origin.y*manifest.avatar.height,58);assert.equal(characterState(true,'working'),'walking');assert.equal(characterState(false,'working'),'typing');assert.equal(characterState(false,'sitting'),'sitting');assert.equal(characterState(false,'idle'),'idle');
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
