import {enterRoom,clickObject} from './room-fixture';
import {resolvePoint} from './world-fixture';
import {test,expect,type Page} from '../frontend/node_modules/@playwright/test';
const suffix=()=>String(Date.now()).slice(-7);
async function ready(p:Page){await expect(p.locator('.connection')).toContainText('접속');await expect.poll(()=>p.evaluate(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement)).toBe(true);}
async function join(p:Page,name:string,admin=false){await p.goto('/');await p.getByLabel('개발용 닉네임',{exact:true}).fill(name);if(admin){await p.getByText('운영자 테스트 계정',{exact:true}).click();await p.getByLabel('개발용 운영자 키').fill('e2e-only-key');}await p.getByRole('button',{name:'오피스 입장하기'}).click();await ready(p);}
async function own(p:Page){return p.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world');return s?.model.players.find((v:any)=>v.id===s.model.session.user.id)??{};});}
async function clickWorld(p:Page,x:number,y:number,offset=0){({x,y}=await resolvePoint(p,x,y,offset));await p.getByRole('button',{name:'월드 전체 보기',exact:true}).click();await p.evaluate(()=>new Promise<void>(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r()))));const point=await p.evaluate(({x,y,offset})=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),c=s.cameras.main,w=s.coords.toWorld({x,y}),o=c.getWorldPoint(0,0),r=s.game.canvas.getBoundingClientRect();return {x:r.left+(w.x-o.x)*c.zoom,y:r.top+(w.y+offset-o.y)*c.zoom};},{x,y,offset});await p.mouse.click(point.x,point.y);}
async function at(p:Page,x:number,y:number){({x,y}=await resolvePoint(p,x,y,0));await expect.poll(async()=>{const u=await own(p);return Math.hypot(u.x-x,u.y-y);},{timeout:45000}).toBeLessThan(.08);}
async function say(p:Page,text:string){await p.getByLabel('채팅 메시지',{exact:true}).fill(text);await p.getByRole('button',{name:'채팅 보내기'}).click();}
async function api(p:Page,url:string){return p.evaluate(async url=>{const token=(window as any).__NOBIS_GAME__.registry.get('world').model.session.token,r=await fetch(url,{headers:{Authorization:`Bearer ${token}`}});return {status:r.status,body:await r.json()};},url);}
async function invite(host:Page,name:string){const panel=host.locator('.private-channel details');if(await panel.getAttribute('open')===null)await panel.locator('summary').click();await host.getByLabel('초대할 사용자').selectOption({label:name});await host.getByRole('button',{name:'초대',exact:true}).click();}
async function accept(p:Page){await p.getByRole('button',{name:/^대화방/}).click();await p.getByRole('dialog',{name:'대화방 관리'}).getByRole('button',{name:'초대 수락',exact:true}).click();}
async function details(p:Page){const panel=p.locator('.private-channel details');if(await panel.getAttribute('open')===null)await panel.locator('summary').click();}

test('three browsers: invitation ACL, private cafe, room retention, meeting archive and admin notice',async({browser})=>{
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),a=await context.newPage(),b=await context.newPage(),c=await context.newPage();
 const id=suffix(),guest=`참여자${id}`,secret=`초대 전 비밀-${id}`,reply=`승인 후 대화-${id}`;const frames:string[]=[],errors:string[]=[];let roomId='',bSockets=0;
 for(const p of [a,b,c])p.on('pageerror',e=>errors.push(e.message));
 a.on('websocket',ws=>ws.on('framereceived',e=>{const m=JSON.parse(String(e.payload));if(m.type==='channel_created')roomId=m.channel_id;}));
 b.on('websocket',ws=>{if(new URL(ws.url()).pathname==='/ws')bSockets++;});c.on('websocket',ws=>ws.on('framereceived',e=>frames.push(String(e.payload))));
 await join(a,`주최자${id}`);await join(b,guest);await join(c,`운영자${id}`,true);await expect(a.locator('.connection')).toContainText('3 / 15');
 await clickWorld(a,18,8);await at(a,18,8);await clickWorld(a,16,9,-25);await expect(a.getByRole('dialog',{name:'대화방 관리'})).toBeVisible({timeout:10000});await a.getByLabel('대화 이름').fill(`비공개 카페 ${id}`);await a.getByRole('button',{name:'대화 만들기',exact:true}).click();await expect(a.locator('.private-channel')).toContainText(`비공개 카페 ${id}`);
 await say(a,secret);await expect(a.getByRole('log')).toContainText(secret);await expect(b.getByRole('log')).not.toContainText(secret);await expect(c.getByRole('log')).not.toContainText(secret);
 expect((await api(c,`/api/channels/${roomId}/messages`)).status).toBe(403);await invite(a,guest);
 await b.getByRole('button',{name:/^대화방/}).click();await expect(b.getByRole('dialog',{name:'대화방 관리'})).toContainText('초대 대기');expect((await api(b,`/api/channels/${roomId}/messages`)).status).toBe(403);
 await b.getByRole('dialog').getByRole('button',{name:'초대 수락',exact:true}).click();await expect(b.locator('.private-channel')).toContainText(`비공개 카페 ${id}`);await expect(b.getByRole('log')).toContainText(secret);await say(b,reply);await expect(a.getByRole('log')).toContainText(reply);await expect(a.getByRole('log')).not.toContainText('undefined');
 const socketCount=bSockets;await b.getByRole('button',{name:'채팅 전용 모드',exact:true}).click();await expect(b.locator('canvas')).not.toBeVisible();await say(a,`연결 유지-${id}`);await expect(b.getByRole('log')).toContainText(`연결 유지-${id}`);await expect(b.locator('.private-channel')).toContainText(`비공개 카페 ${id}`);expect(bSockets).toBe(socketCount);
 await b.getByRole('button',{name:'전체 모드로 돌아가기'}).click();await details(b);await b.getByRole('button',{name:'대화 나가기',exact:true}).click();await expect(b.locator('.private-channel')).toHaveCount(0);expect((await api(b,`/api/channels/${roomId}/messages`)).status).toBe(403);
 expect(frames.some(f=>f.includes(secret)||f.includes(reply))).toBe(false);
 await enterRoom(a,'lobby');await clickObject(a,'portal-meeting');await expect(a.getByRole('dialog',{name:'회의실 목록'})).toBeVisible({timeout:30000});await a.getByRole('button',{name:'닫기',exact:true}).click();await a.getByRole('button',{name:/^대화방/}).click();await a.getByLabel('대화 종류').selectOption('meeting');await a.getByLabel('대화 이름').fill(`참석 회의 ${id}`);await a.getByRole('button',{name:'대화 만들기',exact:true}).click();await expect(a.locator('.private-channel')).toContainText(`참석 회의 ${id}`);const meetingId=roomId;
 await invite(a,guest);await accept(b);await say(a,`회의 기록-${id}`);await expect(b.getByRole('log')).toContainText(`회의 기록-${id}`);await details(a);await a.getByRole('button',{name:'회의 종료',exact:true}).click();await expect(b.locator('.private-channel')).toContainText('종료');await expect(b.getByLabel('채팅 메시지',{exact:true})).toBeDisabled();expect((await api(b,`/api/channels/${meetingId}/messages`)).status).toBe(200);expect((await api(c,`/api/channels/${meetingId}/messages`)).status).toBe(403);
 await c.evaluate(async text=>{const token=(window as any).__NOBIS_GAME__.registry.get('world').model.session.token;const r=await fetch('/api/admin/announcements',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({title:'운영 공지',text})});if(!r.ok)throw Error('공지 발송 실패');},`운영 공지-${id}`);await expect(a.locator('.world-announcement-toast')).toContainText(`운영 공지-${id}`);await expect(b.locator('.world-announcement-toast')).toContainText(`운영 공지-${id}`);
 await a.screenshot({path:'../docs/phase2-meeting.png'});expect(errors).toEqual([]);await context.close();
});

test('toggle interactions, bookshelf animation, private room, real DevNest popup and preserved return',async({browser})=>{
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),a=await context.newPage(),b=await context.newPage();const id=suffix(),errors:string[]=[],effects:string[]=[];
 for(const p of [a,b])p.on('pageerror',e=>errors.push(e.message));b.on('websocket',ws=>ws.on('framereceived',e=>{const m=JSON.parse(String(e.payload));if(m.type==='object_effect')effects.push(m.object_id);}));
 await join(a,`개인실${id}`);await join(b,`동료${id}`);
 await clickWorld(a,6,5,-35);await expect.poll(async()=>(await own(a)).action,{timeout:30000}).toBe('sitting');await clickWorld(a,6,5,-35);await expect.poll(async()=>(await own(a)).action).toBe('idle');
 await clickWorld(a,3,3,-45);await expect.poll(async()=>(await own(a)).action,{timeout:30000}).toBe('working');await clickWorld(a,3,3,-45);await expect.poll(async()=>(await own(a)).action).toBe('idle');
 await clickWorld(a,16,4,-40);await expect.poll(async()=>(await own(a)).action,{timeout:30000}).toBe('drinking');await expect.poll(async()=>(await own(a)).status_text).toBe('커피 마시는 중');
 await clickWorld(a,28,4,-35);await expect.poll(async()=>(await own(a)).action,{timeout:30000}).toBe('resting');
 await enterRoom(a,'lobby');await clickObject(a,'bookshelf');await expect(a.getByRole('dialog',{name:'개인 집 입구'})).toBeVisible({timeout:30000});const officePosition=await own(a);
 await a.getByRole('button',{name:'내 방 · 작업실 입장 →',exact:true}).click();await expect.poll(async()=>(await own(a)).scope).toContain('personal:');await ready(a);expect(await a.evaluate(()=>(window as any).__NOBIS_GAME__.registry.get('world').avatars.size)).toBe(1);
 await a.getByRole('button',{name:'설정 열기',exact:true}).click();await a.getByLabel('개인 공간 이름').fill(`저장된 작업실 ${id}`);await a.getByLabel('DevNest 외부 URL').fill('http://127.0.0.1:18003/');await a.getByRole('button',{name:'연결 주소 저장'}).click();await expect(a.getByRole('dialog')).toHaveCount(0);await a.reload();await ready(a);await expect(a.locator('.location-label')).toContainText(`저장된 작업실 ${id}`);
 await clickWorld(a,3,3,-45);await expect(a.getByRole('dialog',{name:'DevNest 개인 대시보드'})).toBeVisible({timeout:10000});const before=await own(a);
 const popupPromise=context.waitForEvent('page');await a.getByRole('link',{name:'DevNest 새 탭에서 열기'}).click();const popup=await popupPromise;await expect(popup).toHaveTitle(/DevNest/);await popup.close();await a.getByRole('button',{name:'작업실로 돌아가기',exact:true}).click();await at(a,before.x,before.y);expect((await own(a)).scope).toBe(before.scope);expect((await own(a)).work_status).toBe(before.work_status);
 await a.screenshot({path:'../docs/phase2-personal-room.png'});
 await a.getByRole('button',{name:'로비로 돌아가기',exact:true}).click();await expect.poll(async()=>(await own(a)).scope).toBe('office');await at(a,officePosition.x,officePosition.y);expect(errors).toEqual([]);await context.close();
});
