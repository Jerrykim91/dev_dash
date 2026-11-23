import {test,expect,type Page} from '../frontend/node_modules/@playwright/test';

// 옷 갈아입기(실행 중 겹치기, docs/visual-standard-v2.md §15): 고른 파트가 다른 사람 화면에도 레이어로 그려진다.
async function join(p:Page,name:string){await p.goto('/');await p.getByLabel('개발용 닉네임',{exact:true}).fill(name);await p.getByRole('button',{name:/오피스 입장하기/}).click();await expect(p.locator('.connection')).toContainText('접속');await p.waitForFunction(()=>!!(window as any).__NOBIS_GAME__?.registry.get('world')?.movement);}
const look=(p:Page,nickname:string)=>p.evaluate(n=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),pl=s.model.players.find((x:any)=>x.nickname===n),a=pl&&s.avatars.get(pl.id);if(!a)return null;const l=a.sprite.getData('layers');return{parts:pl.avatar.parts??null,source:a.sprite.getData('visual-source'),base:a.sprite.frame.name,top:l?.top.visible?l.top.frame.name:null,bottom:l?.bottom.visible?l.bottom.frame.name:null,hair:l?.hair.visible?l.hair.frame.name:null};},nickname);

test('wardrobe: choosing hair, top and bottom renders layered parts for everyone and can reset to the default look',async({browser})=>{
 const ca=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:2}),a=await ca.newPage(),cb=await browser.newContext(),b=await cb.newPage();
 await join(a,'옷입기A');await join(b,'옷입기B');
 expect((await look(b,'옷입기A'))?.source).toBe('atlas');
 await a.locator('.wardrobe>summary').click();await a.getByRole('group',{name:'옷 갈아입기'}).getByRole('button',{name:'입어 보기'}).click();
 await a.locator('#wardrobe-hair').selectOption('1');await a.locator('#wardrobe-top').selectOption('hoodie');await a.locator('#wardrobe-bottom').selectOption('skirt');
 // 레이어 프레임은 다음 화면 프레임에 바뀐다 → 상의·하의까지 함께 기다린다
 await expect.poll(()=>look(b,'옷입기A'),{timeout:15000}).toMatchObject({parts:{hair:'1',top:'hoodie',bottom:'skirt'},source:'parts',hair:'part/hair/1/south',top:expect.stringMatching(/^part\/top\/hoodie\/south\//),bottom:expect.stringMatching(/^part\/bottom\/skirt\/south\//)});
 const seen=(await look(b,'옷입기A'))!;expect(seen.base).toMatch(/^part\/base\/south\//);expect(seen.top).toMatch(/^part\/top\/hoodie\/south\//);expect(seen.bottom).toMatch(/^part\/bottom\/skirt\/south\//);
 const own=await look(a,'옷입기A');expect(own?.source).toBe('parts');
 await a.evaluate(()=>{const s=(window as any).__NOBIS_GAME__.registry.get('world'),me=s.avatars.get(s.model.session.user.id),w=me.container,c=s.cameras.main;s.cameraMode='explore';c.stopFollow();c.setZoom(4);c.centerOn(w.x,w.y-30);});
 await a.waitForTimeout(400);const box=(await a.locator('.game-canvas canvas').boundingBox())!;
 await a.screenshot({path:'../docs/wardrobe-parts.png',clip:{x:box.x+box.width/2-200,y:box.y+box.height/2-200,width:400,height:320}});
 await a.getByRole('group',{name:'옷 갈아입기'}).getByRole('button',{name:'기본 외형으로'}).click();
 await expect.poll(()=>look(b,'옷입기A').then(x=>x?.source),{timeout:15000}).toBe('atlas');expect((await look(b,'옷입기A'))?.top).toBeNull();
 await ca.close();await cb.close();
});
