import Phaser from 'phaser';
import {lobbyManifest} from './LobbyCatalog';
import {manifest,assetUrl,type VisualFrame} from './catalog';
export function preloadVisuals(scene:Phaser.Scene,lobby=false){
 const media=matchMedia('(prefers-reduced-motion: reduce)'),changed=()=>scene.registry.set('visual-reduced-motion',media.matches);changed();media.addEventListener('change',changed);scene.events.once('shutdown',()=>media.removeEventListener('change',changed));
 const atlases=[...manifest.atlases,...(lobby?lobbyManifest.atlases:[])];
 const failures:string[]=[],registered=new Set(atlases.map(a=>a.key));let queued=0;
 const failed=(file:Phaser.Loader.File)=>{if(registered.has(file.key))failures.push(file.key);};scene.load.on('loaderror',failed);
 scene.events.once('shutdown',()=>scene.load.off('loaderror',failed));
 for(const a of atlases){if(a.width>manifest.maxTextureSize||a.height>manifest.maxTextureSize||a.width<1||a.height<1){failures.push(a.key+':dimensions');continue;}if(scene.textures.exists(a.key))continue;scene.load.atlas(a.key,assetUrl(a.image),assetUrl(a.data));queued++;}
 scene.registry.set('visual-metrics',{version:manifest.version,queuedAtlases:queued,failures,declaredPngBytes:atlases.reduce((n,a)=>n+a.bytes,0),decodedTextureBytes:atlases.reduce((n,a)=>n+a.width*a.height*4,0),maxTextureSize:manifest.maxTextureSize});
}
export function frameAvailable(scene:Phaser.Scene,frame:VisualFrame|undefined):frame is VisualFrame{return !!frame&&scene.textures.exists(frame.atlas)&&scene.textures.get(frame.atlas).has(frame.frame);}
