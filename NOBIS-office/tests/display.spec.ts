import {test,expect,type Page} from '../frontend/node_modules/@playwright/test';

// HiDPI·4K 렌더링 (docs/visual-standard-v2.md §12): 장치 픽셀 캔버스, 픽셀 정렬 카메라 배율, 장치 해상도 글자, 입력 좌표 환산.
async function join(p:Page,name:string){await p.goto('/');await p.getByLabel('개발용 닉네임',{exact:true}).fill(name);await p.getByRole('button',{name:/오피스 입장하기/}).click();await expect(p.locator('.connection')).toContainText('접속');await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);}
const info=(p:Page)=>p.evaluate(()=>{const g=(window as any).__NOBIS_GAME__,s=g.registry.get('world'),r=g.canvas.getBoundingClientRect(),a=s.avatars.get(s.model.session.user.id);return{dpr:devicePixelRatio,buffer:g.canvas.width,css:r.width,zoom:s.cameras.main.zoom,label:a.name.style.resolution,pos:{...s.movement.position}};});
// 월드 → CSS 클라이언트 좌표: 게임(장치) 픽셀을 캔버스 표시 배율로 나눈다
async function clickTile(p:Page,tile:{x:number;y:number}){const pt=await p.evaluate(t=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),w=s.coords.toWorld(t),c=s.cameras.main,v=c.getWorldPoint(0,0),r=s.game.canvas.getBoundingClientRect(),k=r.width/s.game.canvas.width;return{x:r.left+(w.x-v.x)*c.zoom*k,y:r.top+(w.y-v.y)*c.zoom*k};},tile);await p.mouse.click(pt.x,pt.y);}
const pixelAligned=(z:number)=>Number.isInteger(z)||Number.isInteger(1/z);

for(const dpr of [1,2]){
 test(`HiDPI ${dpr}x at 1920x1080: device-pixel canvas, pixel-aligned zoom, crisp labels and correct input`,async({browser})=>{
  const c=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:dpr}),p=await c.newPage();
  await join(p,`해상도${dpr}`);
  const i=await info(p);
  expect(i.dpr).toBe(dpr);expect(Math.abs(i.buffer-i.css*dpr)).toBeLessThanOrEqual(1);expect(pixelAligned(i.zoom)).toBe(true);expect(i.label).toBe(dpr);
  // 픽셀 정렬 휠 줌: 한 단계 위 정수 배율
  const r=(await p.locator('.game-canvas canvas').boundingBox())!;await p.mouse.move(r.x+r.width/2,r.y+r.height/2);await p.mouse.wheel(0,-120);
  await expect.poll(()=>info(p).then(x=>x.zoom)).toBeGreaterThan(i.zoom);expect(pixelAligned((await info(p)).zoom)).toBe(true);
  await p.getByRole('button',{name:'캐릭터 추적',exact:true}).click();await p.waitForTimeout(300);
  // 바닥 클릭이 장치 픽셀 캔버스에서도 정확한 칸으로
  // 캔버스 크기가 바뀐 뒤(사이드바 펼치기)에도 입력 환산 비율이 갱신되어야 한다(회귀: displayScale 미갱신으로 클릭 12% 어긋남)
  await p.getByRole('button',{name:'사이드바 펼치기'}).click();await p.waitForTimeout(600);
  expect(await p.evaluate(()=>{const g=(window as any).__NOBIS_GAME__,r=g.canvas.getBoundingClientRect();return Math.abs(g.scale.displayScale.x-g.canvas.width/r.width);})).toBeLessThan(.01);
  const start=(await info(p)).pos,target={x:Math.round(start.x)+1,y:Math.round(start.y)};
  await clickTile(p,target);await expect.poll(()=>info(p).then(x=>Math.hypot(x.pos.x-target.x,x.pos.y-target.y)),{timeout:15000}).toBeLessThan(.05);
  // 회귀: east(+x)로 걸은 뒤에도 새 아틀라스 프레임을 반전해 써야 한다(옛 east 프레임 이름 때문에 비상용 도형으로 떨어지던 버그)
  const look=await p.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),a=s.avatars.get(s.model.session.user.id);return{source:a.sprite.getData('visual-source'),dir:a.sprite.getData('visual-direction'),flip:a.sprite.flipX};});
  expect(look).toEqual({source:'atlas',dir:'east',flip:true});
  await p.screenshot({path:`../docs/display-${dpr}x-lobby.png`,animations:'disabled'});
  await c.close();
 });
}
