export type LabelBox={id:string;x:number;y:number;width:number;height:number;priority:number};
export type PlacedLabel=LabelBox&{visible:boolean};
export function overlaps(a:{x:number;y:number;width:number;height:number},b:{x:number;y:number;width:number;height:number},gap=4){return a.x<b.x+b.width+gap&&a.x+a.width+gap>b.x&&a.y<b.y+b.height+gap&&a.y+a.height+gap>b.y;}
// Screen-space placement keeps text readable at any zoom and within the visible canvas.
export function layoutLabels(labels:LabelBox[],view:{x:number;y:number;width:number;height:number},reserved:LabelBox[]=[]):PlacedLabel[]{
 const placed:PlacedLabel[]=[],occupied:LabelBox[]=[...reserved];
 for(const label of [...labels].sort((a,b)=>a.priority-b.priority||a.id.localeCompare(b.id))){
  const width=Math.min(label.width,view.width),height=Math.min(label.height,view.height),clamp=(x:number,y:number)=>({x:Math.max(view.x,Math.min(view.x+view.width-width,x)),y:Math.max(view.y,Math.min(view.y+view.height-height,y))});
  const offsets=[[0,0],[-width*.55,-5],[width*.55,-5],[0,-height-6],[0,height+6],[-width-5,0],[width+5,0]];
  const candidates=offsets.map(([dx,dy])=>clamp(label.x+dx,label.y+dy));
  let target=candidates.find(p=>!occupied.some(o=>overlaps({...p,width,height},o)));
  if(!target){for(let y=view.y;y+height<=view.y+view.height;y+=height+6)for(let x=view.x;x+width<=view.x+view.width;x+=width+6)candidates.push({x,y});
  candidates.sort((a,b)=>Math.hypot(a.x-label.x,a.y-label.y)-Math.hypot(b.x-label.x,b.y-label.y));
  target=candidates.find(p=>!occupied.some(o=>overlaps({...p,width,height},o)));}
  const result={...label,...(target??clamp(label.x,label.y)),width,height,visible:!!target};
  placed.push(result);if(target)occupied.push(result);
 }
 return placed;
}
