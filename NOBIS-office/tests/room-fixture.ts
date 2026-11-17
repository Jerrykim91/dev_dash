import {expect,type Page} from '../frontend/node_modules/@playwright/test';
export async function roomType(p:Page){return p.evaluate(()=>(window as any).__NOBIS_GAME__?.registry.get('world')?.map?.room_type??'loading');}
export async function clickObject(p:Page,id:string){
 await p.bringToFront();await p.getByRole('button',{name:'월드 전체 보기',exact:true}).click();await p.evaluate(()=>new Promise<void>(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r()))));
 const point=await p.evaluate(id=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),o=s.map.objects.find((o:any)=>o.id===id);if(!o)throw Error('missing object '+id);const w=s.coords.toWorld(o),c=s.cameras.main,v=c.getWorldPoint(0,0),r=s.game.canvas.getBoundingClientRect();return{x:r.left+(w.x-v.x)*c.zoom,y:r.top+(w.y-v.y-32)*c.zoom};},id);await p.mouse.click(point.x,point.y);
}
export async function enterRoom(p:Page,type:string){
 if(await roomType(p)===type)return;
 if(await roomType(p)!=='lobby'){await clickObject(p,'room-exit');await expect.poll(()=>roomType(p),{timeout:45000}).toBe('lobby');}
 if(type==='lobby')return;
 await clickObject(p,'portal-'+type);await expect.poll(()=>roomType(p),{timeout:45000}).toBe(type);
 await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);
}
