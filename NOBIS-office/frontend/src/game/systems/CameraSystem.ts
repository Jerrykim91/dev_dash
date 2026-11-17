import type {Point} from '../types';
export type CameraView={x:number;y:number;width:number;height:number;scrollX:number;scrollY:number;zoom:number};
export type WorldBounds={x:number;y:number;width:number;height:number};
export function screenToWorld(p:Point,c:CameraView):Point{return{x:c.scrollX+c.width/2+(p.x-c.x-c.width/2)/c.zoom,y:c.scrollY+c.height/2+(p.y-c.y-c.height/2)/c.zoom};}
export function worldToScreen(p:Point,c:CameraView):Point{return{x:c.x+c.width/2+(p.x-c.scrollX-c.width/2)*c.zoom,y:c.y+c.height/2+(p.y-c.scrollY-c.height/2)*c.zoom};}
export function boundScroll(c:CameraView,b:WorldBounds):Point{
 const axis=(position:number,size:number,origin:number,span:number)=>{const visible=size/c.zoom;if(visible>=span)return origin+span/2-size/2;return Math.max(origin-size/2+visible/2,Math.min(origin+span-size/2-visible/2,position));};
 return{x:axis(c.scrollX,c.width,b.x,b.width),y:axis(c.scrollY,c.height,b.y,b.height)};
}
export function zoomAt(c:CameraView,b:WorldBounds,zoom:number,before:Point,after=before):CameraView{
 const fit=Math.min(c.width/b.width,c.height/b.height,1),z=Math.max(fit,Math.min(1.8,zoom)),anchor=screenToWorld(before,c);
 const next={x:c.x,y:c.y,width:c.width,height:c.height,zoom:z,scrollX:anchor.x-c.width/2-(after.x-c.x-c.width/2)/z,scrollY:anchor.y-c.height/2-(after.y-c.y-c.height/2)/z},clamped=boundScroll(next,b);
 return{...next,scrollX:clamped.x,scrollY:clamped.y};
}
