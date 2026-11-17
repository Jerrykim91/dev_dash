"""Owner-only homes, authoritative placements and atomic/idempotent shop transactions."""
import copy
import json
import math
import uuid
from collections import deque
from .world import SHARED, PERSONAL

CATALOG=json.loads((SHARED/'furniture-catalog.json').read_text())
CATALOG_BY_ID={i['item_id']:i for i in CATALOG}
EXIT={'id':'home-exit','kind':'door','label':'오피스로 나가기','x':10,'y':8,'interaction':{'kind':'home_exit'}}
ENTRY=(10,7)
MAX_PLACEMENTS=70

class HomeError(Exception):
    def __init__(self,message,status=422):self.message=message;self.status=status

def footprint(item,x,y,rotation):
    w,h=item['size']['width'],item['size']['height']
    if rotation in (90,270):w,h=h,w
    return {(x+dx,y+dy) for dx in range(w) for dy in range(h)}

def validate_layout(placements,instances,player=None):
    """Pure grid validation; assets are never consulted for collision."""
    occupied={(EXIT['x'],EXIT['y'])};blocked=set(occupied);seen=set();solids=[]
    if len(placements)>MAX_PLACEMENTS:raise HomeError('한 집에는 최대 70개까지 배치할 수 있어요.')
    for p in placements:
        iid=p['instance_id'];item=instances.get(iid)
        if not item:raise HomeError('내가 보유한 가구만 배치할 수 있어요.',403)
        if iid in seen:raise HomeError('같은 가구를 중복 설치할 수 없어요.')
        seen.add(iid)
        rotation=p['rotation']
        if rotation not in (0,90,180,270) or (rotation and not item['rotatable']):raise HomeError('가구 방향이 올바르지 않아요.')
        cells=footprint(item,p['grid_x'],p['grid_y'],rotation)
        if any(x<0 or y<0 or x>=PERSONAL['width'] or y>=PERSONAL['height'] for x,y in cells):raise HomeError('벽 밖에는 배치할 수 없어요.')
        if cells&occupied:raise HomeError('가구 또는 출입문과 겹쳐요.')
        if ENTRY in cells or (PERSONAL['spawn']['x'],PERSONAL['spawn']['y']) in cells:raise HomeError('입구와 기본 이동 위치를 비워 주세요.')
        occupied|=cells
        if item['blocking']:
            blocked|=cells;solids.append(cells)
            if player and (math.floor(player[0]+.5),math.floor(player[1]+.5)) in cells:raise HomeError('캐릭터가 있는 칸에는 배치할 수 없어요.')
    free={(x,y) for x in range(PERSONAL['width']) for y in range(PERSONAL['height'])}-blocked
    reached={ENTRY};queue=deque([ENTRY])
    while queue:
        x,y=queue.popleft()
        for t in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if t in free and t not in reached:reached.add(t);queue.append(t)
    if reached!=free:raise HomeError('모든 바닥과 입구로 이어지는 통로를 확보해 주세요.')
    for cells in solids:
        if not any((x+dx,y+dy) in reached for x,y in cells for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))):raise HomeError('가구에 접근할 수 있는 통로가 필요해요.')
    return blocked

def interaction(category):
    if category=='computer':return {'kind':'dashboard'}
    action={'chair':'sitting','sofa':'resting','bed':'resting','desk':'working'}.get(category)
    if action:return {'kind':'action','action':action,'toggle':True,'message':{'sitting':'의자에 앉았어요.','working':'작업 중이에요.','resting':'편안하게 쉬는 중이에요.'}[action]}
    return {'kind':'action','action':'idle','message':'나의 가구예요. 꾸미기 모드에서 이동하거나 회수할 수 있어요.'}

class HomeService:
    def __init__(self,repo,initial_coins=1000):self.repo=repo;self.initial_coins=initial_coins;self.maps={}
    def initialize(self):
        with self.repo.connect() as c:
            for item in CATALOG:c.execute('INSERT INTO furniture_catalog(item_id,data) VALUES (?,?) ON CONFLICT(item_id) DO UPDATE SET data=excluded.data',(item['item_id'],json.dumps(item,ensure_ascii=False)))
    def ensure(self,uid):
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO personal_homes(id,owner_id) VALUES (?,?)',(f'personal:{uid}',uid))
            if c.execute('SELECT 1 FROM user_wallets WHERE user_id=?',(uid,)).fetchone():return
            c.execute('INSERT INTO user_wallets(user_id,balance) VALUES (?,?)',(uid,self.initial_coins))
            c.execute("INSERT INTO coin_transactions(id,user_id,amount,balance_after,kind) VALUES (?,?,?,?,'initial_grant')",(str(uuid.uuid4()),uid,self.initial_coins,self.initial_coins))
            # Preserve the six Phase 2 starter positions; new instances have independent IDs.
            for o in PERSONAL['objects']:
                item=next((i for i in CATALOG if i['category']==o['kind']),None)
                if not item:continue
                iid=str(uuid.uuid4())
                c.execute('INSERT INTO furniture_instances(id,owner_id,item_id) VALUES (?,?,?)',(iid,uid,item['item_id']))
                c.execute('INSERT INTO furniture_placements(instance_id,room_id,grid_x,grid_y,rotation) VALUES (?,?,?,?,0)',(iid,f'personal:{uid}',o['x'],o['y']))
            # A desk and a rug are given uninstalled to make decorating usable immediately.
            for cat in ('desk','rug'):
                c.execute('INSERT INTO furniture_instances(id,owner_id,item_id) VALUES (?,?,?)',(str(uuid.uuid4()),uid,f'furniture_{cat}_001'))
    def require_home(self,uid,room_id):
        if room_id!=f'personal:{uid}':raise HomeError('내 집만 조회하거나 편집할 수 있어요.',403)
    def state(self,uid):
        self.ensure(uid)
        with self.repo.connect() as c:
            c.execute('BEGIN')
            home=dict(c.execute('SELECT * FROM personal_homes WHERE owner_id=?',(uid,)).fetchone())
            inventory=[dict(r) for r in c.execute('SELECT * FROM furniture_instances WHERE owner_id=? ORDER BY acquired_at,id',(uid,))]
            placements=[dict(r) for r in c.execute('SELECT * FROM furniture_placements WHERE room_id=? ORDER BY instance_id',(home['id'],))]
            balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(uid,)).fetchone()[0]
            transactions=[dict(r) for r in c.execute('SELECT * FROM coin_transactions WHERE user_id=? ORDER BY rowid DESC LIMIT 100',(uid,))]
        return {'home':home,'catalog':CATALOG,'inventory':inventory,'placements':placements,'balance':balance,'transactions':transactions,'map':self.render_map(placements,inventory)}
    def render_map(self,placements,inventory):
        by_id={i['id']:i for i in inventory};objects=[]
        for p in placements:
            item=CATALOG_BY_ID[by_id[p['instance_id']]['item_id']]
            w,h=item['size']['width'],item['size']['height']
            if p['rotation'] in (90,270):w,h=h,w
            objects.append({'id':p['instance_id'],'instance_id':p['instance_id'],'kind':item['asset_key'],'label':item['name'],'x':p['grid_x'],'y':p['grid_y'],'width':w,'height':h,'rotation':p['rotation'],'blocking':item['blocking'],'interaction':interaction(item['category'])})
        return {**copy.deepcopy(PERSONAL),'objects':objects+[EXIT]}
    def map_for(self,uid):
        if uid not in self.maps:self.maps[uid]=self.state(uid)['map']
        return self.maps[uid]
    def save(self,uid,room_id,revision,placements,player=None):
        self.require_home(uid,room_id);self.ensure(uid)
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            current=c.execute('SELECT revision FROM personal_homes WHERE id=? AND owner_id=?',(room_id,uid)).fetchone()[0]
            if revision!=current:raise HomeError('다른 화면에서 집이 변경됐어요. 최신 배치를 다시 불러오세요.',409)
            instances={r['id']:CATALOG_BY_ID[r['item_id']] for r in c.execute('SELECT id,item_id FROM furniture_instances WHERE owner_id=?',(uid,))}
            validate_layout(placements,instances,player)
            c.execute('DELETE FROM furniture_placements WHERE room_id=?',(room_id,))
            for p in placements:c.execute('INSERT INTO furniture_placements VALUES (?,?,?,?,?)',(p['instance_id'],room_id,p['grid_x'],p['grid_y'],p['rotation']))
            c.execute('UPDATE personal_homes SET revision=revision+1 WHERE id=?',(room_id,))
        self.maps.pop(uid,None)
        return self.state(uid)
    def purchase(self,uid,item_id,request_id):
        self.ensure(uid)
        item=CATALOG_BY_ID.get(item_id)
        if not item:raise HomeError('판매 중인 가구가 아니에요.',404)
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM shop_purchases WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
            if old:
                if old['item_id']!=item_id:raise HomeError('동일한 요청 번호로 다른 상품을 구매할 수 없어요.',409)
                receipt=dict(old);replayed=True
            else:
                cursor=c.execute('UPDATE user_wallets SET balance=balance-? WHERE user_id=? AND balance>=?',(item['price'],uid,item['price']))
                if not cursor.rowcount:raise HomeError('NOBIS Coin 잔액이 부족해요.',409)
                balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(uid,)).fetchone()[0]
                iid=str(uuid.uuid4());pid=str(uuid.uuid4())
                c.execute('INSERT INTO furniture_instances(id,owner_id,item_id) VALUES (?,?,?)',(iid,uid,item_id))
                c.execute('INSERT INTO shop_purchases(id,user_id,request_id,item_id,instance_id,price) VALUES (?,?,?,?,?,?)',(pid,uid,request_id,item_id,iid,item['price']))
                c.execute("INSERT INTO coin_transactions(id,user_id,amount,balance_after,kind,purchase_id) VALUES (?,?,?,?,'purchase',?)",(str(uuid.uuid4()),uid,-item['price'],balance,pid))
                receipt=dict(c.execute('SELECT * FROM shop_purchases WHERE id=?',(pid,)).fetchone());replayed=False
        return {'receipt':receipt,'replayed':replayed,'state':self.state(uid)}
