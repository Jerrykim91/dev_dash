import json
import hashlib
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SHARED=ROOT/'shared'
if not SHARED.exists(): SHARED=Path(__file__).resolve().parents[1]/'shared'
MAPS=json.loads((SHARED/'maps.json').read_text())
ZONES=json.loads((SHARED/'zones.json').read_text())
ROOM_DATA=json.loads((SHARED/'rooms.json').read_text())
from .seats import with_seats
for _m in ROOM_DATA['maps'].values():with_seats(_m)
WORLD=ROOM_DATA['maps']['lobby']
PERSONAL=json.loads((SHARED/'personal-room.json').read_text())
with_seats(MAPS.get('office'))
WORLD_REVISION=hashlib.sha256(json.dumps([WORLD,ZONES],sort_keys=True).encode()).hexdigest()[:16]
PUBLIC_ZONES={z['id'] for z in ZONES}
BLOCKED={(o['x']+dx,o['y']+dy) for o in WORLD['objects'] if o.get('blocking',True) for dx in range(o.get('width',1)) for dy in range(o.get('height',1))}
FLOOR={(p['x'],p['y']) for p in WORLD['walkable_tiles']}
ZONE_CELLS={z['id']:{(p['x'],p['y']) for p in z.get('cells',[])} for z in ZONES}
CLOSED={((a['x'],a['y']),(b['x'],b['y'])) for a,b in WORLD.get('closed_edges',[])}
CLOSED|={(b,a) for a,b in list(CLOSED)}

def map_for(scope=None):return PERSONAL if scope and(scope=='personal' or scope.startswith('personal:')) else ROOM_DATA['maps'].get(scope,WORLD)

def allowed(zone,user_id=None): return zone in PUBLIC_ZONES or zone=='personal' or (user_id is not None and zone==f'personal:{user_id}')

def zones_for(_uid=None): return ZONES

def zone_at(x,y,scope='office'):
    if scope.startswith('personal:'):return 'personal'
    return next((d['zone_id'] for d in ROOM_DATA['definitions'] if d['room_type']==scope),'office')

NAV={}
for m in ROOM_DATA['maps'].values():
    NAV[id(m)]=({(p['x'],p['y']) for p in m['walkable_tiles']},{(o['x']+dx,o['y']+dy)for o in m['objects'] if o.get('blocking',True) for dx in range(o.get('width',1))for dy in range(o.get('height',1))})
def walkable(scope,x,y,world_map=None):
    m=world_map or map_for(scope)
    if not(math.isfinite(x) and math.isfinite(y) and -.49<=x<m['width']-.5 and -.49<=y<m['height']-.5):return False
    tile=(math.floor(x+.5),math.floor(y+.5))
    if id(m) in NAV:
        floor,blocked=NAV[id(m)];return tile in floor and tile not in blocked
    blocked={(o['x']+dx,o['y']+dy) for o in m['objects'] if o.get('blocking',True) for dx in range(o.get('width',1)) for dy in range(o.get('height',1))}
    return tile not in blocked and ('walkable_tiles' not in m or any(p['x']==tile[0] and p['y']==tile[1]for p in m['walkable_tiles']))

HEIGHT={(p['x'],p['y']):r['elevation'] for r in WORLD['surface']['regions'] for p in r.get('cells',[])}

def elevation(tile,surface):
    if surface is WORLD['surface']:return HEIGHT.get(tile,0)
    for r in surface.get('regions',[]):
        t=r['tiles']
        if (any(p['x']==tile[0] and p['y']==tile[1] for p in r['cells']) if 'cells' in r else t['x']<=tile[0]<t['x']+t['width'] and t['y']<=tile[1]<t['y']+t['height']):return r['elevation']
    return 0

def surface_crossing(before,after,surface):
    if elevation(before,surface)==elevation(after,surface):return True
    point=lambda p:(p['x'],p['y'])
    return any((before,after) in ((point(s['from']),point(s['to'])),(point(s['to']),point(s['from']))) for s in surface.get('stairs',[]))

def valid_move(scope,before,after,elapsed,world_map=None):
    x,y=after
    if not walkable(scope,x,y,world_map):return False
    d=math.hypot(x-before[0],y-before[1])
    if d>min(max(elapsed,0),.5)*4.5+.15:return False
    count=max(2,math.ceil(d/.08))
    surface=(world_map or map_for(scope)).get('surface',{})
    previous=(math.floor(before[0]+.5),math.floor(before[1]+.5))
    for i in range(1,count+1):
        px=before[0]+(x-before[0])*i/count;py=before[1]+(y-before[1])*i/count
        tile=(math.floor(px+.5),math.floor(py+.5))
        if not walkable(scope,px,py,world_map) or not surface_crossing(previous,tile,surface) or any(((a['x'],a['y']),(b['x'],b['y'])) in [(previous,tile),(tile,previous)] for a,b in (world_map or map_for(scope)).get('closed_edges',[])):return False
        previous=tile
    return True
