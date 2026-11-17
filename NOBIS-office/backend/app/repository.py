from .rooms_schema import ROOM_SCHEMA
"""SQLite/PostgreSQL access boundary. WebSocket handlers do not execute SQL directly."""
import hashlib
import json
from .migrations import PHASE2, PHASE3, MULTICHANNEL
from .games.schema import PHASE4
from .community.schema import SOCIAL_SCHEMA
from .integration.schema import PHASE6
from .collectibles.schema import COLLECTIBLES_SCHEMA,COIN_GACHA_SCHEMA
from contextlib import contextmanager
import secrets
import sqlite3
import time
import uuid
from pathlib import Path

class Repository:
    def __init__(self,path):
        self.path=str(path);self.kind='postgresql' if self.path.startswith(('postgresql://','postgres://')) else 'sqlite'
    @contextmanager
    def connect(self):
        if self.kind=='postgresql':
            import psycopg
            from .database import record_row,PostgresConnection
            with psycopg.connect(self.path,row_factory=record_row,options='-c timezone=UTC',connect_timeout=5) as raw:
                yield PostgresConnection(raw)
            return
        con = sqlite3.connect(self.path,timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            with con:
                yield con
        finally:
            con.close()
    def initialize(self,runtime_cleanup=True):
        if self.kind=='postgresql':
            from .database import initialize_postgres
            initialize_postgres(self,runtime_cleanup);return
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            existing=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
            migrated=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchone()
            migrated=bool(migrated and con.execute('SELECT 1 FROM schema_migrations WHERE version=2').fetchone())
            backup=Path(str(self.path)+'.pre-phase2.bak')
            if existing and not migrated and not backup.exists():
                target=sqlite3.connect(backup)
                try:con.backup(target)
                finally:target.close()
            if existing and (not migrated or not con.execute('SELECT 1 FROM schema_migrations WHERE version=6').fetchone()):
                backup4=Path(str(self.path)+'.pre-phase4.bak')
                if not backup4.exists():
                    with sqlite3.connect(backup4) as target:con.backup(target)
            if existing and (not migrated or not con.execute('SELECT 1 FROM schema_migrations WHERE version=7').fetchone()):
                phase5=Path(str(self.path)+'.pre-phase5.bak')
                if not phase5.exists():
                    with sqlite3.connect(phase5) as target:con.backup(target)
            if existing and migrated and not con.execute('SELECT 1 FROM schema_migrations WHERE version=8').fetchone():
                coins=Path(str(self.path)+'.pre-coin-gacha.bak')
                if not coins.exists():
                    with sqlite3.connect(coins) as target:con.backup(target)
            if existing and migrated and not con.execute('SELECT 1 FROM schema_migrations WHERE version=9').fetchone():
                phase6=Path(str(self.path)+'.pre-phase6.bak')
                if not phase6.exists():
                    with sqlite3.connect(phase6) as target:con.backup(target)
            if existing and migrated and not con.execute('SELECT 1 FROM schema_migrations WHERE version=10').fetchone():
                backup_room=Path(str(self.path)+'.pre-hybrid.bak')
                if not backup_room.exists():
                    with sqlite3.connect(backup_room) as target:con.backup(target)
            con.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, nickname TEXT NOT NULL,
                work_status TEXT NOT NULL DEFAULT 'working', message TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'member');
            CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL);
            """)
            # Non-destructive upgrade from the earlier MVP's users.status column.
            columns = {r['name'] for r in con.execute('PRAGMA table_info(users)')}
            if 'work_status' not in columns:
                con.execute("ALTER TABLE users ADD COLUMN work_status TEXT NOT NULL DEFAULT 'working'")
            if 'role' not in columns:
                con.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'member'")
            con.executescript('BEGIN IMMEDIATE;\n'+PHASE2+'\nCOMMIT;')
            v3=con.execute('SELECT 1 FROM schema_migrations WHERE version=3').fetchone()
            backup3=Path(str(self.path)+'.pre-phase3.bak')
            if existing and not v3 and not backup3.exists():
                target=sqlite3.connect(backup3)
                try:con.backup(target)
                finally:target.close()
            con.executescript('BEGIN IMMEDIATE;\n'+PHASE3+'\nCOMMIT;')
            if not con.execute('SELECT 1 FROM schema_migrations WHERE version=4').fetchone():
                backup4=Path(str(self.path)+'.pre-multichannel.bak')
                if existing and not backup4.exists():
                    target=sqlite3.connect(backup4)
                    try:con.backup(target)
                    finally:target.close()
            if existing and not con.execute('SELECT 1 FROM schema_migrations WHERE version=5').fetchone():
                backup35=Path(str(self.path)+'.pre-phase35.bak')
                if not backup35.exists():
                    target=sqlite3.connect(backup35)
                    try:con.backup(target)
                    finally:target.close()
            for table,column,definition in [('users','account_origin',"TEXT NOT NULL DEFAULT 'legacy'"),('sessions','auth_kind',"TEXT NOT NULL DEFAULT 'dev'"),('users','disabled','INTEGER NOT NULL DEFAULT 0'),('users','password_hash',"TEXT NOT NULL DEFAULT ''"),('zone_presence','world_id',"TEXT NOT NULL DEFAULT 'nobis'"),('zone_presence','channel_id',"TEXT NOT NULL DEFAULT 'ch1'")]:
                if column not in {r['name'] for r in con.execute(f'PRAGMA table_info({table})')}:con.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
            con.executescript('BEGIN IMMEDIATE;\n'+MULTICHANNEL+'\nCOMMIT;')
            con.execute('INSERT OR IGNORE INTO schema_migrations(version) VALUES (5)')
            con.executescript('BEGIN IMMEDIATE;\n'+PHASE4+SOCIAL_SCHEMA+COLLECTIBLES_SCHEMA+COIN_GACHA_SCHEMA+PHASE6+ROOM_SCHEMA+'\nCOMMIT;')
            if runtime_cleanup:con.execute("UPDATE zone_presence SET presence='offline'")
            con.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
    def create_user(self,nickname,role='member',origin='legacy'):
        uid, token = str(uuid.uuid4()), secrets.token_urlsafe(32)
        with self.connect() as con:
            con.execute('INSERT INTO users (id,nickname,work_status,message,role,account_origin) VALUES (?,?,?,?,?,?)',(uid,nickname,'working','',role,origin))
            self.ensure_user_rows(con,uid,nickname)
            con.execute('INSERT INTO sessions(token_hash,user_id,expires,auth_kind) VALUES (?,?,?,?)', (hashlib.sha256(token.encode()).hexdigest(),uid,time.time()+86400,'dev'))
        return token, self.user_for(token)
    def user_for(self, token):
        if not isinstance(token,str) or not token: return None
        with self.connect() as con:
            row = con.execute('SELECT u.id,u.nickname,st.work_status,st.message,r.role,s.expires,s.auth_kind FROM users u JOIN user_roles r ON r.user_id=u.id JOIN user_status st ON st.user_id=u.id JOIN sessions s ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>? AND u.disabled=0', (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        return dict(row) if row else None
    def update_status(self, uid, status, message):
        with self.connect() as con:
            con.execute('UPDATE users SET work_status=?, message=? WHERE id=?',(status,message,uid))
            con.execute('INSERT INTO user_status VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET work_status=excluded.work_status,message=excluded.message',(uid,status,message))

    def status_for(self, uid):
        with self.connect() as con:
            row=con.execute('SELECT work_status FROM user_status WHERE user_id=?',(uid,)).fetchone()
        return row['work_status'] if row else 'before_work'

    def ensure_user_rows(self,con,uid,nickname):
        con.execute("INSERT OR IGNORE INTO user_roles(user_id,role) SELECT id,CASE WHEN role IN ('admin','moderator','super_admin') THEN role ELSE 'user' END FROM users WHERE id=?",(uid,))
        con.execute("INSERT OR IGNORE INTO user_status VALUES (?,'working','')",(uid,))
        con.execute('INSERT OR IGNORE INTO avatar_profiles(user_id) VALUES (?)',(uid,))
        con.execute('INSERT OR IGNORE INTO personal_rooms VALUES (?,?,?)',(f'personal:{uid}',uid,f'{nickname}의 방'))
        con.execute('INSERT OR IGNORE INTO room_settings(room_id) VALUES (?)',(f'personal:{uid}',))
    def user_exists(self,uid):
        with self.connect() as c:return c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone() is not None
    def avatar_for(self,uid):
        with self.connect() as c:
            row=c.execute('SELECT avatar_id,palette FROM avatar_profiles WHERE user_id=?',(uid,)).fetchone()
        return dict(row) if row else {}
    def save_avatar(self,uid,palette):
        with self.connect() as c:c.execute('UPDATE avatar_profiles SET palette=? WHERE user_id=?',(palette,uid))
    def save_presence(self,p,return_position=None):
        with self.connect() as c:
            c.execute("""INSERT INTO zone_presence(user_id,scope,zone,x,y,presence,action,active_object,return_x,return_y)
                VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET scope=excluded.scope,zone=excluded.zone,x=excluded.x,y=excluded.y,presence=excluded.presence,action=excluded.action,active_object=excluded.active_object,return_x=excluded.return_x,return_y=excluded.return_y""",
                (p['id'],p.get('scope','office'),p['zone'],p['x'],p['y'],p['presence'],p['action'],p.get('active_object'),(return_position or {}).get('x'),(return_position or {}).get('y')))
            c.execute('UPDATE zone_presence SET world_id=?,channel_id=? WHERE user_id=?',(p.get('world_id','nobis'),p.get('channel_id','ch1'),p['id']))
            if p.get('scope','office')=='office':c.execute('INSERT INTO channel_locations VALUES (?,?,?,?) ON CONFLICT(user_id,channel_id) DO UPDATE SET x=excluded.x,y=excluded.y',(p['id'],p.get('channel_id','ch1'),p['x'],p['y']))
    def presence_for(self,uid):
        with self.connect() as c:row=c.execute('SELECT * FROM zone_presence WHERE user_id=?',(uid,)).fetchone()
        return dict(row) if row else None
    def settings_for(self,uid):
        with self.connect() as c:
            row=c.execute('SELECT p.id,p.name,s.dashboard_url FROM personal_rooms p JOIN room_settings s ON s.room_id=p.id WHERE p.user_id=?',(uid,)).fetchone()
        return dict(row)
    def save_settings(self,uid,name,url):
        with self.connect() as c:
            c.execute('UPDATE personal_rooms SET name=? WHERE user_id=?',(name,uid))
            c.execute('UPDATE room_settings SET dashboard_url=? WHERE room_id=?',(url,f'personal:{uid}'))
        return self.settings_for(uid)
    def ensure_channel(self,cid,kind,name):
        with self.connect() as c:c.execute('INSERT OR IGNORE INTO chat_channels(id,kind,name) VALUES (?,?,?)',(cid,kind,name))
    def channel(self,cid):
        with self.connect() as c:row=c.execute('SELECT * FROM chat_channels WHERE id=?',(cid,)).fetchone()
        return dict(row) if row else None
    def member(self,cid,uid):
        with self.connect() as c:row=c.execute('SELECT * FROM channel_members WHERE channel_id=? AND user_id=?',(cid,uid)).fetchone()
        return dict(row) if row else None
    def create_channel(self,uid,kind,name):
        cid=f'room:{uuid.uuid4()}'
        with self.connect() as c:
            c.execute('INSERT INTO chat_channels(id,kind,name,owner_id,meeting_id) VALUES (?,?,?,?,?)',(cid,kind,name,uid,f'meeting:{uuid.uuid4()}' if kind=='meeting' else None))
            c.execute("INSERT INTO channel_members(channel_id,user_id,state,role) VALUES (?,?,'active','owner')",(cid,uid))
        return cid
    def channels_for(self,uid):
        with self.connect() as c:
            rows=c.execute("SELECT ch.*,m.state AS membership,m.role AS member_role FROM chat_channels ch JOIN channel_members m ON m.channel_id=ch.id WHERE m.user_id=? AND m.state IN ('active','invited') ORDER BY ch.created_at,ch.id",(uid,)).fetchall()
            result=[]
            for row in rows:
                item=dict(row)
                item['members']=[dict(m) for m in c.execute("SELECT m.user_id,u.nickname,m.state,m.role FROM channel_members m JOIN users u ON u.id=m.user_id WHERE m.channel_id=? AND m.state IN ('active','invited')",(item['id'],))] if item['membership']=='active' else []
                result.append(item)
        return result
    def require_owner(self,cid,uid):
        ch=self.channel(cid)
        if not ch or ch['owner_id']!=uid or ch['status']!='open':raise PermissionError('방 소유자만 열린 대화를 관리할 수 있어요.')
        return ch
    def invite(self,cid,uid,target):
        self.require_owner(cid,uid)
        if uid==target or not self.user_exists(target):raise ValueError('초대할 사용자를 확인하세요.')
        existing=self.member(cid,target)
        if existing and existing['state']=='active':raise ValueError('이미 참여한 사용자예요.')
        with self.connect() as c:c.execute("INSERT INTO channel_members(channel_id,user_id,state,role,invited_by) VALUES (?,?,'invited','member',?) ON CONFLICT(channel_id,user_id) DO UPDATE SET state='invited',invited_by=excluded.invited_by",(cid,target,uid))
    def accept(self,cid,uid):
        ch=self.channel(cid);member=self.member(cid,uid)
        if not ch or ch['status']!='open' or not member or member['state']!='invited':raise PermissionError('유효한 초대가 필요해요.')
        with self.connect() as c:c.execute("UPDATE channel_members SET state='active' WHERE channel_id=? AND user_id=?",(cid,uid))
    def leave(self,cid,uid):
        ch=self.channel(cid);member=self.member(cid,uid)
        if not ch or not member:raise PermissionError('참여 권한이 없어요.')
        if ch['owner_id']==uid:raise PermissionError('소유자는 대화 종료를 선택하세요.')
        with self.connect() as c:c.execute("UPDATE channel_members SET state='left' WHERE channel_id=? AND user_id=?",(cid,uid))
    def close_channel(self,cid,uid):
        self.require_owner(cid,uid)
        with self.connect() as c:
            c.execute("UPDATE chat_channels SET status='closed' WHERE id=?",(cid,))
            c.execute("UPDATE channel_members SET state='left' WHERE channel_id=? AND state='invited'",(cid,))
    def save_chat(self,chat):
        with self.connect() as c:
            cursor=c.execute('INSERT INTO chat_messages(id,channel,user_id,nickname,text,time,mentions) VALUES (?,?,?,?,?,?,?) RETURNING seq',(chat['id'],chat['channel'],chat['user_id'],chat['nickname'],chat['text'],chat['time'],json.dumps(chat['mentions'])))
            chat['seq']=cursor.fetchone()['seq']
        return chat
    def history(self,cid,limit=100):
        with self.connect() as c:rows=c.execute('SELECT * FROM chat_messages WHERE channel=? ORDER BY seq DESC LIMIT ?',(cid,limit)).fetchall()
        return [{**dict(row),'mentions':json.loads(row['mentions']),'message_type':('world' if row['channel']=='world' else 'channel' if row['channel'].startswith('channel:') else 'zone' if row['channel'].startswith('zone:') else 'announcement' if row['channel']=='announcements' else 'private')} for row in reversed(rows)]

    def issue_session(self,uid,auth_kind='password'):
        token=secrets.token_urlsafe(32)
        with self.connect() as c:c.execute('INSERT INTO sessions(token_hash,user_id,expires,auth_kind) VALUES (?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,time.time()+86400,auth_kind))
        return token,self.user_for(token)

    @property
    def errors(self):
        import psycopg
        return (sqlite3.Error,psycopg.Error)
    def ping(self):
        with self.connect() as c:return c.execute('SELECT 1').fetchone()[0]==1
