// Original code-authored pixel artwork. No third-party art or network requests.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('../../frontend/node_modules/@playwright/test');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'frontend/public/visual');
const tokens=JSON.parse(fs.readFileSync(path.join(root,'frontend/src/design/tokens.json')));
const world=JSON.parse(fs.readFileSync(path.join(root,'shared/maps.json'))).office;
const catalog=JSON.parse(fs.readFileSync(path.join(root,'shared/furniture-catalog.json')));
const palettes=['#d2beff','#b5e5d0','#ffceaf','#a9d8ff','#f4bfe7','#e5e8ac','#b7c6f2','#e5bbbc','#bbdedc','#e2c99d','#c0b1df','#b2d4ad','#e6b8d0','#abc1dc','#d4d4aa','#d0b9a6'];
const base=new Map();for(const o of [...world.objects,...catalog.map(i=>({kind:i.asset_key,width:i.size.width,height:i.size.height})),{kind:'door'}]){const kind=o.kind==='partition'?'partition-'+o.axis:o.kind;base.set(`${kind}/${o.width??1}x${o.height??1}`,{kind,width:o.width??1,height:o.height??1});}
(async()=>{fs.mkdirSync(out,{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});let data;try{const page=await browser.newPage();data=await page.evaluate(({tokens,palettes,bases})=>{
 const cols=tokens.colors,art={outline:'#35283f',hair:['#51404e','#665044','#35354b','#855c63'],skin:['#f1c8a9','#e2ae91','#d6a183','#f4d5bc'],wood:'#c49b7e',woodLight:'#edcfa8',woodShade:'#936b70',metal:'#66516f',fabric:'#b8a1d5',fabricLight:'#d5bee8',leaf:'#62977b',leafLight:'#a1c99b',screen:'#abd9cb',paper:'#f8e9cf'};
 function canvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d');x.imageSmoothingEnabled=false;return[c,x];}
 function primitives(ctx){return{r:(x,y,w,h,c)=>{ctx.fillStyle=c;ctx.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));},p:(pts,c)=>{ctx.fillStyle=c;ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(Math.round(x),Math.round(y)):ctx.moveTo(Math.round(x),Math.round(y)));ctx.closePath();ctx.fill();}};}
 const frames=[];
 for(let variant=0;variant<16;variant++)for(const dir of ['north','south','east','west'])for(const [state,count]of Object.entries({idle:2,walking:4,sitting:2,typing:2}))for(let f=0;f<count;f++){
  const [c,x]=canvas(48,64),{r,p}=primitives(x);const hair=art.hair[variant%4],skin=art.skin[Math.floor(variant/4)%4],shirt=palettes[variant],side=dir==='east'||dir==='west',back=dir==='north',sit=state==='sitting'||state==='typing',step=state==='walking'?[0,2,0,-2][f]:0,bob=state==='walking'?(f%2):state==='idle'?f:0,headY=6+bob+(sit?7:0);
  // Hard edged pixel silhouette; foot baseline y58 is invariant for every pose.
  r(12,57,24,2,'#392a4440');r(16,56,17,3,'#392a4440');
  if(sit){r(13,45,10,9,art.outline);r(25,45,10,9,art.outline);r(12,53,12,5,art.paper);r(26,53,12,5,art.paper);r(15,46,19,5,shirt);}
  else{r(15,43,8,13+step,art.outline);r(26,43,8,13-step,art.outline);r(12,54+step,12,4,art.paper);r(26,54-step,12,4,art.paper);r(13,57+step,11,1,art.metal);r(27,57-step,11,1,art.metal);}
  r(13,29+bob+(sit?5:0),23,17,art.outline);r(15,30+bob+(sit?5:0),19,14,shirt);r(17,31+bob+(sit?5:0),14,3,art.paper);r(16,35+bob+(sit?5:0),3,8,cols.accentStrong);r(28,36+bob+(sit?5:0),4,7,shirt);
  const armY=state==='typing'?39+(f%2):34+step;r(10,armY,5,10,skin);r(34,state==='typing'?40-(f%2):34-step,5,9,skin);
  if(state==='typing'){r(14,44,22,5,art.metal);r(17,44,16,2,art.screen);r(16+f,40,7,4,skin);r(28-f,40,7,4,skin);}
  // 24px head with outlined stepped corners: approx 2.4 heads tall.
  r(13,headY-2,22,2,art.outline);r(9,headY,30,23,art.outline);r(7,headY+6,34,12,art.outline);r(11,headY+2,26,21,skin);r(9,headY+8,30,9,skin);r(15,headY+22,18,3,skin);
  r(10,headY,28,9,hair);r(14,headY-2,20,6,hair);r(8,headY+6,6,12,hair);r(34,headY+6,5,11,hair);r(14,headY+6,7,5,hair);r(24,headY+6,10,3,hair);r(15,headY+1,12,2,'#ffffff26');
  if(back){r(11,headY+9,26,13,hair);r(14,headY+21,20,2,hair);}
  else{const eyes=side?[dir==='east'?30:15]:[17,29];for(const eye of eyes){r(eye,headY+14,3,state==='idle'&&f===1?2:4,art.outline);if(!(state==='idle'&&f===1))r(eye,headY+14,1,1,art.paper);}r(side?(dir==='east'?34:11):22,headY+20,4,1,art.woodShade);r(12,headY+19,5,2,'#e9969f');r(32,headY+19,4,2,'#e9969f');}
  // Variant-specific clips and tuft, never tinting skin or hair at runtime.
  r(variant%2?32:11,headY+8,5,3,palettes[(variant+5)%16]);if(variant%3===0)r(27,headY-4,5,4,hair);
  frames.push({name:`v${variant}/${dir}/${state}/${f}`,canvas:c});
 }
 function furniture(kind,w,h,rotation,layer){const[c,x]=canvas(128,160);x.translate(64,104);const{r,p}=primitives(x);const face=rotation===90||rotation===180,wood=art.wood,light=art.woodLight,shade=art.woodShade;
  const box=(height,top=light,left=shade,right=wood)=>{const a=[0,-14-height],b=[32*(w-1)+27,16*(w-1)-height],d=[-32*(h-1)-27,16*(h-1)-height],cc=[32*(w-h),16*(w+h-2)+14-height];p([d,cc,[cc[0],cc[1]+height],[d[0],d[1]+height]],left);p([cc,b,[b[0],b[1]+height],[cc[0],cc[1]+height]],right);p([a,b,cc,d],top);};
  const desk=kind==='desk'||kind==='table';
  if(layer==='lower'){
   if(kind.startsWith('partition')){const ay=kind==='partition-y';p([[ay?16:-16,-8],[ay?-16:16,8],[ay?-16:16,11],[ay?16:-16,-5]],art.metal);return c;}
   if(kind==='rug'){box(1,cols.accent,cols.accentStrong,cols.accentStrong);p([[0,-8],[32*(w-1)+18,16*(w-1)],[32*(w-h),16*(w+h-2)+8],[-32*(h-1)-18,16*(h-1)]],cols.cream);p([[0,-4],[32*(w-1)+10,16*(w-1)],[32*(w-h),16*(w+h-2)+4],[-32*(h-1)-10,16*(h-1)]],cols.accentStrong);return c;}
   p([[-23,3],[0,-9],[32*(w-1)+25,16*(w-1)+3],[32*(w-h),16*(w+h-2)+17],[-32*(h-1)-25,16*(h-1)+3]],'#30233d30');
   if(desk){r(-18,-22,5,33,shade);r(18+32*(w-1),16*(w-1)-22,5,33,shade);r(-16-32*(h-1),16*(h-1)-22,5,33,shade);x.save();x.translate(0,-20);box(5,light,shade,wood);x.restore();if(kind==='desk'){r(-14,-19,18,9,wood);r(-8,-15,5,2,art.paper);}}
   else if(kind==='chair'){box(14,art.fabricLight,cols.accentStrong,art.fabric);r(-17,0,4,13,art.metal);r(14,0,4,13,art.metal);}
   else if(kind==='sofa'){box(23,art.fabricLight,cols.accentStrong,art.fabric);r(-21,4,5,9,wood);r(19+32*(w-1),16*(w-1)+4,5,9,wood);}
   else if(kind==='bed'){box(22,art.paper,cols.accentStrong,art.fabric);}
   else if(kind==='plant'){box(17,art.paper,shade,wood);r(-12,-8,23,2,light);}
   else if(kind==='lamp'){box(4,wood,shade,wood);r(-2,-48,4,48,art.metal);}
   else if(kind==='bookshelf'){box(60,wood,shade,wood);r(-20,-57,40,47,'#634753');r(-20,-33,40,4,light);r(-20,-9,40,3,light);}
   else if(kind==='door'){r(-20,-66,40,70,shade);r(-16,-62,32,66,'#35283f');r(10,-30,4,4,art.paper);r(-16,-65,32,3,light);}
   else if(kind==='whiteboard'){r(-22,-53,4,61,art.metal);r(18,-53,4,61,art.metal);}
   else if(kind==='arcade'){box(57,cols.accent,cols.accentStrong,art.metal);r(-16,-63,32,28,cols.ink);r(-18,-27,36,8,wood);}
   else{box(20,wood,shade,wood);}
  }else{
   if(kind.startsWith('partition')){const ay=kind==='partition-y',a=[ay?16:-16,-8],b=[-a[0],8];p([a,b,[b[0],b[1]-42],[a[0],a[1]-42]],'#c8e4e555');p([[a[0],a[1]-41],[b[0],b[1]-41],[b[0],b[1]-38],[a[0],a[1]-38]],art.paper);r(a[0]-1,a[1]-41,3,41,cols.borderStrong);r(b[0]-1,b[1]-41,3,41,cols.borderStrong);p([[a[0]+3,a[1]-34],[b[0]-3,b[1]-34],[b[0]-3,b[1]-32],[a[0]+3,a[1]-32]],'#ffffff70');}
   else if(desk){if(kind==='desk'){const dx=16*(w-h);r(dx-14,-61,29,23,art.metal);r(dx-11,-58,23,16,art.screen);r(dx-8,-55,11,2,art.paper);r(dx-8,-50,16,2,art.leaf);r(dx-2,-38,5,10,art.metal);p([[dx-13,-27],[dx,-33],[dx+15,-26],[dx+2,-19]],cols.accentStrong);}p([[-15,-28],[-4,-34],[12,-26],[1,-20]],art.paper);r(10+32*(w-1)/2,-32,6,13,cols.accentStrong);r(10+32*(w-1)/2,-34,6,2,cols.cream);p([[-24,-21],[-19,-24],[-10,-20],[-15,-17]],wood);}
   else if(kind==='chair'){const dx=face?14:-18;r(dx,-44,7,29,shade);r(-18,-44,36,20,art.fabric);r(-15,-41,30,3,art.fabricLight);r(-15,-26,29,2,cols.accentStrong);}
   else if(kind==='sofa'){r(-25,-42,51+32*(w-1),17,art.fabric);r(-22,-39,45+32*(w-1),3,art.fabricLight);r(-27,-28,9,26,cols.accentStrong);r(20+32*(w-1),16*(w-1)-26,9,24,art.fabricLight);r(-16,-27,14,11,cols.cream);r(-14,-25,10,2,art.paper);}
   else if(kind==='bed'){p([[0,-34],[25,-21],[0,-8],[-25,-21]],art.paper);p([[0,-16],[27,0],[-32*(h-1),16*(h-1)+15],[-27-32*(h-1),16*(h-1)]],art.fabric);p([[0,-13],[24,0],[-32*(h-1),16*(h-1)+12],[-24-32*(h-1),16*(h-1)]],art.fabricLight);}
   else if(kind==='plant'){r(-3,-65,6,46,art.leaf);r(-22,-53,20,11,art.leaf);r(3,-64,19,12,art.leaf);r(-17,-57,15,7,art.leafLight);r(5,-68,14,7,art.leafLight);r(-8,-77,15,15,art.leaf);r(-7,-77,9,4,art.leafLight);}
   else if(kind==='lamp'){p([[-14,-67],[14,-67],[22,-45],[-22,-45]],cols.cream);r(-11,-64,17,3,art.paper);r(-18,-46,36,3,cols.creamDark);}
   else if(kind==='bookshelf'){for(let row=0;row<2;row++)for(let j=0;j<5;j++){const cc=[cols.accent,art.paper,art.leafLight,cols.warning,cols.info][(j+row+rotation/90)%5];r(-16+j*7,-52+row*26,5,15-(j%2)*3,cc);r(-16+j*7,-50+row*26,5,1,'#ffffff55');}}
   else if(kind==='computer'){r(face?-17:-20,-60,40,29,art.metal);r(-16,-56,32,21,art.screen);r(-13,-53,12,2,art.paper);r(-13,-47,23,2,art.leaf);r(-3,-31,6,10,art.metal);p([[-14,-24],[0,-29],[17,-22],[2,-15]],art.paper);p([[-10,-23],[0,-26],[12,-22],[1,-18]],cols.accentStrong);}
   else if(kind==='coffee'){r(-19,-60,38,37,art.metal);r(-16,-56,32,8,wood);r(-13,-51,5,4,cols.success);r(-13,-40,27,5,cols.ink);r(-7,-32,14,11,art.paper);r(7,-30,5,7,cols.cream);r(-18,-24,36,4,art.woodLight);r(12,-52,3,3,cols.warning);}
   else if(kind==='whiteboard'){r(-29,-73,58,46,wood);r(-26,-70,52,40,art.paper);r(-22,-64,22,3,cols.accentStrong);r(-22,-56,39,2,art.leaf);r(-22,-49,17,2,cols.accentStrong);r(4,-47,12,10,cols.cream);r(-22,-36,30,2,wood);}
   else if(kind==='arcade'){r(-13,-59,26,19,cols.ink);r(-11,-57,22,15,art.screen);r(-7,-54,4,4,cols.cream);r(3,-50,4,4,cols.accentStrong);r(-16,-26,32,4,cols.cream);r(-9,-30,3,5,cols.error);r(8,-26,4,2,cols.error);r(-13,-11,26,4,cols.ink);}
   else if(kind==='decoration'){r(-17,-43,34,25,art.paper);p([[-17,-43],[-11,-54],[-2,-43]],art.paper);p([[3,-43],[11,-54],[17,-43]],art.paper);r(-10,-35,3,4,art.outline);r(7,-35,3,4,art.outline);r(-3,-28,6,2,wood);r(-14,-29,5,2,cols.error);r(10,-29,5,2,cols.error);}
  }return c;
 }
 const furnishing=[];for(const b of bases)for(const rotation of b.kind.startsWith('partition')?[0]:[0,90,180,270]){const w=rotation%180?b.height:b.width,h=rotation%180?b.width:b.height,key=`${b.kind}/${w}x${h}/${rotation}`;for(const layer of ['lower','upper'])if(!furnishing.some(f=>f.name===key+'/'+layer))furnishing.push({name:key+'/'+layer,canvas:furniture(b.kind,w,h,rotation,layer)});}
 function pack(list,w,h,maxCols,maxRows){const pages=[];for(let start=0;start<list.length;start+=maxCols*maxRows){const chunk=list.slice(start,start+maxCols*maxRows),rows=Math.ceil(chunk.length/maxCols),[c,x]=canvas(maxCols*w,rows*h),frames={};chunk.forEach((f,i)=>{const xx=i%maxCols*w,yy=Math.floor(i/maxCols)*h;x.drawImage(f.canvas,xx,yy);frames[f.name]={frame:{x:xx,y:yy,w,h},rotated:false,trimmed:false,spriteSourceSize:{x:0,y:0,w,h},sourceSize:{w,h}};});pages.push({png:c.toDataURL('image/png').split(',')[1],frames,width:c.width,height:c.height});}return pages;}
 const bounds={};for(let i=0;i<furnishing.length;i+=2){let minX=128,minY=160,maxX=0,maxY=0;for(const f of furnishing.slice(i,i+2)){const a=f.canvas.getContext('2d').getImageData(0,0,128,160).data;for(let y=0;y<160;y++)for(let x=0;x<128;x++)if(a[(y*128+x)*4+3]>0){minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}}bounds[furnishing[i].name.replace('/lower','')]={x:Math.max(0,minX-4),y:Math.max(0,minY-4),w:Math.min(128,maxX+5)-Math.max(0,minX-4),h:Math.min(160,maxY+5)-Math.max(0,minY-4)};}return {avatar:pack(frames,48,64,32,32),furniture:pack(furnishing,128,160,8,10),furnitureBounds:bounds,originalPalette:art};
 },{tokens,palettes,bases:[...base.values()]});}finally{await browser.close();}
 const manifest={version:1,maxTextureSize:2048,atlases:[],frames:{},avatar:{width:48,height:64,portrait:{x:6,y:0,w:36,h:34},origin:{x:.5,y:58/64},scale:1.125,palettes,directions:['north','south','east','west'],animations:{idle:{frames:2,fps:1.2},walking:{frames:4,fps:8},sitting:{frames:2,fps:1.5},typing:{frames:2,fps:5}}},furniture:{width:128,height:160,origin:{x:.5,y:104/160},previewBounds:data.furnitureBounds},license:{origin:'original-code-authored',source:'infra/visual/build-assets.cjs',externalArt:false,policy:'Project-internal artwork; external distribution license is not assigned.'}};
 for(const category of ['avatar','furniture'])for(const [i,page]of data[category].entries()){
  const bytes=Buffer.from(page.png,'base64'),digest=crypto.createHash('sha256').update(bytes).digest('hex').slice(0,12),key=`nobis-${category}-${i}`,image=`visual/${category}-${digest}.png`;
  const atlasContent=JSON.stringify({frames:page.frames,meta:{image:path.basename(image),size:{w:page.width,h:page.height},scale:'1'}}),atlasDigest=crypto.createHash('sha256').update(atlasContent).digest('hex').slice(0,12),atlas=`visual/${category}-atlas-${atlasDigest}.json`;
  fs.writeFileSync(path.join(root,'frontend/public',image),bytes);fs.writeFileSync(path.join(root,'frontend/public',atlas),atlasContent);
  manifest.atlases.push({key,image,data:atlas,width:page.width,height:page.height,bytes:bytes.length});for(const [name,frame]of Object.entries(page.frames))manifest.frames[category+'/'+name]={atlas:key,frame:name,rect:frame.frame};
 }
 fs.writeFileSync(path.join(root,'frontend/src/game/visual/manifest.json'),JSON.stringify(manifest,null,2)+'\n');
 let css='/* Generated from tokens.json by infra/visual/build-assets.cjs. */\n:root{\n';for(const [name,value]of Object.entries(tokens.colors)){const rgb=value.slice(1).match(/../g).map(v=>parseInt(v,16));css+=` --color-${name}:${value}; --color-${name}-rgb:${rgb.join(' ')};\n`;}for(const group of ['font','radius','motion'])for(const [name,value]of Object.entries(tokens[group]))css+=` --${group}-${name}:${value};\n`;css+='}\n';fs.writeFileSync(path.join(root,'frontend/src/design/tokens.css'),css);
 console.log(JSON.stringify({atlasCount:manifest.atlases.length,frames:Object.keys(manifest.frames).length,totalPngBytes:manifest.atlases.reduce((n,a)=>n+a.bytes,0),decodedTextureBytes:manifest.atlases.reduce((n,a)=>n+a.width*a.height*4,0),sizes:manifest.atlases.map(a=>[a.width,a.height])}));
})().catch(e=>{console.error(e);process.exitCode=1;});
