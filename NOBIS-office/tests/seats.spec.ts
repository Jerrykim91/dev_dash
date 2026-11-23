import {test,expect,type Page} from '../frontend/node_modules/@playwright/test';
import {enterRoom,clickObject} from './room-fixture';

// 엔진 1단계(좌석) + 스타일 보드 v2 실제 화면 검증. docs/visual-standard-v2.md §7.4 1단계 완료 기준.
async function join(p:Page,name:string){await p.goto('/');await p.getByLabel('개발용 닉네임',{exact:true}).fill(name);await p.getByRole('button',{name:/오피스 입장하기/}).click();await expect(p.locator('.connection')).toContainText('접속');await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);}
const me=(p:Page)=>p.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),pl=s.model.players.find((x:any)=>x.id===s.model.session.user.id);return{seat:pl?.seat_id??null,x:pl?.x,y:pl?.y,dir:pl?.direction,action:pl?.action,local:{...s.movement.position}};});
const depths=(p:Page,objectId:string)=>p.evaluate(id=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),art=s.objectSprites.get(id),a=s.avatars.get(s.model.session.user.id);return{lower:art.depth,upper:art.upper?.depth??null,avatar:a.container.depth,source:art.getData('visual-source')};},objectId);
async function focusCamera(p:Page,tile:{x:number;y:number},zoom=2){await p.evaluate(({tile,zoom})=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),w=s.coords.toWorld(tile),c=s.cameras.main;s.cameraMode='explore';c.stopFollow();c.setZoom(zoom);c.centerOn(w.x,w.y-20);},{tile,zoom});await p.waitForTimeout(400);}
// 화면 클릭은 앉아 있는 사람(프로필)이 가로챌 수 있으므로, 점유 검증은 게임의 상호작용 경로를 직접 호출한다
const use=(p:Page,id:string)=>p.evaluate(id=>{const s=(window as any).__NOBIS_GAME__.registry.get('world');s.approach(s.map.objects.find((o:any)=>o.id===id));},id);
async function clickTile(p:Page,tile:{x:number;y:number}){const pt=await p.evaluate(t=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),w=s.coords.toWorld(t),c=s.cameras.main,v=c.getWorldPoint(0,0),r=s.game.canvas.getBoundingClientRect();return{x:r.left+(w.x-v.x)*c.zoom,y:r.top+(w.y-v.y)*c.zoom};},tile);await p.mouse.click(pt.x,pt.y);}

test('focus desk click seats the user on the linked chair, blocks a second user, and stands up to the approach tile',async({browser})=>{
 const ca=await browser.newContext(),a=await ca.newPage(),cb=await browser.newContext(),b=await cb.newPage();
 await join(a,'좌석A');await enterRoom(a,'focus');
 await clickObject(a,'desk-0');
 await expect.poll(()=>me(a).then(m=>m.seat),{timeout:45000}).toBe('chair#0');
 const seated=await me(a);expect([seated.x,seated.y,seated.dir,seated.action]).toEqual([5,5,'north','working']);
 const d=await depths(a,'chair');expect(d.source).toBe('atlas');expect(d.lower).toBeLessThan(d.avatar);expect(d.avatar).toBeLessThan(d.upper);
 await focusCamera(a,{x:5,y:5});await a.screenshot({path:'../docs/seat-demo-workstation.png',animations:'disabled'});
 await join(b,'좌석B');await enterRoom(b,'focus');await use(b,'chair');
 // B는 진입 칸(5,6)까지 걸어가지만 서버가 점유 중이라 거절 → 앉지 못함
 await expect.poll(()=>me(b).then(m=>Math.hypot(m.local.x-5,m.local.y-6)),{timeout:45000}).toBeLessThan(.2);
 await b.waitForTimeout(1500);expect((await me(b)).seat).toBeNull();
 await clickTile(a,{x:8,y:8});
 await expect.poll(()=>me(a).then(m=>m.seat),{timeout:15000}).toBeNull();
 await expect.poll(()=>me(a).then(m=>Math.hypot(m.local.x-8,m.local.y-8)),{timeout:30000}).toBeLessThan(.2);
 await use(b,'chair');await expect.poll(()=>me(b).then(m=>m.seat),{timeout:45000}).toBe('chair#0');
 await ca.close();await cb.close();
});

test('demo: several users at focus workstations and on lobby sofas with style board v2 art',async({browser})=>{
 const roomOf=(p:Page)=>p.evaluate(()=>(window as any).__NOBIS_GAME__?.registry.get('world')?.map?.room_type??'loading');
 const enter=async(p:Page,type:string)=>{await use(p,'portal-'+type);await expect.poll(()=>roomOf(p),{timeout:60000}).toBe(type);await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);};
 const ctx:Awaited<ReturnType<typeof browser.newContext>>[]=[];const pages:Page[]=[];
 for(const [i,name] of ['데모1','데모2','데모3','데모4'].entries()){const c=await browser.newContext();ctx.push(c);const p=await c.newPage();pages.push(p);await join(p,name);await enter(p,'focus');await use(p,['desk-0','desk-1','desk-2','desk-3'][i]);}
 for(const p of pages)await expect.poll(()=>me(p).then(m=>m.seat),{timeout:60000}).not.toBeNull();
 await focusCamera(pages[0],{x:6,y:9},2);await pages[0].screenshot({path:'../docs/seat-demo-focus.png',animations:'disabled'});
 const c=await browser.newContext();ctx.push(c);const l=await c.newPage();await join(l,'소파데모');await use(l,'lobby-sofa-west');
 await expect.poll(()=>me(l).then(m=>m.seat),{timeout:60000}).toMatch(/^lobby-sofa-west#/);
 const c2=await browser.newContext();ctx.push(c2);const l2=await c2.newPage();await join(l2,'소파데모2');await use(l2,'lobby-sofa-west');
 await expect.poll(()=>me(l2).then(m=>m.seat),{timeout:60000}).toMatch(/^lobby-sofa-west#/);expect((await me(l2)).seat).not.toBe((await me(l)).seat);
 // 2칸 소파의 두 자리 모두: 소파 몸통 < 앉은 캐릭터 < 등받이 (자리별 깊이가 아니라 가구 정렬 기준)
 await expect.poll(()=>l.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),art=s.objectSprites.get('lobby-sofa-west');return s.model.players.filter((p:any)=>p.seat_id?.startsWith('lobby-sofa-west#')).map((p:any)=>{const d=s.avatars.get(p.id)?.container.depth;return art.depth<d&&(art.upper?d<art.upper.depth:true);});}),{timeout:15000}).toEqual([true,true]);
 const s=await me(l);await focusCamera(l,{x:s.x,y:s.y},2);await l.screenshot({path:'../docs/seat-demo-lobby-sofa.png',animations:'disabled'});
 for(const x of ctx)await x.close();
});
