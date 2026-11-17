import {spawn} from './world-fixture';
import {test,expect,type Page} from '../frontend/node_modules/@playwright/test';
async function join(p:Page,name:string){await p.goto('/');await p.getByLabel('개발용 닉네임',{exact:true}).fill(name);await p.getByRole('button',{name:'오피스 입장하기'}).click();await expect(p.locator('.connection')).toContainText('접속');await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);}
async function snapshot(p:Page){return p.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),c=s.cameras.main;return {x:s.movement.position.x,y:s.movement.position.y,scrollX:c.scrollX,scrollY:c.scrollY,zoom:c.zoom};});}
async function viewport(p:Page){return p.locator('canvas').boundingBox();}
test('desktop sidebar persistence, camera drag wheel and zoomed floor click',async({page})=>{
 await join(page,'카메라검증');await expect(page.getByLabel('구역까지 걸어가기')).toHaveCount(0);
 expect(await page.locator('.sidebar').evaluate(e=>e.getBoundingClientRect().width)).toBe(64);
 await page.getByRole('button',{name:'사이드바 펼치기'}).click();await page.reload();await expect(page.locator('.connection')).toContainText('접속');await page.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);await expect(page.getByRole('button',{name:'사이드바 접기'})).toBeVisible();await page.getByRole('button',{name:'사이드바 접기'}).click();
 await page.getByRole('button',{name:'월드 전체 보기',exact:true}).click();const old=await snapshot(page),r=(await viewport(page))!;
 await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.mouse.wheel(0,-300);await expect.poll(async()=>(await snapshot(page)).zoom).toBeGreaterThan(old.zoom);
 const zoomed=await snapshot(page);await page.mouse.move(r.x+r.width*.5,r.y+r.height*.5);await page.mouse.down();await page.mouse.move(r.x+r.width*.6,r.y+r.height*.6,{steps:8});await page.mouse.up();const dragged=await snapshot(page);expect(Number.isFinite(dragged.scrollX)&&Number.isFinite(dragged.scrollY)).toBe(true);expect(dragged.x).toBe(old.x);expect(dragged.y).toBe(old.y);expect(dragged.scrollX).not.toBe(zoomed.scrollX);
 await page.getByRole('button',{name:'캐릭터 추적',exact:true}).click();await page.waitForTimeout(150);const target=await page.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),c=s.cameras.main,w=s.coords.toWorld({x:s.map.spawn.x,y:s.map.spawn.y-1}),o=c.getWorldPoint(0,0),r=s.game.canvas.getBoundingClientRect();return{x:r.left+(w.x-o.x)*c.zoom,y:r.top+(w.y-o.y)*c.zoom};});await page.mouse.click(target.x,target.y);await expect.poll(async()=>{const p=await snapshot(page);return Math.hypot(p.x-spawn.x,p.y-(spawn.y-1));}).toBeLessThan(.05);
 await page.screenshot({path:'../docs/phase35-desktop.png'});
});
test('mobile viewport, pinch and pan do not move avatar; chat mode preserves scene',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true}),page=await context.newPage();await join(page,'터치검증');
 expect(await page.evaluate(()=>({w:document.documentElement.scrollWidth<=innerWidth,h:document.documentElement.scrollHeight<=innerHeight+1}))).toEqual({w:true,h:true});const r=(await viewport(page))!;expect(r.height).toBeGreaterThan(550);
 const cdp=await context.newCDPSession(page),old=await snapshot(page),cx=r.x+r.width/2,cy=r.y+r.height/2;
 const touch=(id:number,x:number,y:number)=>({id,x,y,radiusX:3,radiusY:3});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touch(1,cx-30,cy),touch(2,cx+30,cy)]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[touch(1,cx-65,cy),touch(2,cx+65,cy)]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await expect.poll(async()=>(await snapshot(page)).zoom).toBeGreaterThan(old.zoom);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[touch(1,cx,cy)]});await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[touch(1,cx+50,cy+50)]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});const after=await snapshot(page);expect(Number.isFinite(after.scrollX)&&Number.isFinite(after.scrollY)).toBe(true);expect(after.x).toBe(old.x);expect(after.y).toBe(old.y);
 await page.screenshot({path:'../docs/phase35-mobile-world.png'});await page.getByRole('tab',{name:'채팅 전용 모드',exact:true}).click();await expect(page.locator('canvas')).not.toBeVisible();await expect(page.getByLabel('채팅 메시지',{exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);await page.screenshot({path:'../docs/phase35-mobile-chat.png'});
 await page.getByRole('tab',{name:'전체 모드로 돌아가기',exact:true}).click();expect((await snapshot(page)).x).toBe(old.x);expect((await snapshot(page)).y).toBe(old.y);await context.close();
});
test('DevNest blocked popup exposes retry and settings guidance',async({page})=>{
 await join(page,'연결검증');await page.getByRole('button',{name:'작업실 · 대시보드',exact:true}).click();await page.evaluate(()=>{window.open=()=>null;});await page.getByRole('link',{name:'DevNest 새 탭에서 열기'}).click();await expect(page.getByRole('alert')).toContainText('팝업');await page.getByText('대시보드가 열리지 않나요?',{exact:true}).click();await expect(page.getByRole('button',{name:'연결 주소 설정'})).toBeVisible();
});
