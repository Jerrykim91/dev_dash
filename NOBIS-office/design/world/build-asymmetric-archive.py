"""Compile authored screen-relative u=x-y/v=x+y areas into shared logical data. No DB access."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=json.loads((ROOT/'design/world/office-world-v2.json').read_text())
old=json.loads((ROOT/'shared/maps.json').read_text())['office'];old_objects={o['id']:o for o in old['objects']}
# Retain original object contracts even when re-running after generation.
contracts=ROOT/'design/world/object-contracts.json'
if not contracts.exists():contracts.write_text(json.dumps(old_objects,ensure_ascii=False,indent=2)+'\n')
old_objects=json.loads(contracts.read_text())
zones=json.loads((ROOT/'shared/zones.json').read_text())
point=lambda uv:((uv[0]+uv[1])/2,(uv[1]-uv[0])/2)
def inside(p,poly):
 x,y=p;yes=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:yes=not yes
 return yes
def neighbors(p):return [(p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)]
def obj(p):return {'x':p[0],'y':p[1]}
def edge(a,b):return tuple(sorted((a,b)))
areas={};owner={};height={};anchors={}
for a in source['areas']:
 poly=list(map(point,a['polygon']));cells={(x,y) for x in range(source['width']) for y in range(source['height']) if inside((x,y),poly)}
 # Rasterized acute polygon tips may touch only diagonally; keep the anchor's cardinal component.
 target=point(a['anchor']);root=min(cells,key=lambda p:(math.dist(p,target),p));connected={root};queue=[root]
 for p in queue:
  for n in neighbors(p):
   if n in cells and n not in connected:connected.add(n);queue.append(n)
 cells=connected
 if cells&owner.keys():raise ValueError('Overlapping areas '+a['id'])
 areas[a['id']]={**a,'cells':cells,'polygon_grid':poly}
 for p in cells:owner[p]=a['id'];height[p]=a['elevation']
 target=point(a['anchor']);anchors[a['id']]=min(cells,key=lambda p:(math.dist(p,target),p))
floor=set(owner);paths=[];open_edges=set()
for start,end,width in source['connections']:
 ac,bc=areas[start]['cells'],areas[end]['cells'];a,b=min(((a,b) for a in ac for b in bc),key=lambda pair:(abs(pair[0][0]-pair[1][0])+abs(pair[0][1]-pair[1][1]),pair))
 queue=[a];prev={a:None}
 for p in queue:
  if p==b:break
  for n in neighbors(p):
   if n in prev or not (0<=n[0]<source['width'] and 0<=n[1]<source['height']) or n in owner and owner[n] not in [start,end]:continue
   prev[n]=p;queue.append(n)
 if b not in prev:raise ValueError('No connector '+start+' '+end)
 route=[];p=b
 while p is not None:route.append(p);p=prev[p]
 route.reverse();paths.append({'id':start+'--'+end,'from_area':start,'to_area':end,'width':width,'path':route})
 for i,p in enumerate(route):
  if i:
   a=route[i-1];dx,dy=p[0]-a[0],p[1]-a[1]
   for lane in range(-(width//2),width-width//2):
    u=(a[0]-dy*lane,a[1]+dx*lane);v=(p[0]-dy*lane,p[1]+dx*lane)
    if owner.get(u) in [None,start,end] and owner.get(v) in [None,start,end]:open_edges.add(edge(u,v))
  for dx in range(-(width//2),width-width//2):
   for dy in range(-(width//2),width-width//2):
    n=p[0]+dx,p[1]+dy
    if 0<=n[0]<source['width'] and 0<=n[1]<source['height']:
     floor.add(n);height.setdefault(n,areas[start]['elevation'])
closed=[];stairs=[];doors=[]
for p in sorted(floor):
 for n in neighbors(p):
  if n not in floor or p>n:continue
  barrier=owner.get(p)!=owner.get(n) or height[p]!=height[n]
  if barrier and edge(p,n) not in open_edges:closed.append([obj(p),obj(n)])
  elif barrier:
   c={'id':f'connector-{p[0]}-{p[1]}-{n[0]}-{n[1]}','from':obj(p),'to':obj(n)}
   (stairs if height[p]!=height[n] else doors).append(c)
# Place real existing interactables away from all doorway/stair cells and anchor tiles.
reserved={ (p[0]+dx,p[1]+dy) for p in anchors.values() for dx in range(-2,3) for dy in range(-2,3) if abs(dx)+abs(dy)<=2 }
for c in stairs+doors:
 for p in[(c['from']['x'],c['from']['y']),(c['to']['x'],c['to']['y'])]:reserved.add(p);reserved.update(neighbors(p))
objects=[];used=set();workstations=[];meeting_seats=[]
def add_object(template,id,p,**extra):
 o={**old_objects[template],'id':id,**obj(p),**extra};objects.append(o)
 used.update((o['x']+dx,o['y']+dy) for dx in range(o.get('width',1)) for dy in range(o.get('height',1)))
 return o
def connected_after(cells,solids,anchor):
 free=cells-solids
 if anchor not in free:return False
 seen={anchor};q=[anchor]
 for p in q:
  for n in neighbors(p):
   if n in free and n not in seen:seen.add(n);q.append(n)
 return seen==free
# Every employee receives an exclusive 3x3 plot, 2x1 desk, chair and reachable seat approach.
cfg=source.get('capacity',{}).get('workstations')
if cfg:
 aid=cfg['area'];cells=areas[aid]['cells'];size=cfg['plot_size'];stride=size+cfg['grid_gap'];best=[]
 for ox in range(stride):
  for oy in range(stride):
   candidates=[]
   for x,y in sorted(cells):
    if x%stride!=ox or y%stride!=oy:continue
    plot={(x+dx,y+dy) for dx in range(size) for dy in range(size)}
    if plot<=cells and not plot&reserved:candidates.append((x,y,plot))
   if len(candidates)>len(best):best=candidates
 if len(best)<cfg['count']:raise ValueError(f"Only {len(best)} employee plots fit")
 for i,(x,y,plot) in enumerate(best[:cfg['count']]):
  solids={(x,y),(x+1,y),(x+1,y+1)}
  if not connected_after(cells,(used&cells)|solids,anchors[aid]):raise ValueError('Workstation disconnects floor')
  desk_id=f'desk-{i}';chair_id='chair' if i==0 else f'work-chair-{i}'
  add_object('desk-0',desk_id,(x,y),width=2,height=1,label=f'업무 책상 {i+1:02d}')
  add_object('chair',chair_id,(x+1,y+1),label=f'업무 의자 {i+1:02d}')
  workstations.append({'id':f'workstation-{i+1:02d}','desk_id':desk_id,'chair_id':chair_id,'plot':[obj(p) for p in sorted(plot)],'approach':obj((x+1,y+2))})
  reserved|=plot
# Fifteen real chair objects surround a single 3x5 temporary conference table.
cfg=source.get('capacity',{}).get('meeting')
if cfg:
 aid=cfg['area'];cells=areas[aid]['cells'];portal={tuple(c[k].values()) for c in stairs+doors for k in ['from','to']};candidates=[]
 for x,y in sorted(cells):
  box={(x+dx,y+dy) for dx in range(7) for dy in range(9)}
  if box<=cells and not box&portal:candidates.append((x,y,box))
 if not candidates:raise ValueError('Conference layout does not fit')
 x,y,box=min(candidates,key=lambda p:math.dist((p[0]+3,p[1]+4),anchors[aid]));tx,ty=x+2,y+2
 chair_points=[(tx+i,ty-1,(tx+i,ty-2)) for i in range(3)]+[(tx+i,ty+5,(tx+i,ty+6)) for i in range(3)]+[(tx-1,ty+i,(tx-2,ty+i)) for i in range(5)]+[(tx+3,ty+i,(tx+4,ty+i)) for i in range(4)]
 old_anchor=anchors[aid];solids={(tx+dx,ty+dy) for dx in range(3) for dy in range(5)}|{(cx,cy) for cx,cy,_ in chair_points}
 anchors[aid]=min(cells-box,key=lambda p:math.dist(p,old_anchor))
 if not connected_after(cells,solids,anchors[aid]):raise ValueError('Conference layout disconnects floor')
 add_object('meeting-table-0','meeting-table-0',(tx,ty),width=3,height=5,placeholder=True,label='15인 회의 테이블')
 for i,(cx,cy,approach) in enumerate(chair_points):
  id=f'meeting-chair-{i+1:02d}';add_object('chair',id,(cx,cy),label=f'회의 의자 {i+1:02d}');meeting_seats.append({'chair_id':id,'approach':obj(approach)})
 reserved|=box|{(anchors[aid][0]+dx,anchors[aid][1]+dy) for dx in range(-2,3) for dy in range(-2,3)}

for aid,ids in source['placements'].items():
 cells=areas[aid]['cells'];available=[p for p in cells if p not in reserved and all(n in cells for n in neighbors(p))]
 # Spread furnishings through the room instead of lining a single wall.
 for i,id in enumerate(ids):
  candidates=[p for p in available if p not in used and all(abs(p[0]-u[0])+abs(p[1]-u[1])>=3 for u in used)]
  if not candidates:candidates=[p for p in available if p not in used]
  if not candidates:raise ValueError('No furniture slot '+id)
  center=anchors[aid]
  def preserves_access(p):
   free=cells-used-{p};seen={anchors[aid]};q=[anchors[aid]]
   for current in q:
    for n in neighbors(current):
     if n in free and n not in seen:seen.add(n);q.append(n)
   return len(seen)==len(free)
  candidates=[p for p in candidates if preserves_access(p)]
  if not candidates:raise ValueError('Furniture would disconnect '+id)
  p=max(candidates,key=lambda p:(min([math.dist(p,u) for u in used&cells] or [math.dist(p,center)]),-p[0],-p[1]))
  objects.append({**old_objects[id],**obj(p)});used.add(p)
# No old partition grid. Explicit edge obstacles define walls, glass and rails.
surface={'regions':[{'id':f'height-{z}','elevation':z,'tiles':{'x':0,'y':0,'width':source['width'],'height':source['height']},'cells':[obj(p) for p in sorted(floor) if height[p]==z]} for z in sorted(set(height.values())) if z], 'stairs':stairs}
world={'id':source['map_id'],'version':source['version'],'workstations':workstations,'meeting_seats':meeting_seats,'visualAreas':[{'id':id,'name':a['name'],'anchor':obj(anchors[id])} for id,a in areas.items()],'width':source['width'],'height':source['height'],'spawn':obj(anchors['entrance']),'objects':objects,'walkable_tiles':[obj(p) for p in sorted(floor)],'closed_edges':closed,'surface':surface}
(ROOT/'shared/maps.json').write_text(json.dumps({'office':world},ensure_ascii=False,indent=2)+'\n')
for z in zones:
 if z['id']=='vacation':z.update(id='garden',name='옥상 정원 · 휴식',chat_bubbles_allowed=True)
 cells=set().union(*(a['cells'] for a in areas.values() if a['zone_id']==z['id'])) if z['id']!='office' else floor-set(owner)|areas['entrance']['cells']
 aid=z['id'] if z['id'] in anchors else 'entrance';z['anchor']=obj(anchors[aid]);z['cells']=[obj(p) for p in sorted(cells)]
 # Keep bounds only for legacy display clients; cells are authoritative for nonrectangular zones.
 if cells:
  xs=[p[0] for p in cells];ys=[p[1] for p in cells];z['tiles']={'x':min(xs),'y':min(ys),'width':max(xs)-min(xs)+1,'height':max(ys)-min(ys)+1} if z['id']!='office' else None
(ROOT/'shared/zones.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
layout=json.loads((ROOT/'shared/world-layout.json').read_text());layout.update(version=source['version'],surface=surface,architecture=[],areas=[{k:(list(map(obj,v)) if k=='cells' else v) for k,v in a.items()} for a in areas.values()],connectors=[{**p,'path':list(map(obj,p['path']))} for p in paths],doors=doors)
layout['zones']=[{'zone_id':z['id'],'tiles':z['tiles'],'visual_asset':z['id']} for z in zones];layout['reference']={'path':source['reference'],'fallback':'design/reference/nobis-office-target.png','usage':'composition only; final artwork deferred'}
(ROOT/'shared/world-layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'floor_tiles':len(floor),'walls':len(closed),'stairs':len(stairs),'doors':len(doors),'anchors':{k:obj(v) for k,v in anchors.items()},'objects':len(objects)},ensure_ascii=False))
