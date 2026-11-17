import json,secrets,time,uuid,re,math
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from ..home import CATALOG_BY_ID


class CollectibleError(Exception):
 def __init__(self,message,status=422):self.message=message;self.status=status

def normal_coin_pool():
 # Symmetric largest-remainder rounding preserves mean 505 and exactly 10000 bps.
 amounts=list(range(10,1001,10));raw=[math.exp(-0.5*((a-505)/165)**2) for a in amounts]
 total=sum(raw);half=[max(1,math.floor(w/total*10000)) for w in raw[:50]]
 remaining=(10000-2*sum(half))//2
 order=sorted(range(50),key=lambda i:(-(raw[i]/total*10000-half[i]),i))
 for i in order[:remaining]:half[i]+=1
 weights=half+list(reversed(half))
 return [{'coin_amount':a,'weight_bps':w} for a,w in zip(amounts,weights)]

COIN_POOL=normal_coin_pool()
def validate_pool(data):
 items=data['items'];weights=data['rarity_weights']
 if weights!={'coin':10000}:raise CollectibleError('코인 확률 합계는 100%여야 합니다.')
 if not 1<=len(items)<=100 or any(type(i.get('coin_amount'))!=int or not 10<=i['coin_amount']<=1000 or i['coin_amount']%10 or type(i.get('weight_bps'))!=int or not 1<=i['weight_bps']<=10000 for i in items):raise CollectibleError('보상은 10~1,000코인, 10코인 단위이며 확률은 양수여야 합니다.')
 if len({i['coin_amount'] for i in items})!=len(items) or sum(i['weight_bps'] for i in items)!=10000:raise CollectibleError('중복 없는 코인 금액의 확률 합계가 정확히 100%여야 합니다.')
 return data

def coin_item(i):return {**dict(i),'item_id':'coin_'+str(i['coin_amount']),'name':f"{i['coin_amount']:,} Coin",'rarity':'coin'}

class CollectibleService:
 def __init__(self,repo,homes,social,clock=None):self.repo=repo;self.homes=homes;self.social=social;self.clock=clock or time.time
 def initialize(self):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   # Retain all old furniture versions/receipts, but stop offering furniture draws.
   c.execute('UPDATE gacha_banners SET enabled=0 WHERE NOT EXISTS (SELECT 1 FROM gacha_coin_pool_items p WHERE p.banner_id=gacha_banners.id AND p.version=gacha_banners.current_version)')
   if not c.execute("SELECT 1 FROM gacha_banners WHERE id='daily-coins'").fetchone():self._banner(c,'daily-coins',{'name':'NOBIS Coin 뽑기','description':'무료 출석 티켓으로 10~1,000코인을 받아요. 기본 확률은 평균 505, 표준편차 165의 정규분포 형태입니다.','enabled':True,'rarity_weights':{'coin':10000},'items':COIN_POOL},None)
 def ensure(self,c,uid):c.execute('INSERT OR IGNORE INTO ticket_balances(user_id) VALUES (?)',(uid,))
 def today(self):return datetime.fromtimestamp(self.clock(),ZoneInfo('Asia/Seoul')).date()
 def status(self,uid,month=None):
  today=self.today();month=month or today.isoformat()[:7]
  if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):raise CollectibleError('달력 연월은 YYYY-MM 형식입니다.')
  try:datetime.strptime(month,'%Y-%m')
  except ValueError:raise CollectibleError('달력의 연월을 확인해 주세요.')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.ensure(c,uid)
   rows=[dict(r) for r in c.execute('SELECT * FROM daily_attendance WHERE user_id=? AND attendance_date LIKE ? ORDER BY attendance_date',(uid,month+'%'))]
   latest=c.execute('SELECT * FROM daily_attendance WHERE user_id=? ORDER BY attendance_date DESC LIMIT 1',(uid,)).fetchone();total=c.execute('SELECT COUNT(*) FROM daily_attendance WHERE user_id=?',(uid,)).fetchone()[0];reward=c.execute("SELECT reward_tickets FROM attendance_settings WHERE id='default'").fetchone()[0];balance=c.execute('SELECT balance FROM ticket_balances WHERE user_id=?',(uid,)).fetchone()[0]
   coin_balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(uid,)).fetchone();earned=c.execute("SELECT COALESCE(SUM(amount),0) FROM coin_transactions WHERE user_id=? AND kind='gacha_reward'",(uid,)).fetchone()[0]
  return {'coin_balance':coin_balance[0] if coin_balance else 0,'total_earned_coins':earned,'today':today.isoformat(),'month':month,'timezone':'Asia/Seoul','claimed_today':bool(latest and latest['attendance_date']==today.isoformat()),'balance':balance,'streak':latest['streak'] if latest and latest['attendance_date'] in (today.isoformat(),(today-timedelta(days=1)).isoformat()) else 0,'total_days':total,'reward_tickets':reward,'calendar':rows}
 def claim(self,uid):
  today=self.today();now=self.clock()
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.ensure(c,uid);old=c.execute('SELECT * FROM daily_attendance WHERE user_id=? AND attendance_date=?',(uid,today.isoformat())).fetchone();replayed=bool(old)
   if not old:
    last=c.execute('SELECT * FROM daily_attendance WHERE user_id=? ORDER BY attendance_date DESC LIMIT 1',(uid,)).fetchone();streak=last['streak']+1 if last and last['attendance_date']==(today-timedelta(days=1)).isoformat() else 1
    if last and last['attendance_date']>today.isoformat():raise CollectibleError('서버 날짜를 확인한 뒤 다시 시도해 주세요.',409)
    reward=c.execute("SELECT reward_tickets FROM attendance_settings WHERE id='default'").fetchone()[0];aid=str(uuid.uuid4());c.execute('INSERT INTO daily_attendance VALUES (?,?,?,?,?,?)',(aid,uid,today.isoformat(),streak,reward,now));c.execute('UPDATE ticket_balances SET balance=balance+? WHERE user_id=?',(reward,uid));balance=c.execute('SELECT balance FROM ticket_balances WHERE user_id=?',(uid,)).fetchone()[0]
    c.execute("INSERT INTO ticket_transactions VALUES (?,?,?,?,'attendance',?,NULL,?,NULL,?)",(str(uuid.uuid4()),uid,reward,balance,aid,'attendance:'+today.isoformat(),now));self.social.audit(c,uid,'attendance_ticket_issued',aid,{'date':today.isoformat(),'tickets':reward})
  return {'replayed':replayed,'state':self.status(uid)}
 def banners(self,include_disabled=False):
  with self.repo.connect() as c:
   result=[]
   for r in c.execute('SELECT * FROM gacha_banners ORDER BY created_at,id'):
    if not include_disabled and not r['enabled']:continue
    d=dict(r);v=c.execute('SELECT * FROM gacha_pool_versions WHERE banner_id=? AND version=?',(r['id'],r['current_version'])).fetchone();d['rarity_weights']=json.loads(v['rarity_weights'])
    coins=[coin_item(i) for i in c.execute('SELECT * FROM gacha_coin_pool_items WHERE banner_id=? AND version=? ORDER BY coin_amount',(r['id'],r['current_version']))]
    d['reward_type']='coin' if coins else 'furniture'
    d['items']=coins or [{**dict(i),'name':CATALOG_BY_ID[i['item_id']]['name'],'size':CATALOG_BY_ID[i['item_id']]['size'],'asset_key':CATALOG_BY_ID[i['item_id']]['asset_key']} for i in c.execute('SELECT * FROM gacha_pool_items WHERE banner_id=? AND version=? ORDER BY rarity,item_id',(r['id'],r['current_version']))]
    if coins:
     mean=sum(i['coin_amount']*i['weight_bps'] for i in coins)/10000
     d['expected_coins']=mean;d['standard_deviation']=math.sqrt(sum((i['coin_amount']-mean)**2*i['weight_bps'] for i in coins)/10000)
    result.append(d)
  return result
 def draw(self,uid,banner_id,count,request_id,expected_version=None):
  self.homes.ensure(uid);failure=None
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.ensure(c,uid);old=c.execute('SELECT * FROM gacha_draws WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
   if old:
    if old['banner_id']!=banner_id or old['tickets_used']!=count or expected_version is not None and old['pool_version']!=expected_version:raise CollectibleError('동일한 요청 번호를 다른 뽑기에 사용할 수 없습니다.',409)
    did=old['id'];replayed=True
   else:
    b=c.execute('SELECT * FROM gacha_banners WHERE id=? AND enabled=1',(banner_id,)).fetchone()
    if not b:raise CollectibleError('현재 이용 가능한 배너가 아닙니다.',404)
    if expected_version is not None and b['current_version']!=expected_version:raise CollectibleError('확률표가 변경됐습니다. 최신 확률을 확인한 뒤 다시 선택해 주세요.',409)
    pool=[dict(i) for i in c.execute('SELECT * FROM gacha_coin_pool_items WHERE banner_id=? AND version=? ORDER BY coin_amount',(banner_id,b['current_version']))]
    version=c.execute('SELECT rarity_weights FROM gacha_pool_versions WHERE banner_id=? AND version=?',(banner_id,b['current_version'])).fetchone();validate_pool({'rarity_weights':json.loads(version['rarity_weights']),'items':pool})
    if not c.execute('UPDATE ticket_balances SET balance=balance-? WHERE user_id=? AND balance>=?',(count,uid,count)).rowcount:failure='insufficient_tickets'
    else:
     did=str(uuid.uuid4());now=self.clock();c.execute('INSERT INTO gacha_draws VALUES (?,?,?,?,?,?,?)',(did,uid,banner_id,b['current_version'],count,request_id,now))
     for position in range(count):
      pick=secrets.randbelow(10000);acc=0
      for item in pool:
       acc+=item['weight_bps']
       if pick<acc:break
      txid=str(uuid.uuid4());c.execute('UPDATE user_wallets SET balance=balance+? WHERE user_id=?',(item['coin_amount'],uid));coin_balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(uid,)).fetchone()[0]
      c.execute("INSERT INTO coin_transactions(id,user_id,amount,balance_after,kind) VALUES (?,?,?,?,'gacha_reward')",(txid,uid,item['coin_amount'],coin_balance));c.execute('INSERT INTO gacha_coin_draw_items VALUES (?,?,?,?)',(did,position,item['coin_amount'],txid))
     balance=c.execute('SELECT balance FROM ticket_balances WHERE user_id=?',(uid,)).fetchone()[0];c.execute("INSERT INTO ticket_transactions VALUES (?,?,?,?,'draw',NULL,?,?,NULL,?)",(str(uuid.uuid4()),uid,-count,balance,did,'draw:'+request_id,now));self.social.audit(c,uid,'gacha_draw_completed',did,{'banner_id':banner_id,'version':b['current_version'],'count':count});replayed=False
     if hasattr(self,'community'):self.community._notify(c,uid,uid,'gacha_coin','코인 뽑기 보상이 지갑에 지급됐습니다.',ref=did)
  if failure:
   with self.repo.connect() as c:
    now=self.clock()
    if not c.execute('SELECT 1 FROM collectible_alerts WHERE user_id=? AND kind=? AND created_at>?',(uid,failure,now-30)).fetchone():c.execute('INSERT INTO collectible_alerts VALUES (?,?,?,?)',(str(uuid.uuid4()),uid,failure,now))
   raise CollectibleError('티켓이 부족합니다. 무료 출석 보상을 확인해 주세요.',409)
  return {'draw':self.receipt(uid,did),'replayed':replayed,'state':self.status(uid)}
 def receipt(self,uid,did):
  with self.repo.connect() as c:
   d=c.execute('SELECT d.*,b.name AS banner_name FROM gacha_draws d JOIN gacha_banners b ON b.id=d.banner_id WHERE d.id=? AND d.user_id=?',(did,uid)).fetchone()
   if not d:raise CollectibleError('내 뽑기 기록을 찾을 수 없습니다.',404)
   coins=[coin_item(i) for i in c.execute('SELECT * FROM gacha_coin_draw_items WHERE draw_id=? ORDER BY position',(did,))]
   items=coins or [{**dict(i),'name':CATALOG_BY_ID[i['item_id']]['name'],'asset_key':CATALOG_BY_ID[i['item_id']]['asset_key'],'size':CATALOG_BY_ID[i['item_id']]['size']} for i in c.execute('SELECT * FROM gacha_draw_items WHERE draw_id=? ORDER BY position',(did,))]
   v=c.execute('SELECT rarity_weights FROM gacha_pool_versions WHERE banner_id=? AND version=?',(d['banner_id'],d['pool_version'])).fetchone()
   pool=[coin_item(i) for i in c.execute('SELECT coin_amount,weight_bps FROM gacha_coin_pool_items WHERE banner_id=? AND version=? ORDER BY coin_amount',(d['banner_id'],d['pool_version']))] if coins else [dict(i) for i in c.execute('SELECT item_id,rarity,weight_bps FROM gacha_pool_items WHERE banner_id=? AND version=? ORDER BY item_id',(d['banner_id'],d['pool_version']))]
  return {**dict(d),'reward_type':'coin' if coins else 'furniture','total_coins':sum(i['coin_amount'] for i in coins),'items':items,'rarity_weights':json.loads(v['rarity_weights']),'probabilities':pool}
 def history(self,uid):
  with self.repo.connect() as c:
   ids=[r['id'] for r in c.execute('SELECT id FROM gacha_draws WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 30',(uid,))];tx=[dict(r) for r in c.execute('SELECT * FROM ticket_transactions WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 100',(uid,))]
  return {'draws':[self.receipt(uid,did) for did in ids],'transactions':tx}
 def _banner(self,c,bid,data,actor):
  validate_pool(data);old=c.execute('SELECT current_version FROM gacha_banners WHERE id=?',(bid,)).fetchone();version=old['current_version']+1 if old else 1;now=self.clock()
  if old:c.execute('UPDATE gacha_banners SET name=?,description=?,enabled=?,current_version=? WHERE id=?',(data['name'],data['description'],int(data['enabled']),version,bid))
  else:c.execute('INSERT INTO gacha_banners VALUES (?,?,?,?,?,?)',(bid,data['name'],data['description'],int(data['enabled']),version,now))
  c.execute('INSERT INTO gacha_pool_versions VALUES (?,?,?,?)',(bid,version,json.dumps(data['rarity_weights']),now))
  for item in data['items']:c.execute('INSERT INTO gacha_coin_pool_items VALUES (?,?,?,?)',(bid,version,item['coin_amount'],item['weight_bps']))
  if actor:self.social.audit(c,actor,'gacha_banner_changed',bid,{'name':data['name'],'version':version,'enabled':data['enabled']})
  return bid
 def configure_banner(self,actor,bid,data):
  self.social.require(actor,'collectibles_manage')
  with self.repo.connect() as c:c.execute('BEGIN IMMEDIATE');self._banner(c,bid,data,actor)
  return self.banners(True)
 def configure_attendance(self,actor,reward):
  self.social.require(actor,'collectibles_manage')
  with self.repo.connect() as c:c.execute('BEGIN IMMEDIATE');c.execute("UPDATE attendance_settings SET reward_tickets=? WHERE id='default'",(reward,));self.social.audit(c,actor,'attendance_reward_changed',details={'tickets':reward})
  return {'reward_tickets':reward}
 def grant(self,actor,uid,amount,request_id):
  self.social.require(actor,'collectibles_manage')
  if not self.repo.user_exists(uid):raise CollectibleError('사용자를 찾을 수 없습니다.',404)
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.ensure(c,uid);old=c.execute('SELECT amount FROM ticket_transactions WHERE user_id=? AND request_id=?',(uid,'grant:'+request_id)).fetchone()
   if old and old['amount']!=amount:raise CollectibleError('요청 번호를 재사용할 수 없습니다.',409)
   if not old:
    c.execute('UPDATE ticket_balances SET balance=balance+? WHERE user_id=?',(amount,uid));balance=c.execute('SELECT balance FROM ticket_balances WHERE user_id=?',(uid,)).fetchone()[0];c.execute("INSERT INTO ticket_transactions VALUES (?,?,?,?,'admin_grant',NULL,NULL,?,?,?)",(str(uuid.uuid4()),uid,amount,balance,'grant:'+request_id,actor,self.clock()));self.social.audit(c,actor,'tickets_granted',uid,{'tickets':amount,'request_id':request_id})
  return self.status(uid)
 def admin(self,actor):
  self.social.require(actor,'collectibles_read')
  with self.repo.connect() as c:
   reward=c.execute("SELECT reward_tickets FROM attendance_settings WHERE id='default'").fetchone()[0];tx=[dict(r) for r in c.execute('SELECT t.*,u.nickname FROM ticket_transactions t JOIN users u ON u.id=t.user_id ORDER BY t.created_at DESC,t.id DESC LIMIT 100')];stats=[dict(r) for r in c.execute('SELECT coin_amount,COUNT(*) AS count FROM gacha_coin_draw_items GROUP BY coin_amount ORDER BY coin_amount')];alerts=[dict(r) for r in c.execute('SELECT a.*,u.nickname FROM collectible_alerts a JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT 100')]
  return {'banners':self.banners(True),'reward_tickets':reward,'transactions':tx,'statistics':stats,'alerts':alerts,'default_coin_pool':COIN_POOL}
