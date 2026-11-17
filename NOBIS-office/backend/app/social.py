"""World instances, private delivery, moderation and RBAC persistence boundary."""
import hashlib
import hmac
import json
import os
import secrets
import time
import unicodedata
import uuid
from datetime import datetime,timezone

RANK={'user':0,'moderator':1,'admin':2,'super_admin':3}
BASE={'world_use','chat_send'}
PERMISSIONS={'user':BASE,'moderator':BASE|{'reports_read','messages_manage','mutes_manage'},'admin':BASE|{'reports_read','messages_manage','mutes_manage','announcements_manage','channels_manage','users_manage','role_moderator','audit_read'},'super_admin':BASE|{'reports_read','messages_manage','mutes_manage','announcements_manage','channels_manage','users_manage','role_moderator','audit_read','role_admin','system_settings'}}
for _role in ('moderator','admin','super_admin'):PERMISSIONS[_role]=PERMISSIONS[_role]|{'games_read'}
for _role in ('admin','super_admin'):PERMISSIONS[_role]=PERMISSIONS[_role]|{'games_manage'}
for _role in ('moderator','admin','super_admin'):PERMISSIONS[_role]=PERMISSIONS[_role]|{'social_moderate','collectibles_read'}
for _role in ('admin','super_admin'):PERMISSIONS[_role]=PERMISSIONS[_role]|{'collectibles_manage'}
class SocialError(Exception):
    def __init__(self,message,status=422):self.message=message;self.status=status

def timestamp():return datetime.now(timezone.utc).isoformat()
def canonical(name):return unicodedata.normalize('NFKC',name).casefold()
def zone_channel(channel,zone,scope='office'):
    if scope.startswith('personal:'):return 'zone:'+scope
    return f'zone:{zone}' if channel=='ch1' else f'zone:{channel}:{zone}'
def hash_password(password):
    salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'
def verify_password(password,encoded):
    try:
        scheme,rounds,salt,wanted=encoded.split('$')
        if scheme!='pbkdf2_sha256':return False
        return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)).hex(),wanted)
    except (ValueError,TypeError):return False

class SocialService:
    def __init__(self,repo):self.repo=repo
    def initialize(self,capacity=15):
        with self.repo.connect() as c:
            c.execute("INSERT OR IGNORE INTO world_channels VALUES ('ch1','nobis','채널 1',?,1)",(capacity,))
            for role,permissions in PERMISSIONS.items():
                for permission in permissions:c.execute('INSERT OR IGNORE INTO role_permissions VALUES (?,?)',(role,permission))
    def role(self,uid):
        with self.repo.connect() as c:r=c.execute('SELECT role FROM user_roles WHERE user_id=?',(uid,)).fetchone()
        return r['role'] if r else 'user'
    def require(self,uid,permission):
        with self.repo.connect() as c:r=c.execute('SELECT 1 FROM user_roles r JOIN role_permissions p ON r.role=p.role JOIN users u ON u.id=r.user_id WHERE r.user_id=? AND p.permission=? AND u.disabled=0',(uid,permission)).fetchone()
        if not r:raise SocialError('관리자 권한이 없습니다.',403)
    def audit(self,c,actor,action,target=None,details=None):c.execute('INSERT INTO admin_audit_logs(actor_id,action,target_id,details) VALUES (?,?,?,?)',(actor,action,target,json.dumps(details or {},ensure_ascii=False)))
    def bootstrap(self,uid):
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute("SELECT 1 FROM user_roles WHERE role='super_admin'").fetchone() or c.execute("SELECT 1 FROM system_settings WHERE key='bootstrap_done'").fetchone():raise SocialError('최초 관리자 초기화는 이미 완료됐습니다.',409)
            if not c.execute('SELECT 1 FROM users WHERE id=? AND disabled=0',(uid,)).fetchone():raise SocialError('기존의 활성 사용자 ID가 필요합니다.',404)
            c.execute("UPDATE user_roles SET role='super_admin',updated_at=CURRENT_TIMESTAMP WHERE user_id=?",(uid,))
            c.execute("UPDATE users SET role='super_admin' WHERE id=?",(uid,))
            c.execute("INSERT INTO system_settings VALUES ('bootstrap_done','true')")
            self.audit(c,None,'bootstrap_super_admin',uid)
    def change_role(self,actor,target,role):
        if role not in RANK:raise SocialError('지원하지 않는 역할입니다.')
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            rows={r['user_id']:r['role'] for r in c.execute('SELECT user_id,role FROM user_roles WHERE user_id IN (?,?)',(actor,target))}
            a=rows.get(actor,'user');old=rows.get(target)
            if old is None:raise SocialError('사용자를 찾을 수 없습니다.',404)
            if a!='super_admin' and not (a=='admin' and old in ('user','moderator') and role in ('user','moderator')):raise SocialError('super_admin만 관리자 권한을 임명·해제할 수 있습니다.',403)
            if old=='super_admin' and role!='super_admin' and c.execute("SELECT COUNT(*) FROM user_roles WHERE role='super_admin'").fetchone()[0]<=1:raise SocialError('마지막 super_admin은 해제할 수 없습니다.',409)
            c.execute('UPDATE user_roles SET role=?,assigned_by=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?',(role,actor,target))
            c.execute('UPDATE users SET role=? WHERE id=?',(role,target));self.audit(c,actor,'role_changed',target,{'before':old,'after':role})
    def channels(self):
        with self.repo.connect() as c:return [dict(r) for r in c.execute('SELECT * FROM world_channels ORDER BY id')]
    def channel(self,cid):return next((c for c in self.channels() if c['id']==cid),None)
    def manage_channel(self,actor,cid,name,capacity,enabled,create=False):
        self.require(actor,'channels_manage')
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            exists=c.execute('SELECT 1 FROM world_channels WHERE id=?',(cid,)).fetchone()
            max_channels=int((c.execute("SELECT value FROM system_settings WHERE key='max_channels'").fetchone() or ['32'])[0])
            if create and c.execute('SELECT COUNT(*) FROM world_channels').fetchone()[0]>=max_channels:raise SocialError('시스템의 채널 수 한도에 도달했습니다.',409)
            if create and exists:raise SocialError('이미 존재하는 채널입니다.',409)
            if not create and not exists:raise SocialError('채널이 없습니다.',404)
            if cid=='ch1' and not enabled:raise SocialError('기본 채널은 비활성화할 수 없습니다.',409)
            c.execute('INSERT INTO world_channels VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,capacity=excluded.capacity,enabled=excluded.enabled',(cid,'nobis',name,capacity,int(enabled)))
            self.audit(c,actor,'channel_created' if create else 'channel_updated',cid,{'name':name,'capacity':capacity,'enabled':enabled})
    def preference(self,uid):
        with self.repo.connect() as c:r=c.execute('SELECT chat_bubbles_enabled FROM user_chat_preferences WHERE user_id=?',(uid,)).fetchone()
        return {'chat_bubbles_enabled':bool(r and r[0])}
    def save_preference(self,uid,enabled):
        with self.repo.connect() as c:c.execute('INSERT INTO user_chat_preferences VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET chat_bubbles_enabled=excluded.chat_bubbles_enabled',(uid,int(enabled)))
        return self.preference(uid)
    def directory(self,query=''):
        q=canonical(query)
        with self.repo.connect() as c:rows=c.execute('SELECT id,nickname FROM users WHERE disabled=0 ORDER BY nickname,id').fetchall()
        return [dict(r) for r in rows if q in canonical(r['nickname']) or q in r['id']][:30]
    def resolve_recipient(self,text,uid=None):
        if uid:
            with self.repo.connect() as c:r=c.execute('SELECT id,nickname FROM users WHERE id=? AND disabled=0',(uid,)).fetchone()
            if not r:raise SocialError('수신자를 찾을 수 없습니다.',404)
            prefix='@'+r['nickname']
            if not text.startswith(prefix+' '):raise SocialError('수신자를 다시 선택해 주세요.')
            body=text[len(prefix):].strip()
        else:
            parts=text.split(maxsplit=1)
            if len(parts)!=2 or not parts[0].startswith('@'):raise SocialError('@닉네임 뒤에 메시지를 입력하세요.')
            name=canonical(parts[0][1:])
            with self.repo.connect() as c:rows=[r for r in c.execute('SELECT id,nickname FROM users WHERE disabled=0') if canonical(r['nickname'])==name]
            if not rows:raise SocialError('존재하지 않는 닉네임입니다.',404)
            if len(rows)>1:raise SocialError('같은 닉네임이 여러 명입니다. 자동완성에서 ID를 확인하고 선택하세요.',409)
            r=rows[0];body=parts[1].strip()
        if not body or len(body)>500:raise SocialError('귓속말은 1~500자로 입력하세요.')
        return dict(r),body
    def private(self,sender,target,text,online):
        mid=str(uuid.uuid4())
        with self.repo.connect() as c:c.execute('INSERT INTO private_messages(id,sender_id,recipient_id,text,time,delivery) VALUES (?,?,?,?,?,?)',(mid,sender,target,text,timestamp(),'delivered' if online else 'stored'))
        return next(m for m in self.private_history(sender) if m['id']==mid)
    def private_history(self,uid):
        with self.repo.connect() as c:rows=c.execute('SELECT p.*,a.nickname,b.nickname AS recipient_nickname FROM private_messages p JOIN users a ON a.id=p.sender_id JOIN users b ON b.id=p.recipient_id WHERE p.sender_id=? OR p.recipient_id=? ORDER BY p.seq DESC LIMIT 100',(uid,uid)).fetchall()
        return [{**dict(r),'user_id':r['sender_id'],'channel':'private','message_type':'private','mentions':[]} for r in reversed(rows)]
    def deliver(self,uid):
        with self.repo.connect() as c:
            rows=[dict(r) for r in c.execute("SELECT id,sender_id FROM private_messages WHERE recipient_id=? AND delivery='stored'",(uid,))]
            c.execute("UPDATE private_messages SET delivery='delivered' WHERE recipient_id=? AND delivery='stored'",(uid,))
        return rows
    def announcements(self,cid):
        with self.repo.connect() as c:return [dict(r) for r in c.execute('SELECT * FROM announcements WHERE target_channel_id IS NULL OR target_channel_id=? ORDER BY rowid DESC LIMIT 100',(cid,))]
    def announce(self,actor,title,text,target,duration):
        self.require(actor,'announcements_manage')
        if target and not self.channel(target):raise SocialError('대상 채널이 없습니다.',404)
        item={'id':str(uuid.uuid4()),'author_id':actor,'title':title,'text':text,'target_channel_id':target,'duration_seconds':duration,'time':timestamp()}
        with self.repo.connect() as c:
            c.execute('INSERT INTO announcements VALUES (?,?,?,?,?,?,?)',tuple(item.values()));self.audit(c,actor,'announcement_sent',item['id'],{'target_channel_id':target,'title':title})
        return item
    def muted(self,uid):
        with self.repo.connect() as c:r=c.execute('SELECT * FROM user_chat_restrictions WHERE user_id=? AND until_time>?',(uid,time.time())).fetchone()
        if r:raise SocialError('채팅 제한 중입니다: '+r['reason'],403)
    def moderation_target(self,actor,target):
        if actor==target or RANK[self.role(actor)]<=RANK[self.role(target)]:raise SocialError('본인 또는 동급 이상의 사용자는 관리할 수 없습니다.',403)
    def mute(self,actor,target,minutes,reason):
        self.require(actor,'mutes_manage');self.moderation_target(actor,target)
        if not self.repo.user_exists(target):raise SocialError('사용자를 찾을 수 없습니다.',404)
        with self.repo.connect() as c:
            if minutes:c.execute('INSERT INTO user_chat_restrictions VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET until_time=excluded.until_time,reason=excluded.reason,actor_id=excluded.actor_id',(target,time.time()+minutes*60,reason,actor))
            else:c.execute('DELETE FROM user_chat_restrictions WHERE user_id=?',(target,))
            self.audit(c,actor,'chat_muted' if minutes else 'chat_unmuted',target,{'minutes':minutes,'reason':reason})
    def disable(self,actor,target,disabled):
        self.require(actor,'users_manage');self.moderation_target(actor,target)
        with self.repo.connect() as c:
            if not c.execute('UPDATE users SET disabled=? WHERE id=?',(int(disabled),target)).rowcount:raise SocialError('사용자가 없습니다.',404)
            self.audit(c,actor,'user_disabled' if disabled else 'user_enabled',target)
    def report(self,uid,target,reason):
        if not self.repo.user_exists(target):raise SocialError('사용자가 없습니다.',404)
        with self.repo.connect() as c:c.execute('INSERT INTO user_reports(id,reporter_id,target_id,reason) VALUES (?,?,?,?)',(str(uuid.uuid4()),uid,target,reason))
    def report_status(self,actor,rid,status):
        self.require(actor,'reports_read')
        with self.repo.connect() as c:
            if not c.execute('UPDATE user_reports SET status=? WHERE id=?',(status,rid)).rowcount:raise SocialError('신고가 없습니다.',404)
            self.audit(c,actor,'report_updated',rid,{'status':status})
    def delete_message(self,actor,mid):
        self.require(actor,'messages_manage')
        with self.repo.connect() as c:
            row=c.execute('SELECT * FROM chat_messages WHERE id=?',(mid,)).fetchone()
            if not row or row['channel'].startswith(('room:','zone:personal')):raise SocialError('공개 채팅 메시지만 관리할 수 있습니다.',404)
            c.execute("UPDATE chat_messages SET text='[관리자가 삭제한 메시지]' WHERE id=?",(mid,));self.audit(c,actor,'message_deleted',mid)
        return dict(row)
    def admin_data(self,actor,section):
        required={'dashboard':'reports_read','users':'users_manage','roles':'role_moderator','logs':'audit_read','reports':'reports_read','messages':'messages_manage','channels':'channels_manage','announcements':'announcements_manage','online':'reports_read'}
        if section not in required:raise SocialError('지원하지 않는 메뉴입니다.',404)
        self.require(actor,required[section])
        with self.repo.connect() as c:
            if section in ('users','roles'):return [dict(r) for r in c.execute('SELECT u.id,u.nickname,u.disabled,r.role,m.until_time AS muted_until FROM users u JOIN user_roles r ON r.user_id=u.id LEFT JOIN user_chat_restrictions m ON m.user_id=u.id ORDER BY u.nickname LIMIT 500')]
            if section=='logs':return self.audit_logs(c)
            if section=='reports':return [dict(r) for r in c.execute('SELECT * FROM user_reports ORDER BY rowid DESC LIMIT 200')]
            if section=='messages':return [dict(r) for r in c.execute("SELECT id,user_id,nickname,text,time,channel FROM chat_messages WHERE channel='world' OR (channel LIKE 'zone:%' AND channel NOT LIKE 'zone:personal%') OR channel LIKE 'channel:%' ORDER BY seq DESC LIMIT 100")]
            if section=='announcements':return [dict(r) for r in c.execute('SELECT * FROM announcements ORDER BY rowid DESC LIMIT 100')]
            if section=='channels':return self.channels()
            return {'users':c.execute('SELECT COUNT(*) FROM users').fetchone()[0],'channels':c.execute('SELECT COUNT(*) FROM world_channels').fetchone()[0],'active_channels':c.execute('SELECT COUNT(*) FROM world_channels WHERE enabled=1').fetchone()[0],'account_origins':{r['account_origin']:r['total'] for r in c.execute('SELECT account_origin,COUNT(*) AS total FROM users GROUP BY account_origin')},'recent_announcements':[dict(r) for r in c.execute('SELECT * FROM announcements ORDER BY rowid DESC LIMIT 5')],'recent_actions':self.audit_logs(c,5)}

    def system_settings(self,actor,data=None):
        self.require(actor,'system_settings')
        with self.repo.connect() as c:
            if data is not None:
                c.execute('BEGIN IMMEDIATE')
                if data['max_channels']<c.execute('SELECT COUNT(*) FROM world_channels').fetchone()[0]:raise SocialError('현재 채널 수보다 한도를 낮출 수 없습니다.',409)
                if not data['world_name'].strip():raise SocialError('월드 이름이 필요합니다.')
                c.execute("UPDATE worlds SET name=? WHERE id='nobis'",(data['world_name'].strip(),))
                c.execute("INSERT INTO system_settings VALUES ('max_channels',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(data['max_channels']),))
                self.audit(c,actor,'system_settings_changed','nobis',data)
            return {'world_name':c.execute("SELECT name FROM worlds WHERE id='nobis'").fetchone()[0],'max_channels':int((c.execute("SELECT value FROM system_settings WHERE key='max_channels'").fetchone() or ['32'])[0])}

    def password_user(self,uid,password):
        with self.repo.connect() as c:r=c.execute('SELECT id,password_hash FROM users WHERE id=? AND disabled=0',(uid,)).fetchone()
        return r['id'] if r and verify_password(password,r['password_hash']) else None
    def mark_delivered(self,mid):
        with self.repo.connect() as c:c.execute("UPDATE private_messages SET delivery='delivered' WHERE id=?",(mid,))
    def location_for(self,uid,target):
        from .world import walkable,map_for
        with self.repo.connect() as c:dest=c.execute('SELECT x,y FROM channel_locations WHERE user_id=? AND channel_id=?',(uid,target)).fetchone()
        return dict(dest) if dest and walkable('office',dest['x'],dest['y']) else map_for('office')['spawn']
    def switch_location(self,player,target):
        from .world import walkable,map_for,zone_at
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT INTO channel_locations VALUES (?,?,?,?) ON CONFLICT(user_id,channel_id) DO UPDATE SET x=excluded.x,y=excluded.y',(player['id'],player['channel_id'],player['x'],player['y']))
            dest=c.execute('SELECT x,y FROM channel_locations WHERE user_id=? AND channel_id=?',(player['id'],target)).fetchone()
            destination=dict(dest) if dest and walkable('office',dest['x'],dest['y']) else map_for('office')['spawn']
            zone=zone_at(destination['x'],destination['y'])
            c.execute("UPDATE zone_presence SET channel_id=?,world_id='nobis',scope='office',zone=?,x=?,y=?,action='idle',active_object=NULL WHERE user_id=?",(target,zone,destination['x'],destination['y'],player['id']))
        return destination,zone

    def audit_logs(self,con,limit=200):
        return [dict(r) for r in con.execute('SELECT l.*,a.nickname AS actor_name,t.nickname AS target_name,ch.name AS channel_name FROM admin_audit_logs l LEFT JOIN users a ON a.id=l.actor_id LEFT JOIN users t ON t.id=l.target_id LEFT JOIN world_channels ch ON ch.id=l.target_id ORDER BY l.seq DESC LIMIT ?',(limit,))]
