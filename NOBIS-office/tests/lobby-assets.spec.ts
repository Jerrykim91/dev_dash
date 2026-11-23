import {test,expect,type Page} from '../frontend/node_modules/@playwright/test';
import {clickObject,enterRoom,roomType} from './room-fixture';
async function join(p:Page,name:string){await p.goto('/');await p.getByLabel('개발용 닉네임',{exact:true}).fill(name);await p.getByRole('button',{name:/오피스 입장하기/}).click();await expect(p.locator('.connection')).toContainText('접속');await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);}
async function walk(p:Page){await p.bringToFront();const t={x:17,y:14};const point=await p.evaluate(t=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),w=s.coords.toWorld(t),c=s.cameras.main,v=c.getWorldPoint(0,0),r=s.game.canvas.getBoundingClientRect();return{x:r.left+(w.x-v.x)*c.zoom,y:r.top+(w.y-v.y)*c.zoom};},t);await p.mouse.click(point.x,point.y);await expect.poll(()=>p.evaluate(t=>{const s=(window as any).__NOBIS_GAME__.registry.get('world');return Math.hypot(s.movement.position.x-t.x,s.movement.position.y-t.y);},t),{timeout:10000}).toBeLessThan(.05);}

test('lobby layers, real floor click, other avatar synchronization and original cafe portals',async({browser})=>{
 const c=await browser.newContext({viewport:{width:1440,height:1000}}),a=await c.newPage(),b=await c.newPage(),errors:string[]=[];for(const p of[a,b])p.on('pageerror',e=>errors.push(e.message));await join(a,'로비아트A');await join(b,'로비아트B');
 const art=await a.evaluate(()=>{const g=(window as any).__NOBIS_GAME__,s=g.registry.get('world');return{floor:s.children.list.filter((o:any)=>/^floor\/floor_(stone|wood)$/.test(o.frame?.name??'')).length,walls:g.registry.get('wall-visuals'),door:s.objectSprites.get('portal-cafe').lower.texture.key,doorFrame:s.objectSprites.get('portal-cafe').lower.frame.name,queue:g.registry.get('visual-metrics').queuedAtlases};});expect(art.floor).toBe(607);// 뒤쪽 두 벽은 새 벽 그림, 입구는 벽에 붙는 문(docs/visual-standard-v2.md §13)
 expect(art.walls.segments).toBeGreaterThan(40);expect(art.door).toBe('nobis-avatar-0');expect(art.doorFrame).toBe('door/cafe/y');expect(art.queue).toBe(5);
 await walk(a);await expect.poll(()=>b.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world');return s.model.players.find((p:any)=>p.nickname==='로비아트A')?.x;})).toBeCloseTo(17,1);
 await a.getByRole('button',{name:'월드 전체 보기',exact:true}).click();await a.screenshot({path:'../docs/phase7b-lobby-overview.png',animations:'disabled'});await a.getByRole('button',{name:'캐릭터 추적',exact:true}).click();await a.screenshot({path:'../docs/phase7b-lobby-detail.png',animations:'disabled'});
 await enterRoom(a,'cafe');await enterRoom(a,'lobby');expect(await roomType(a)).toBe('lobby');expect(errors).toEqual([]);await c.close();
});

test('missing lobby atlases keep original floor and interactive door fallbacks',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await page.route('**/assets/world/lobby/**/*.png',r=>r.abort());await join(page,'로비리소스대체');
 expect(await page.evaluate(()=>(window as any).__NOBIS_GAME__.registry.get('visual-metrics').failures)).toContain('nobis-lobby-tiles');await walk(page);await page.getByRole('button',{name:'월드 전체 보기',exact:true}).click();await page.screenshot({path:'../docs/phase7b-lobby-fallback.png',animations:'disabled'});await clickObject(page,'portal-cafe');await expect.poll(()=>roomType(page),{timeout:30000}).toBe('cafe');expect(errors).toEqual([]);
});
