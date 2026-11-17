// Public manifest is the editable source; Vite imports a generated source copy.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),source=path.join(root,'frontend/public/assets/world/lobby/manifest.json'),target=path.join(root,'frontend/src/game/visual/lobby-manifest.generated.json');
const raw=fs.readFileSync(source,'utf8'),manifest=JSON.parse(raw);
if(manifest.map_id!=='room-lobby'||!Array.isArray(manifest.atlases)||!manifest.frames)throw Error('Invalid lobby manifest');
for(const a of manifest.atlases)if(a.width<1||a.height<1||a.width>2048||a.height>2048||!a.image.startsWith('assets/world/lobby/'))throw Error('Invalid lobby atlas '+a.key);
if(!fs.existsSync(target)||fs.readFileSync(target,'utf8')!==raw)fs.writeFileSync(target,raw);
