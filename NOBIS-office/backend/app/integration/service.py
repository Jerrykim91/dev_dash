import json,time,uuid,secrets,os
from datetime import datetime,timezone
from ..community.service import CommunityError
from ..home import CATALOG

def ident():return str(uuid.uuid4())
class IntegrationService:
 def __init__(self,repo,homes,social,community,games,hub,clock=None):self.repo,self.homes,self.social,self.community,self.games,self.hub=repo,homes,social,community,games,hub;self.clock=clock or time.time
 def initialize(self):
  if not 1<=int(os.getenv('HOME_MAX_OCCUPANTS','5'))<=5:raise RuntimeError('HOME_MAX_OCCUPANTS must be between 1 and 5')
  with self.repo.connect() as c:
   c.execute('UPDATE home_visitors SET connected=0');c.execute('UPDATE multiplayer_game_participants SET disconnected_at=? WHERE active=1 AND disconnected_at IS NULL',(self.clock(),))
 def settings(self,c,owner):
  self.community.user(c,owner);c.execute('INSERT OR IGNORE INTO home_visit_settings(owner_id,capacity) VALUES (?,?)',(owner,min(5,max(1,int(os.getenv('HOME_MAX_OCCUPANTS','5'))))))
  return dict(c.execute('SELECT * FROM home_visit_settings WHERE owner_id=?',(owner,)).fetchone())
 def allowed(self,c,who,owner):
  if who==owner:return True
  s=self.settings(c,owner)
  if self.community.blocked(c,who,owner) or s['access']=='private':return False
  if s['access']=='friends' and not self.community.relation(c,who,owner)['friends']:return False
  return bool(c.execute('SELECT 1 FROM home_visit_permissions WHERE owner_id=? AND visitor_id=? AND expires_at>?',(owner,who,self.clock())).fetchone())
 def note(self,c,to,actor,kind,message,reference=None):self.community._notify(c,to,actor,kind,message,ref=reference)
 def home_panel(self,who):
  with self.repo.connect() as c:
   setting=self.settings(c,who);incoming=[dict(r) for r in c.execute("SELECT r.*,u.nickname FROM home_visit_requests r JOIN users u ON u.id=r.visitor_id WHERE owner_id=? AND status='pending' ORDER BY created_at DESC",(who,))]
   outgoing=[{**dict(r),'can_enter':self.allowed(c,who,r['owner_id'])} for r in c.execute("SELECT r.*,u.nickname FROM home_visit_requests r JOIN users u ON u.id=r.owner_id WHERE visitor_id=? AND status IN ('pending','accepted') ORDER BY created_at DESC LIMIT 30",(who,))]
   visitors=[{'user_id':p.player['id'],'nickname':p.player['nickname']} for p in self.hub.peers.values() if p.player['scope']=='personal:'+who and p.player['id']!=who]
  return {'settings':setting,'incoming':incoming,'outgoing':outgoing,'visitors':visitors}
 def configure_home(self,who,access,capacity):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.settings(c,who);c.execute('UPDATE home_visit_settings SET access=?,capacity=? WHERE owner_id=?',(access,capacity,who));self.social.audit(c,who,'home_access_changed',who,{'access':access,'capacity':capacity})
  return self.home_panel(who)
 def request_visit(self,who,owner):
  if who==owner:raise CommunityError('내 집은 기존 입구를 이용하세요.')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');s=self.settings(c,owner)
   if self.community.blocked(c,who,owner) or s['access']=='private' or s['access']=='friends' and not self.community.relation(c,who,owner)['friends']:raise CommunityError('방문 요청이 허용되지 않는 집입니다.',403)
   if self.allowed(c,who,owner):return {'approved':True}
   old=c.execute("SELECT id FROM home_visit_requests WHERE owner_id=? AND visitor_id=? AND status='pending'",(owner,who)).fetchone()
   if old:return {'request_id':old['id']}
   rid=ident();c.execute("INSERT INTO home_visit_requests VALUES (?,?,?,'pending',?)",(rid,owner,who,self.clock()));self.note(c,owner,who,'home_request','친구 집 방문 요청이 있습니다.',rid)
  return {'request_id':rid}
 def decide_visit(self,who,rid,accept):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM home_visit_requests WHERE id=? AND owner_id=?',(rid,who)).fetchone()
   if not r:raise CommunityError('내 집 방문 요청이 아닙니다.',404)
   if r['status']!='pending':return {'ok':True}
   s=self.settings(c,who)
   if accept and (s['access']=='private' or self.community.blocked(c,who,r['visitor_id']) or s['access']=='friends' and not self.community.relation(c,who,r['visitor_id'])['friends']):raise CommunityError('공개 설정과 친구 관계를 확인하세요.',403)
   c.execute('UPDATE home_visit_requests SET status=? WHERE id=?',('accepted' if accept else 'rejected',rid))
   if accept:c.execute('INSERT INTO home_visit_permissions VALUES (?,?,?) ON CONFLICT(owner_id,visitor_id) DO UPDATE SET expires_at=excluded.expires_at',(who,r['visitor_id'],self.clock()+86400))
   self.note(c,r['visitor_id'],who,'home_approved' if accept else 'home_rejected','집 방문이 승인됐습니다.' if accept else '집 방문 요청이 거절됐습니다.',rid)
  return self.home_panel(who)
 def revoke(self,owner,visitor):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM home_visit_permissions WHERE owner_id=? AND visitor_id=?',(owner,visitor));c.execute("UPDATE home_visit_requests SET status='cancelled' WHERE owner_id=? AND visitor_id=? AND status IN ('pending','accepted')",(owner,visitor));self.social.audit(c,owner,'home_visitor_revoked',visitor)
 def may_enter(self,who,owner):
  with self.repo.connect() as c:
   if not self.allowed(c,who,owner):raise CommunityError('집 방문 권한이 없습니다.',403)
   cap=self.settings(c,owner)['capacity']
   if sum(p.player['scope']=='personal:'+owner and p.player['id']!=who for p in self.hub.peers.values())>=cap:raise CommunityError('집 방문 정원이 찼습니다.',409)
  self.homes.ensure(owner)
  return self.homes.map_for(owner)
 def mark_home(self,who,owner=None):
  with self.repo.connect() as c:
   if owner:c.execute('INSERT INTO home_visitors VALUES (?,?,1,?) ON CONFLICT(user_id) DO UPDATE SET owner_id=excluded.owner_id,connected=1,updated_at=excluded.updated_at',(who,owner,self.clock()))
   else:c.execute('DELETE FROM home_visitors WHERE user_id=?',(who,))
 def reserved(self,c,who):
  self.expire(c)
  return c.execute('SELECT s.* FROM multiplayer_game_participants p JOIN multiplayer_game_sessions s ON s.id=p.session_id WHERE p.user_id=? AND p.active=1',(who,)).fetchone()
 def active(self,who):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');s=self.reserved(c,who);return dict(s) if s and s['status']=='active' else None
 def expire(self,c):
  now=self.clock()
  rows=c.execute("SELECT s.id,s.expires_at FROM multiplayer_game_sessions s WHERE s.status IN ('pending','active') AND (s.expires_at<=? OR EXISTS(SELECT 1 FROM multiplayer_game_participants p WHERE p.session_id=s.id AND p.disconnected_at IS NOT NULL AND p.disconnected_at<=?))",(now,now-30)).fetchall()
  for s in rows:self.end(c,s['id'],'expired' if s['expires_at']<=now else 'disconnected')
 def end(self,c,sid,status):
  c.execute('UPDATE multiplayer_game_sessions SET status=?,finished_at=? WHERE id=?',(status,self.clock(),sid));c.execute('UPDATE multiplayer_game_participants SET active=0 WHERE session_id=?',(sid,))
  for p in c.execute('SELECT user_id FROM multiplayer_game_participants WHERE session_id=?',(sid,)):
   self.note(c,p['user_id'],p['user_id'],'multiplayer_result','협동 카드 게임 결과가 저장됐습니다.',sid)
 def owned(self,c,who,sid):
  s=c.execute('SELECT s.* FROM multiplayer_game_sessions s JOIN multiplayer_game_participants p ON p.session_id=s.id WHERE s.id=? AND p.user_id=?',(sid,who)).fetchone()
  if not s:raise CommunityError('참가한 게임이 아닙니다.',404)
  return dict(s)
 def invite_game(self,who,target,key):
  if who==target:raise CommunityError('친구를 선택하세요.')
  self.homes.ensure(who);self.homes.ensure(target)
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM multiplayer_game_sessions WHERE host_user_id=? AND request_id=?',(who,key)).fetchone()
   if old:
    if old['invited_user_id']!=target:raise CommunityError('요청 번호를 재사용할 수 없습니다.',409)
    return self.game_state(who,old['id'],c)
   if self.community.blocked(c,who,target) or not self.community.relation(c,who,target)['friends']:raise CommunityError('차단되지 않은 친구만 초대할 수 있습니다.',403)
   self.games._expire(c,who,self.games.clock());self.games._expire(c,target,self.games.clock())
   if self.reserved(c,who) or self.reserved(c,target) or c.execute("SELECT 1 FROM game_sessions WHERE user_id IN (?,?) AND status='active'",(who,target)).fetchone():raise CommunityError('참가 중인 게임을 먼저 종료하세요.',409)
   board=list(range(6))*2;secrets.SystemRandom().shuffle(board);sid=ident();now=self.clock()
   c.execute("INSERT INTO multiplayer_game_sessions(id,host_user_id,invited_user_id,request_id,status,board,turn_user_id,created_at,expires_at) VALUES (?,?,?,?,'pending',?,?,?,?)",(sid,who,target,key,json.dumps(board),who,now,now+60))
   for u in (who,target):c.execute('INSERT INTO multiplayer_game_participants(session_id,user_id) VALUES (?,?)',(sid,u))
   self.note(c,target,who,'multiplayer_invite','친구가 협동 카드 게임에 초대했습니다.',sid)
   return self.game_state(who,sid,c)
 def game_state(self,who,sid,c=None):
  if c is None:
   with self.repo.connect() as db:db.execute('BEGIN IMMEDIATE');self.expire(db);return self.game_state(who,sid,db)
  s=self.owned(c,who,sid);selected=json.loads(s['selected']);matched=json.loads(s['matched'])
  if len(selected)==2 and self.clock()>=s['reveal_until']:
   c.execute("UPDATE multiplayer_game_sessions SET selected='[]' WHERE id=?",(sid,));selected=[]
  board=json.loads(s['board']);cards=[v if i in matched or i in selected or s['status']=='completed' else None for i,v in enumerate(board)]
  rewards=[dict(r) for r in c.execute('SELECT r.user_id,ct.amount,r.reason FROM multiplayer_game_rewards r JOIN coin_transactions ct ON ct.id=r.coin_transaction_id WHERE session_id=?',(sid,))]
  return {k:s[k] for k in ('id','host_user_id','invited_user_id','status','turn_user_id','revision','created_at','started_at','expires_at')}|{'game_id':'coop-memory','cards':cards,'matched':matched,'selected':selected,'reveal_until':s['reveal_until'],'server_now':self.clock(),'pairs':len(matched)//2,'rewards':rewards}
 def accept_game(self,who,sid,accept):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.expire(c);s=self.owned(c,who,sid)
   if who!=s['invited_user_id']:raise CommunityError('초대받은 사람만 수락할 수 있습니다.',403)
   if s['status']=='pending':
    if not accept:self.end(c,sid,'cancelled')
    else:
     if self.community.blocked(c,who,s['host_user_id']) or not self.community.relation(c,who,s['host_user_id'])['friends']:raise CommunityError('차단되지 않은 친구 초대만 수락할 수 있습니다.',403)
     c.execute("UPDATE multiplayer_game_sessions SET status='active',started_at=?,expires_at=? WHERE id=?",(self.clock(),self.clock()+300,sid));c.execute('UPDATE multiplayer_game_participants SET disconnected_at=NULL WHERE session_id=?',(sid,));self.note(c,s['host_user_id'],who,'multiplayer_accepted','협동 카드 게임 초대가 수락됐습니다.',sid)
   return self.game_state(who,sid,c)
 def choose(self,who,sid,card,revision,key):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.expire(c);s=self.owned(c,who,sid)
   old=c.execute('SELECT * FROM multiplayer_game_actions WHERE session_id=? AND event_id=?',(sid,key)).fetchone()
   if old:
    if old['user_id']!=who or old['card']!=card or old['revision']!=revision:raise CommunityError('다른 입력에 같은 번호를 사용할 수 없습니다.',409)
    return self.game_state(who,sid,c)
   current=self.game_state(who,sid,c);selected=current['selected'];matched=current['matched']
   if s['status']!='active' or s['turn_user_id']!=who or revision!=s['revision'] or card in selected or card in matched or len(selected)>=2:
    raise CommunityError('현재 차례·최신 화면·선택 가능한 카드를 확인하세요.',409)
   board=json.loads(s['board']);selected.append(card);turn=who;until=0
   if len(selected)==2:
    if board[selected[0]]==board[selected[1]]:matched+=selected
    until=self.clock()+1.2;turn=s['invited_user_id'] if who==s['host_user_id'] else s['host_user_id']
   c.execute('INSERT INTO multiplayer_game_actions VALUES (?,?,?,?,?,?)',(sid,key,who,card,revision,self.clock()));c.execute('UPDATE multiplayer_game_sessions SET selected=?,matched=?,turn_user_id=?,revision=revision+1,reveal_until=? WHERE id=?',(json.dumps(selected),json.dumps(matched),turn,until,sid))
   if len(matched)==12:
    self.end(c,sid,'completed');self.pay(c,sid,s)
   return self.game_state(who,sid,c)
 def pay(self,c,sid,s):
  day=datetime.fromtimestamp(self.clock(),timezone.utc).date().isoformat()
  for who in (s['host_user_id'],s['invited_user_id']):
   if c.execute('SELECT 1 FROM multiplayer_game_rewards WHERE session_id=? AND user_id=?',(sid,who)).fetchone():continue
   earned=c.execute("SELECT COALESCE(SUM(ct.amount),0) FROM multiplayer_game_rewards r JOIN coin_transactions ct ON ct.id=r.coin_transaction_id WHERE r.user_id=? AND reward_date=?",(who,day)).fetchone()[0]
   solo=c.execute('SELECT COALESCE(SUM(ct.amount),0) FROM game_reward_transactions r JOIN coin_transactions ct ON ct.id=r.coin_transaction_id WHERE ct.user_id=? AND reward_date=?',(who,day)).fetchone()[0]
   reward=min(25,max(0,100-earned),max(0,300-earned-solo)) if self.clock()-(s['started_at'] or self.clock())>=10 else 0
   c.execute('UPDATE user_wallets SET balance=balance+? WHERE user_id=?',(reward,who));balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(who,)).fetchone()[0];tid=ident()
   c.execute("INSERT INTO coin_transactions(id,user_id,amount,balance_after,kind) VALUES (?,?,?,?,'minigame_reward')",(tid,who,reward,balance));c.execute('INSERT INTO multiplayer_game_rewards VALUES (?,?,?,?,?)',(sid,who,tid,day,'completed' if reward else 'cap_or_minimum_playtime'));self.social.audit(c,who,'multiplayer_reward_paid',sid,{'coins':reward})
 def cancel_game(self,who,sid):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');s=self.owned(c,who,sid)
   if s['status'] in ('pending','active'):self.end(c,sid,'cancelled')
   return self.game_state(who,sid,c)
 def panel(self,who):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.expire(c)
   ids=[r['session_id'] for r in c.execute('SELECT session_id FROM multiplayer_game_participants WHERE user_id=? ORDER BY session_id DESC',(who,))]
   states=[self.game_state(who,sid,c) for sid in ids];states.sort(key=lambda s:s['created_at'],reverse=True)
   return {'current':next((s for s in states if s['status'] in ('pending','active')),None),'history':states[:30]}
 def connection(self,who,online):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.expire(c);c.execute('UPDATE multiplayer_game_participants SET disconnected_at=? WHERE user_id=? AND active=1',(None if online else self.clock(),who))
   if not online:c.execute('UPDATE home_visitors SET connected=0,updated_at=? WHERE user_id=?',(self.clock(),who))
 def collections(self,who):
  self.homes.ensure(who)
  with self.repo.connect() as c:
   entries=[]
   for item in CATALOG:
    instances=[dict(r) for r in c.execute('SELECT * FROM furniture_instances WHERE owner_id=? AND item_id=? ORDER BY acquired_at,id',(who,item['item_id']))]
    bought=c.execute('SELECT COUNT(*) FROM shop_purchases WHERE user_id=? AND item_id=?',(who,item['item_id'])).fetchone()[0]
    installed=c.execute('SELECT COUNT(*) FROM furniture_placements p JOIN furniture_instances i ON i.id=p.instance_id WHERE i.owner_id=? AND i.item_id=?',(who,item['item_id'])).fetchone()[0]
    entries.append({**item,'quantity':len(instances),'installed':installed,'first_acquired':instances[0]['acquired_at'] if instances else None,'sources':(['상점 구매'] if bought else [])+(['기본 지급 또는 이전 보유'] if len(instances)>bought else [])})
   return {'entries':entries,'owned_types':sum(i['quantity']>0 for i in entries),'total_types':len(entries)}
 def share_preview(self,who,kind,target=None):
  if kind=='collection':
   d=self.collections(who);return f"직접 공유한 가구 도감 · {d['owned_types']}/{d['total_types']}종 보유"
  if kind=='furniture':
   e=next((e for e in self.collections(who)['entries'] if e['item_id']==target and e['quantity']>0),None)
   if not e:raise CommunityError('보유한 가구만 공유할 수 있습니다.',403)
   return f"직접 공유한 가구 · {e['name']} · 보유 {e['quantity']}개"
  if kind=='multiplayer':
   s=self.game_state(who,target)
   if s['status']!='completed':raise CommunityError('완료한 게임만 공유할 수 있습니다.')
   return f"협동 카드 짝 맞추기 · {s['pairs']}쌍 완료"
  row=next((r for r in self.games.history(who)['recent'] if r['session_id']==target),None)
  if not row:raise CommunityError('내 게임 결과만 공유할 수 있습니다.',403)
  return f"미니게임 기록 · {row['game_id']} · {row['score']}점"
 def admin(self,who):
  self.social.require(who,'games_read')
  with self.repo.connect() as c:
   return {'sessions':[dict(r) for r in c.execute('SELECT id,host_user_id,invited_user_id,status,revision,created_at,finished_at FROM multiplayer_game_sessions ORDER BY created_at DESC LIMIT 100')],'rewards':[dict(r) for r in c.execute('SELECT r.*,ct.amount FROM multiplayer_game_rewards r JOIN coin_transactions ct ON ct.id=r.coin_transaction_id ORDER BY ct.created_at DESC LIMIT 100')],'reports':[dict(r) for r in c.execute('SELECT * FROM integration_reports ORDER BY created_at DESC LIMIT 100')],'alerts':[dict(r) for r in c.execute('SELECT * FROM multiplayer_validation_events ORDER BY created_at DESC LIMIT 100')]}
