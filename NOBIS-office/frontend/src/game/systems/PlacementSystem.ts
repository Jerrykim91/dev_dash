import type {FurnitureItem,FurnitureInstance,FurniturePlacement,MapData,Point} from '../types';
export function footprint(item:FurnitureItem,p:FurniturePlacement):Point[]{
 const [w,h]=p.rotation%180===90?[item.size.height,item.size.width]:[item.size.width,item.size.height];
 return Array.from({length:w*h},(_,i)=>({x:p.grid_x+i%w,y:p.grid_y+Math.floor(i/w)}));
}
export function placementError(placements:FurniturePlacement[],inventory:FurnitureInstance[],catalog:FurnitureItem[],map:MapData,player?:Point):string {
 const instances=new Map(inventory.map(i=>[i.id,catalog.find(c=>c.item_id===i.item_id)!]));
 if(placements.length>70)return '한 집에는 최대 70개까지 배치할 수 있어요.';
 const solids:Point[][]=[];
 const used=new Set<string>(),occupied=new Set(['10,8']),blocked=new Set(['10,8']);
 for(const p of placements){
  if(!Number.isInteger(p.grid_x)||!Number.isInteger(p.grid_y))return '정수 타일 좌표를 선택해 주세요.';
  const item=instances.get(p.instance_id);if(!item)return '내 가구만 배치할 수 있어요.';
  if(used.has(p.instance_id))return '같은 가구를 중복 설치할 수 없어요.';used.add(p.instance_id);
  if(![0,90,180,270].includes(p.rotation)||(!item.rotatable&&p.rotation))return '회전할 수 없는 방향이에요.';
  const cells=footprint(item,p);if(item.blocking)solids.push(cells);
  for(const cell of cells){
   const k=`${cell.x},${cell.y}`;
   if(cell.x<0||cell.y<0||cell.x>=map.width||cell.y>=map.height)return '벽 밖에는 배치할 수 없어요.';
   if(occupied.has(k))return '가구 또는 출입문과 겹쳐요.';
   if(k==='10,7'||k===`${map.spawn.x},${map.spawn.y}`)return '입구와 기본 이동 위치를 비워 주세요.';
   if(item.blocking&&player&&Math.round(player.x)===cell.x&&Math.round(player.y)===cell.y)return '캐릭터가 있는 칸이에요.';
   occupied.add(k);if(item.blocking)blocked.add(k);
  }
 }
 const reached=new Set(['10,7']),queue=[{x:10,y:7}];
 for(let i=0;i<queue.length;i++){const p=queue[i];for(const n of [{x:p.x+1,y:p.y},{x:p.x-1,y:p.y},{x:p.x,y:p.y+1},{x:p.x,y:p.y-1}]){const k=`${n.x},${n.y}`;if(n.x>=0&&n.y>=0&&n.x<map.width&&n.y<map.height&&!blocked.has(k)&&!reached.has(k)){reached.add(k);queue.push(n);}}}
 if(reached.size!==map.width*map.height-blocked.size)return '입구로 이어지는 통로를 확보해 주세요.';
 if(solids.some(cells=>!cells.some(p=>[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>reached.has(`${p.x+dx},${p.y+dy}`)))))return '가구에 접근할 수 있는 통로가 필요해요.';
 return '';
}
export function layoutMap(base:MapData,placements:FurniturePlacement[],inventory:FurnitureInstance[],catalog:FurnitureItem[]):MapData {
 const objects=placements.flatMap(p=>{
  const instance=inventory.find(i=>i.id===p.instance_id),item=catalog.find(i=>i.item_id===instance?.item_id);if(!item)return [];
  const [width,height]=p.rotation%180===90?[item.size.height,item.size.width]:[item.size.width,item.size.height];
  const previous=base.objects.find(o=>o.id===p.instance_id);
  return [{...previous,id:p.instance_id,instance_id:p.instance_id,kind:item.asset_key,label:item.name,x:p.grid_x,y:p.grid_y,width,height,blocking:item.blocking,rotation:p.rotation}];
 });
 return {...base,objects:[...objects,...base.objects.filter(o=>o.id==='home-exit')]};
}
