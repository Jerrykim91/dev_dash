import base64,json,math,os,time,uuid
from .storage import LocalMediaStore,validate_image

PRIVACY={key:'public' for key in ('bio','message','presence','work_status','location')}
class CommunityError(Exception):
 def __init__(self,message,status=422):self.message=message;self.status=status

def pair(a,b):return tuple(sorted((a,b)))
def uid():return str(uuid.uuid4())
class CommunityService:
 def __init__(self,repo,social,hub,media_root=None,clock=None):
  self.repo=repo;self.social=social;self.hub=hub;self.clock=clock or time.time;self.storage=LocalMediaStore(media_root or os.getenv('MEDIA_ROOT','data/media'));self.pending=set();self.max_members=min(50,max(2,int(os.getenv('SOCIAL_GROUP_MAX_MEMBERS','30'))))
 def blocked(self,c,a,b):return a!=b and bool(c.execute('SELECT 1 FROM user_blocks WHERE (user_id=? AND blocked_id=?) OR (user_id=? AND blocked_id=?)',(a,b,b,a)).fetchone())
 def require_unblocked(self,a,b):
  with self.repo.connect() as c:
   if self.blocked(c,a,b):raise CommunityError('이 사용자와 연결할 수 없습니다.',403)
 def user(self,c,who):
  r=c.execute('SELECT id,nickname FROM users WHERE id=? AND disabled=0',(who,)).fetchone()
  if not r:raise CommunityError('사용자를 찾을 수 없습니다.',404)
  return r
 def relation(self,c,a,b):
  low,high=pair(a,b);friend=bool(c.execute('SELECT 1 FROM friendships WHERE user_low=? AND user_high=?',(low,high)).fetchone());req=c.execute("SELECT id,sender_id,recipient_id FROM friend_requests WHERE user_low=? AND user_high=? AND status='pending'",(low,high)).fetchone()
  return {'friends':friend,'request':dict(req) if req else None,'blocked_by_me':bool(c.execute('SELECT 1 FROM user_blocks WHERE user_id=? AND blocked_id=?',(a,b)).fetchone())}
 def profile(self,viewer,target):
  with self.repo.connect() as c:
   u=self.user(c,target);r=c.execute('SELECT * FROM user_profiles WHERE user_id=?',(target,)).fetchone();privacy=json.loads(r['privacy']) if r else PRIVACY;rel=self.relation(c,viewer,target);blocked=self.blocked(c,viewer,target)
   allowed=lambda key:viewer==target or (not blocked and (privacy[key]=='public' or (privacy[key]=='friends' and rel['friends'])))
   status=c.execute('SELECT * FROM user_status WHERE user_id=?',(target,)).fetchone();avatar=c.execute('SELECT avatar_id,palette FROM avatar_profiles WHERE user_id=?',(target,)).fetchone();p=self.hub.peers.get(target);saved=c.execute('SELECT scope,zone FROM zone_presence WHERE user_id=?',(target,)).fetchone()
   value={'user_id':target,'nickname':u['nickname'],'avatar':dict(avatar) if avatar else {},'bio':(r['bio'] if r else '') if allowed('bio') else None,'message':status['message'] if allowed('message') else None,'work_status':status['work_status'] if allowed('work_status') else None,'presence':('online' if p else 'offline') if allowed('presence') else None,'location':(saved['zone'] if saved and saved['scope']=='office' else 'personal' if saved else None) if allowed('location') else None,'relationship':rel}
   if viewer==target:value['privacy']=privacy
   return value
 def mask_world(self,player,viewer):
  if player['id']==viewer:return player
  with self.repo.connect() as c:
   r=c.execute('SELECT privacy FROM user_profiles WHERE user_id=?',(player['id'],)).fetchone()
   if not r and not self.blocked(c,viewer,player['id']):return player
   privacy=json.loads(r['privacy']) if r else PRIVACY;friend=self.relation(c,viewer,player['id'])['friends'];blocked=self.blocked(c,viewer,player['id'])
   visible=lambda key:not blocked and (privacy[key]=='public' or privacy[key]=='friends' and friend)
   result=dict(player)
   if not visible('work_status'):
    result['work_status']=None
    if player.get('action') in ('vacation','after_work','meeting','outside','focusing'):result['action']='idle'
    result['status_text']=('미니게임 플레이 중' if player.get('minigame') else player.get('message','') if visible('message') else '')
   if not visible('message'):result.update(message='',status_text='미니게임 플레이 중' if player.get('minigame') else '')
   if not visible('presence'):result['presence']='private'
   result['profile_location_visible']=visible('location')
   return result
 def save_profile(self,who,data):
  with self.repo.connect() as c:c.execute('INSERT INTO user_profiles VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET bio=excluded.bio,privacy=excluded.privacy',(who,data['bio'],json.dumps(data['privacy'])))
  self.pending.add(who);return self.profile(who,who)
 def _notify(self,c,to,actor,kind,message,gid=None,lid=None,ref=None):
  if to==actor or self.blocked(c,to,actor):return
  c.execute('INSERT INTO user_notifications(id,user_id,actor_id,kind,group_id,log_id,reference_id,message,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(uid(),to,actor,kind,gid,lid,ref,message,self.clock()));self.pending.add(to)
 def friends(self,who):
  with self.repo.connect() as c:
   ids=[r['user_high'] if r['user_low']==who else r['user_low'] for r in c.execute('SELECT * FROM friendships WHERE user_low=? OR user_high=?',(who,who))];req=[dict(r) for r in c.execute("SELECT f.*,s.nickname AS sender_name,t.nickname AS recipient_name FROM friend_requests f JOIN users s ON s.id=f.sender_id JOIN users t ON t.id=f.recipient_id WHERE (sender_id=? OR recipient_id=?) AND status='pending' ORDER BY created_at DESC",(who,who))];blocks=[dict(r) for r in c.execute('SELECT b.blocked_id,u.nickname FROM user_blocks b JOIN users u ON u.id=b.blocked_id WHERE b.user_id=?',(who,))]
  return {'friends':[self.profile(who,target) for target in ids],'requests':req,'blocks':blocks}
 def request_friend(self,who,target):
  if who==target:raise CommunityError('자신에게 요청할 수 없습니다.')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.user(c,target)
   if self.blocked(c,who,target):raise CommunityError('이 사용자와 연결할 수 없습니다.',403)
   r=self.relation(c,who,target)
   if r['friends'] or r['request']:raise CommunityError('이미 친구이거나 처리 중인 요청이 있습니다.',409)
   if c.execute("SELECT COUNT(*) FROM friend_requests WHERE sender_id=? AND status='pending'",(who,)).fetchone()[0]>=50:raise CommunityError('보낸 요청을 먼저 정리해 주세요.',429)
   rid=uid();c.execute("INSERT INTO friend_requests VALUES (?,?,?,?,?,'pending',?)",(rid,who,target,*pair(who,target),self.clock()));self._notify(c,target,who,'friend_request','새 친구 요청이 있습니다.',ref=rid)
  self.pending.add(who);return self.friends(who)
 def respond_friend(self,who,rid,action):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM friend_requests WHERE id=?',(rid,)).fetchone()
   if not r or (action=='cancel' and r['sender_id']!=who) or (action!='cancel' and r['recipient_id']!=who):raise CommunityError('내 친구 요청이 아닙니다.',403)
   if r['status']!='pending':raise CommunityError('이미 처리한 친구 요청입니다.',409)
   if self.blocked(c,r['sender_id'],r['recipient_id']):raise CommunityError('이 사용자와 연결할 수 없습니다.',403)
   status={'accept':'accepted','reject':'rejected','cancel':'cancelled'}[action];c.execute('UPDATE friend_requests SET status=? WHERE id=?',(status,rid))
   if action=='accept':c.execute('INSERT OR IGNORE INTO friendships VALUES (?,?,?)',(*pair(r['sender_id'],who),self.clock()));self._notify(c,r['sender_id'],who,'friend_accepted','친구 요청이 수락됐습니다.',ref=rid)
   self.pending.update((r['sender_id'],r['recipient_id']))
  return self.friends(who)
 def remove_friend(self,who,target):
  with self.repo.connect() as c:c.execute('DELETE FROM friendships WHERE user_low=? AND user_high=?',pair(who,target))
  self.pending.update((who,target));return self.friends(who)
 def block(self,who,target,enabled):
  if who==target:raise CommunityError('자신을 차단할 수 없습니다.')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.user(c,target)
   if enabled:
    c.execute('INSERT OR IGNORE INTO user_blocks VALUES (?,?,?)',(who,target,self.clock()));c.execute('DELETE FROM friendships WHERE user_low=? AND user_high=?',pair(who,target));c.execute("UPDATE friend_requests SET status='cancelled' WHERE user_low=? AND user_high=? AND status='pending'",pair(who,target));c.execute("UPDATE group_invitations SET status='cancelled' WHERE status='pending' AND ((sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?))",(who,target,target,who))
   else:c.execute('DELETE FROM user_blocks WHERE user_id=? AND blocked_id=?',(who,target))
  self.pending.update((who,target));return self.profile(who,target)
 def group(self,c,gid):
  r=c.execute('SELECT * FROM social_groups WHERE id=? AND deleted=0',(gid,)).fetchone()
  if not r:raise CommunityError('그룹을 찾을 수 없습니다.',404)
  return dict(r)
 def member(self,c,who,gid,roles=None):
  g=self.group(c,gid);m=c.execute('SELECT role FROM group_memberships WHERE group_id=? AND user_id=?',(gid,who)).fetchone()
  if not m or roles and m['role'] not in roles:raise CommunityError('그룹 권한이 없습니다.',403)
  return g,m['role']
 def group_view(self,c,who,gid):
  g=self.group(c,gid);m=c.execute('SELECT role FROM group_memberships WHERE group_id=? AND user_id=?',(gid,who)).fetchone();invited=c.execute("SELECT 1 FROM group_invitations WHERE group_id=? AND recipient_id=? AND status='pending' AND kind='invite'",(gid,who)).fetchone()
  if not m and g['visibility']!='public' and not invited:raise CommunityError('그룹을 찾을 수 없습니다.',404)
  g['my_role']=m['role'] if m else None;g['member_count']=c.execute('SELECT COUNT(*) FROM group_memberships WHERE group_id=?',(gid,)).fetchone()[0]
  g['members']=[dict(r) for r in c.execute('SELECT m.user_id,m.role,u.nickname FROM group_memberships m JOIN users u ON u.id=m.user_id WHERE m.group_id=? ORDER BY m.role,u.nickname',(gid,))] if m else []
  g['invitations']=[dict(r) for r in c.execute("SELECT i.*,u.nickname FROM group_invitations i JOIN users u ON u.id=i.recipient_id WHERE i.group_id=? AND i.status='pending' ORDER BY i.created_at",(gid,))] if m and m['role'] in ('owner','manager') else []
  return g
 def groups(self,who,discover=False):
  with self.repo.connect() as c:
   ids=[r['id'] for r in c.execute("SELECT g.id FROM social_groups g LEFT JOIN group_memberships m ON m.group_id=g.id AND m.user_id=? WHERE g.deleted=0 AND (m.user_id IS NOT NULL OR (?=1 AND g.visibility='public')) ORDER BY g.created_at DESC LIMIT 100",(who,int(discover)))];invitations=[dict(r) for r in c.execute("SELECT i.*,g.name FROM group_invitations i JOIN social_groups g ON g.id=i.group_id WHERE i.recipient_id=? AND i.status='pending' AND i.kind='invite' AND g.deleted=0",(who,))]
   return {'groups':[self.group_view(c,who,gid) for gid in ids],'invitations':invitations,'max_members':self.max_members}
 def _attach_cover(self,c,who,gid,mid):
  if not mid:return
  media=c.execute('SELECT * FROM log_media WHERE id=? AND owner_id=? AND deleted=0',(mid,who)).fetchone()
  if not media or media['log_id'] or media['group_id'] and media['group_id']!=gid:raise CommunityError('내가 업로드한 미사용 이미지만 선택할 수 있습니다.',403)
  c.execute('UPDATE log_media SET group_id=? WHERE id=?',(gid,mid))
 def save_group(self,who,data,gid=None):
  if data['max_members']>self.max_members:raise CommunityError('그룹 최대 인원 설정을 초과했습니다.')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   if gid:
    g,role=self.member(c,who,gid,('owner',));count=c.execute('SELECT COUNT(*) FROM group_memberships WHERE group_id=?',(gid,)).fetchone()[0]
    if data['max_members']<count:raise CommunityError('현재 인원보다 정원을 줄일 수 없습니다.',409)
    self._attach_cover(c,who,gid,data.get('cover_media_id'))
    if g['cover_media_id'] and g['cover_media_id']!=data.get('cover_media_id'):c.execute('UPDATE log_media SET deleted=1 WHERE id=?',(g['cover_media_id'],))
    c.execute('UPDATE social_groups SET name=?,description=?,visibility=?,max_members=?,cover_media_id=? WHERE id=?',(data['name'],data['description'],data['visibility'],data['max_members'],data.get('cover_media_id'),gid))
   else:
    if c.execute('SELECT COUNT(*) FROM social_groups WHERE owner_id=? AND deleted=0',(who,)).fetchone()[0]>=10:raise CommunityError('소유 그룹은 최대 10개입니다.',409)
    gid=uid();c.execute('INSERT INTO social_groups(id,owner_id,name,description,visibility,max_members,cover_media_id,created_at) VALUES (?,?,?,?,?,?,?,?)',(gid,who,data['name'],data['description'],data['visibility'],data['max_members'],None,self.clock()));c.execute("INSERT INTO group_memberships VALUES (?,?,'owner',?)",(gid,who,self.clock()));self._attach_cover(c,who,gid,data.get('cover_media_id'));c.execute('UPDATE social_groups SET cover_media_id=? WHERE id=?',(data.get('cover_media_id'),gid))
   self.pending.add(who);return self.group_view(c,who,gid)
 def membership(self,who,gid,target,action):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');g,role=self.member(c,who,gid)
   if action=='leave':
    if role=='owner':raise CommunityError('소유자는 그룹 삭제로 그룹을 종료할 수 있습니다.',409)
    target=who
   else:
    t=c.execute('SELECT role FROM group_memberships WHERE group_id=? AND user_id=?',(gid,target)).fetchone()
    if not t or t['role']=='owner' or target==who or role=='member' or role=='manager' and t['role']!='member':raise CommunityError('이 멤버를 관리할 권한이 없습니다.',403)
   if action in ('leave','kick'):
    c.execute('DELETE FROM group_memberships WHERE group_id=? AND user_id=?',(gid,target));c.execute("UPDATE group_invitations SET status='cancelled' WHERE group_id=? AND sender_id=? AND status='pending'",(gid,target))
   else:
    if role!='owner':raise CommunityError('소유자만 그룹 관리자를 지정할 수 있습니다.',403)
    c.execute('UPDATE group_memberships SET role=? WHERE group_id=? AND user_id=?',(action,gid,target))
   self.pending.update((who,target))
  return {'ok':True}
 def delete_group(self,who,gid):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.member(c,who,gid,('owner',));self.pending.update(r['user_id'] for r in c.execute('SELECT user_id FROM group_memberships WHERE group_id=?',(gid,)));c.execute('UPDATE social_groups SET deleted=1 WHERE id=?',(gid,));c.execute("UPDATE group_invitations SET status='cancelled' WHERE group_id=? AND status='pending'",(gid,));c.execute('UPDATE log_media SET deleted=1 WHERE group_id=? OR log_id IN (SELECT id FROM shared_logs WHERE group_id=?)',(gid,gid))
  return {'ok':True}
 def invite(self,who,gid,target=None):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');g=self.group(c,gid);kind='invite' if target else 'request';target=target or who
   if kind=='invite':self.member(c,who,gid,('owner','manager'));self.user(c,target)
   elif g['visibility']!='public':raise CommunityError('비공개 그룹은 초대가 필요합니다.',403)
   if c.execute('SELECT 1 FROM group_memberships WHERE group_id=? AND user_id=?',(gid,target)).fetchone():raise CommunityError('이미 그룹 멤버입니다.',409)
   if self.blocked(c,who,target):raise CommunityError('이 사용자와 연결할 수 없습니다.',403)
   if c.execute("SELECT 1 FROM group_invitations WHERE group_id=? AND recipient_id=? AND kind=? AND status='pending'",(gid,target,kind)).fetchone():raise CommunityError('처리 중인 요청이 있습니다.',409)
   iid=uid();c.execute("INSERT INTO group_invitations VALUES (?,?,?,?,?,'pending',?)",(iid,gid,who,target,kind,self.clock()))
   if kind=='invite':self._notify(c,target,who,'group_invite','그룹 초대가 있습니다.',gid,ref=iid)
   else:
    for m in c.execute("SELECT user_id FROM group_memberships WHERE group_id=? AND role IN ('owner','manager')",(gid,)):self._notify(c,m['user_id'],who,'group_request','그룹 가입 요청이 있습니다.',gid,ref=iid)
   self.pending.add(who)
  return {'invitation_id':iid}
 def respond_invite(self,who,iid,accept):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute("SELECT * FROM group_invitations WHERE id=? AND status='pending'",(iid,)).fetchone()
   if not r:raise CommunityError('유효한 초대/가입 요청이 없습니다.',404)
   g=self.group(c,r['group_id'])
   if r['kind']=='invite':
    if who!=r['recipient_id']:raise CommunityError('내 초대가 아닙니다.',403)
    self.member(c,r['sender_id'],g['id'],('owner','manager'))
   else:self.member(c,who,g['id'],('owner','manager'))
   if self.blocked(c,who,r['recipient_id']) or self.blocked(c,r['sender_id'],r['recipient_id']):raise CommunityError('이 사용자와 연결할 수 없습니다.',403)
   if accept:
    if c.execute('SELECT COUNT(*) FROM group_memberships WHERE group_id=?',(g['id'],)).fetchone()[0]>=g['max_members']:raise CommunityError('그룹 정원이 찼습니다.',409)
    c.execute("INSERT OR IGNORE INTO group_memberships VALUES (?,?,'member',?)",(g['id'],r['recipient_id'],self.clock()));c.execute("UPDATE group_invitations SET status='cancelled' WHERE group_id=? AND recipient_id=? AND status='pending' AND id<>?",(g['id'],r['recipient_id'],iid));self._notify(c,r['recipient_id'],who,'group_approved','그룹 가입이 승인됐습니다.',g['id']);self._notify(c,g['owner_id'],r['recipient_id'],'group_member_joined','새 그룹 멤버가 참여했습니다.',g['id'])
   c.execute('UPDATE group_invitations SET status=? WHERE id=?',('accepted' if accept else 'rejected',iid));self.pending.update((who,r['recipient_id'],r['sender_id']))
  return {'ok':True,'group_id':g['id']}
 def _read_log(self,c,who,lid):
  r=c.execute('SELECT * FROM shared_logs WHERE id=? AND deleted=0 AND hidden=0',(lid,)).fetchone()
  if not r:raise CommunityError('기록을 찾을 수 없습니다.',404)
  self.member(c,who,r['group_id'])
  if r['visibility']=='self' and r['author_id']!=who or self.blocked(c,who,r['author_id']):raise CommunityError('기록을 찾을 수 없습니다.',404)
  return dict(r)
 def _changed(self,c,gid,lid):
  for m in c.execute('SELECT user_id FROM group_memberships WHERE group_id=?',(gid,)):
   try:self._read_log(c,m['user_id'],lid)
   except CommunityError:continue
   self.pending.add(m['user_id'])
 def _reactions(self,c,kind,target,who):return [dict(r) for r in c.execute('SELECT emoji,COUNT(*) AS count,SUM(CASE WHEN user_id=? THEN 1 ELSE 0 END) AS mine FROM log_reactions WHERE target_kind=? AND target_id=? GROUP BY emoji',(who,kind,target))]
 def _log_view(self,c,who,lid):
  log=self._read_log(c,who,lid);log['author_name']=c.execute('SELECT nickname FROM users WHERE id=?',(log['author_id'],)).fetchone()[0];log['media']=[{'id':r['id'],'content_type':r['content_type'],'width':r['width'],'height':r['height']} for r in c.execute('SELECT * FROM log_media WHERE log_id=? AND deleted=0',(lid,))];log['reactions']=self._reactions(c,'log',lid,who);log['comment_count']=c.execute('SELECT COUNT(*) FROM log_comments WHERE log_id=? AND deleted=0 AND hidden=0',(lid,)).fetchone()[0];return log
 def feed(self,who,gid,cursor=None,limit=10):
  sql='';args=[gid,who,who,who];limit=min(30,max(1,limit))
  if cursor:
   try:
    t,ident=json.loads(base64.urlsafe_b64decode(cursor.encode()));t=float(t)
    if not math.isfinite(t) or not isinstance(ident,str) or len(ident)>100:raise ValueError()
   except Exception:raise CommunityError('페이지 위치가 올바르지 않습니다.')
   sql=' AND (l.created_at<? OR (l.created_at=? AND l.id<?))';args.extend((t,t,ident))
  with self.repo.connect() as c:
   self.member(c,who,gid);rows=c.execute("SELECT l.id,l.created_at FROM shared_logs l WHERE l.group_id=? AND l.deleted=0 AND l.hidden=0 AND (l.visibility='group' OR l.author_id=?) AND NOT EXISTS (SELECT 1 FROM user_blocks b WHERE (b.user_id=? AND b.blocked_id=l.author_id) OR (b.user_id=l.author_id AND b.blocked_id=?))"+sql+' ORDER BY l.created_at DESC,l.id DESC LIMIT ?',(*args,limit+1)).fetchall();visible=rows[:limit];result=[self._log_view(c,who,r['id']) for r in visible]
  next_cursor=base64.urlsafe_b64encode(json.dumps([visible[-1]['created_at'],visible[-1]['id']]).encode()).decode() if len(rows)>limit else None
  return {'items':result,'next_cursor':next_cursor}
 def get_log(self,who,lid):
  with self.repo.connect() as c:return self._log_view(c,who,lid)
 def write_log(self,who,data,lid=None):
  now=self.clock();mids=data['media_ids']
  if len(set(mids))!=len(mids):raise CommunityError('이미지는 중복 첨부할 수 없습니다.')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.member(c,who,data['group_id'])
   if lid:
    previous=self._read_log(c,who,lid)
    if previous['author_id']!=who or previous['group_id']!=data['group_id']:raise CommunityError('내 기록만 수정할 수 있습니다.',403)
   else:lid=uid()
   for mid in mids:
    m=c.execute('SELECT * FROM log_media WHERE id=? AND owner_id=? AND deleted=0',(mid,who)).fetchone()
    if not m or m['group_id'] or m['log_id'] and m['log_id']!=lid:raise CommunityError('내 미사용 이미지 또는 이 기록의 이미지만 첨부할 수 있습니다.',403)
   if not data['text'].strip() and not mids:raise CommunityError('내용 또는 이미지를 입력해 주세요.')
   if 'previous' in locals():
    c.execute('UPDATE shared_logs SET text=?,visibility=?,updated_at=? WHERE id=?',(data['text'].strip(),data['visibility'],now,lid))
    for m in c.execute('SELECT id FROM log_media WHERE log_id=? AND deleted=0',(lid,)).fetchall():
     if m['id'] not in mids:c.execute('UPDATE log_media SET deleted=1 WHERE id=?',(m['id'],))
   else:c.execute('INSERT INTO shared_logs(id,group_id,author_id,text,visibility,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',(lid,data['group_id'],who,data['text'].strip(),data['visibility'],now,now))
   for mid in mids:c.execute('UPDATE log_media SET log_id=? WHERE id=?',(lid,mid))
   if 'previous' not in locals() and data['visibility']=='group':
    for m in c.execute('SELECT user_id FROM group_memberships WHERE group_id=?',(data['group_id'],)):self._notify(c,m['user_id'],who,'group_log','그룹에 새 기록이 있습니다.',data['group_id'],lid)
   self._changed(c,data['group_id'],lid);return self._log_view(c,who,lid)
 def delete_log(self,who,lid):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');log=self._read_log(c,who,lid);g,role=self.member(c,who,log['group_id'])
   if log['author_id']!=who and role not in ('owner','manager'):raise CommunityError('기록 삭제 권한이 없습니다.',403)
   self._changed(c,g['id'],lid);c.execute('UPDATE shared_logs SET deleted=1 WHERE id=?',(lid,));c.execute('UPDATE log_media SET deleted=1 WHERE log_id=?',(lid,))
  return {'ok':True}
 def comments(self,who,lid):
  with self.repo.connect() as c:
   self._read_log(c,who,lid);rows=[dict(r) for r in c.execute('SELECT c.*,u.nickname AS author_name FROM log_comments c JOIN users u ON u.id=c.author_id WHERE c.log_id=? AND c.deleted=0 AND c.hidden=0 ORDER BY c.created_at,c.id LIMIT 100',(lid,))]
   return [{**r,'reactions':self._reactions(c,'comment',r['id'],who)} for r in rows if not self.blocked(c,who,r['author_id'])]
 def comment(self,who,lid,text,cid=None,delete=False):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');log=self._read_log(c,who,lid)
   if cid:
    old=c.execute('SELECT * FROM log_comments WHERE id=? AND log_id=? AND deleted=0 AND hidden=0',(cid,lid)).fetchone()
    if not old:raise CommunityError('댓글을 찾을 수 없습니다.',404)
    role=self.member(c,who,log['group_id'])[1]
    if old['author_id']!=who and (not delete or role not in ('owner','manager')):raise CommunityError('댓글 관리 권한이 없습니다.',403)
    c.execute('UPDATE log_comments SET text=?,deleted=?,updated_at=? WHERE id=?',(old['text'] if delete else text,int(delete),self.clock(),cid))
   else:
    cid=uid();c.execute('INSERT INTO log_comments(id,log_id,author_id,text,created_at,updated_at) VALUES (?,?,?,?,?,?)',(cid,lid,who,text,self.clock(),self.clock()));self._notify(c,log['author_id'],who,'comment','내 기록에 댓글이 달렸습니다.',log['group_id'],lid,ref=cid)
   self._changed(c,log['group_id'],lid)
  return self.comments(who,lid)
 def reaction(self,who,kind,target,emoji,enabled):
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE')
   if kind=='comment':
    comment=c.execute('SELECT * FROM log_comments WHERE id=? AND deleted=0 AND hidden=0',(target,)).fetchone()
    if not comment or self.blocked(c,who,comment['author_id']):raise CommunityError('댓글을 찾을 수 없습니다.',404)
    lid=comment['log_id'];author=comment['author_id']
   else:lid=target;author=None
   log=self._read_log(c,who,lid);old=c.execute('SELECT 1 FROM log_reactions WHERE target_kind=? AND target_id=? AND user_id=? AND emoji=?',(kind,target,who,emoji)).fetchone()
   if enabled and not old:c.execute('INSERT INTO log_reactions VALUES (?,?,?,?,?)',(kind,target,who,emoji,self.clock()));self._notify(c,author or log['author_id'],who,'reaction','내 콘텐츠에 반응이 달렸습니다.',log['group_id'],lid,ref=target)
   elif not enabled:c.execute('DELETE FROM log_reactions WHERE target_kind=? AND target_id=? AND user_id=? AND emoji=?',(kind,target,who,emoji))
   self._changed(c,log['group_id'],lid);return self._reactions(c,kind,target,who)
 def upload(self,who,data):
  clean,kind,width,height=validate_image(data);key=self.storage.put(clean,kind)
  try:
   with self.repo.connect() as c:
    c.execute('BEGIN IMMEDIATE');used=c.execute('SELECT COALESCE(SUM(size_bytes),0) FROM log_media WHERE owner_id=? AND deleted=0',(who,)).fetchone()[0]
    if used+len(clean)>100*1024*1024:raise CommunityError('개인 이미지 저장 한도 100MB를 초과했습니다.',409)
    mid=uid();c.execute('INSERT INTO log_media(id,owner_id,storage_key,content_type,size_bytes,width,height,created_at) VALUES (?,?,?,?,?,?,?,?)',(mid,who,key,kind,len(clean),width,height,self.clock()))
  except Exception:self.storage.delete(key);raise
  return {'id':mid,'content_type':kind,'width':width,'height':height}
 def media(self,who,mid):
  with self.repo.connect() as c:
   m=c.execute('SELECT * FROM log_media WHERE id=? AND deleted=0',(mid,)).fetchone()
   if not m:raise CommunityError('이미지를 찾을 수 없습니다.',404)
   if m['log_id']:self._read_log(c,who,m['log_id'])
   elif m['group_id']:self.member(c,who,m['group_id'])
   elif m['owner_id']!=who:raise CommunityError('이미지를 찾을 수 없습니다.',404)
  return self.storage.path(m['storage_key']),m['content_type']
 def cleanup_media(self,grace_hours=24):
  removed=0;cutoff=self.clock()-grace_hours*3600
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');rows=c.execute("SELECT id,storage_key FROM log_media WHERE storage_key<>'' AND (deleted=1 OR (log_id IS NULL AND group_id IS NULL AND created_at<?))",(cutoff,)).fetchall()
   for r in rows:self.storage.delete(r['storage_key']);c.execute("UPDATE log_media SET storage_key='',deleted=1 WHERE id=?",(r['id'],));removed+=1
  return {'removed':removed}
 def notifications(self,who):
  with self.repo.connect() as c:
   rows=[dict(r) for r in c.execute('SELECT * FROM user_notifications WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 300',(who,))];visible=[]
   for row in rows:
    if self.blocked(c,who,row['actor_id']):continue
    if row['log_id']:
     try:self._read_log(c,who,row['log_id'])
     except CommunityError:continue
    visible.append(row)
  return {'items':visible,'unread_count':sum(r['read_at'] is None for r in visible)}
 def mark_read(self,who,nid=None):
  with self.repo.connect() as c:
   if nid:c.execute('UPDATE user_notifications SET read_at=? WHERE id=? AND user_id=?',(self.clock(),nid,who))
   else:c.execute('UPDATE user_notifications SET read_at=? WHERE user_id=? AND read_at IS NULL',(self.clock(),who))
  return self.notifications(who)
 def report(self,who,kind,target,reason):
  with self.repo.connect() as c:
   if kind=='log':self._read_log(c,who,target)
   elif kind=='comment':
    row=c.execute('SELECT log_id FROM log_comments WHERE id=? AND deleted=0 AND hidden=0',(target,)).fetchone()
    if not row:raise CommunityError('댓글을 찾을 수 없습니다.',404)
    self._read_log(c,who,row['log_id'])
   else:self.user(c,target)
   rid=uid();c.execute('INSERT INTO content_reports(id,reporter_id,target_kind,target_id,reason,created_at) VALUES (?,?,?,?,?,?)',(rid,who,kind,target,reason,self.clock()))
  return {'report_id':rid}
 def admin_reports(self,who,rid=None):
  self.social.require(who,'social_moderate')
  with self.repo.connect() as c:
   if not rid:return [dict(r) for r in c.execute('SELECT r.*,u.nickname AS reporter_name FROM content_reports r JOIN users u ON u.id=r.reporter_id ORDER BY r.created_at DESC LIMIT 100')]
   row=c.execute('SELECT * FROM content_reports WHERE id=?',(rid,)).fetchone()
   if not row:raise CommunityError('신고를 찾을 수 없습니다.',404)
   table={'log':'shared_logs','comment':'log_comments','user':'users'}[row['target_kind']];fields='id,nickname,disabled' if table=='users' else 'id,author_id,text,deleted,hidden';content=c.execute('SELECT '+fields+' FROM '+table+' WHERE id=?',(row['target_id'],)).fetchone();self.social.audit(c,who,'social_report_reviewed',rid,{'target_kind':row['target_kind'],'target_id':row['target_id']});return {'report':dict(row),'content':dict(content) if content else None,'media':[dict(m) for m in c.execute('SELECT id FROM log_media WHERE log_id=?',(row['target_id'],))] if row['target_kind']=='log' else []}
 def moderate(self,who,rid,hidden,resolution):
  self.social.require(who,'social_moderate')
  with self.repo.connect() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM content_reports WHERE id=?',(rid,)).fetchone()
   if not r:raise CommunityError('신고를 찾을 수 없습니다.',404)
   if r['target_kind'] in ('log','comment'):
    table='shared_logs' if r['target_kind']=='log' else 'log_comments'
    original=c.execute('SELECT * FROM '+table+' WHERE id=?',(r['target_id'],)).fetchone()
    if original:
     lid=r['target_id'] if table=='shared_logs' else original['log_id']
     log=c.execute('SELECT group_id FROM shared_logs WHERE id=?',(lid,)).fetchone()
     if log:self._changed(c,log['group_id'],lid)
    c.execute('UPDATE '+table+' SET hidden=? WHERE id=?',(int(hidden),r['target_id']))
   c.execute("UPDATE content_reports SET status='resolved',resolution=?,resolved_by=?,resolved_at=? WHERE id=?",(resolution,who,self.clock(),rid));self.social.audit(c,who,'social_report_resolved',rid,{'hidden':hidden,'resolution':resolution,'target_kind':r['target_kind']})
  return {'ok':True}

 def report_media(self,who,rid,mid):
  self.social.require(who,'social_moderate')
  with self.repo.connect() as c:
   report=c.execute("SELECT * FROM content_reports WHERE id=? AND target_kind='log'",(rid,)).fetchone()
   media=c.execute('SELECT * FROM log_media WHERE id=?',(mid,)).fetchone()
   if not report or not media or media['log_id']!=report['target_id']:raise CommunityError('신고에 연결된 이미지를 찾을 수 없습니다.',404)
   self.social.audit(c,who,'social_report_media_reviewed',rid,{'media_id':mid})
  return self.storage.path(media['storage_key']),media['content_type']
