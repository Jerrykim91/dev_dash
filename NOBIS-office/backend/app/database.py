from .rooms_schema import ROOM_SCHEMA
"""Small PostgreSQL adapter for the existing SQL repository boundary.
SQLite remains supported. Only fixed application SQL is translated, never user input.
"""
import re
from .migrations import PHASE2,PHASE3,MULTICHANNEL
from .games.schema import PHASE4
from .community.schema import SOCIAL_SCHEMA
from .integration.schema import PHASE6
from .collectibles.schema import COLLECTIBLES_SCHEMA,COIN_GACHA_SCHEMA

class Record(dict):
    def __getitem__(self,key):return tuple(self.values())[key] if isinstance(key,int) else super().__getitem__(key)

def record_row(cursor):
    names=[column.name for column in cursor.description] if cursor.description else []
    return lambda values:Record(zip(names,values))

def postgres_sql(sql,parameters=False):
    q=sql.strip().rstrip(';')
    if q.upper()=='BEGIN IMMEDIATE':return 'SELECT pg_advisory_xact_lock(7135035)'
    if q.upper()=='BEGIN':return 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'
    ignore=bool(re.match(r'INSERT\s+OR\s+IGNORE\b',q,re.I))
    q=re.sub(r'INSERT\s+OR\s+IGNORE\b','INSERT',q,flags=re.I)
    q=q.replace('INTEGER PRIMARY KEY AUTOINCREMENT','BIGSERIAL PRIMARY KEY')
    q=re.sub(r'\bREAL\b','DOUBLE PRECISION',q)
    q=re.sub(r'\browid\b','_rowid',q)
    q=re.sub(r'\bCURRENT_TIMESTAMP\b',"CAST(CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS TEXT)",q)
    if ignore:q+=' ON CONFLICT DO NOTHING'
    if parameters:q=q.replace('%','%%').replace('?','%s')
    return q

class PostgresConnection:
    def __init__(self,connection):self.connection=connection
    def execute(self,sql,params=None):
        parameters=params is not None and len(params)>0
        return self.connection.execute(postgres_sql(sql,parameters),params if parameters else None)
    def executescript(self,sql):
        for statement in sql.split(';'):
            if statement.strip():self.execute(statement)

BASE="""
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,nickname TEXT NOT NULL,work_status TEXT NOT NULL DEFAULT 'working',message TEXT NOT NULL DEFAULT '',role TEXT NOT NULL DEFAULT 'member',disabled INTEGER NOT NULL DEFAULT 0,password_hash TEXT NOT NULL DEFAULT '',account_origin TEXT NOT NULL DEFAULT 'legacy');
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires REAL NOT NULL,auth_kind TEXT NOT NULL DEFAULT 'dev');
"""

def initialize_postgres(repo,runtime_cleanup):
    with repo.connect() as c:
        c.execute('BEGIN IMMEDIATE');c.executescript(BASE);c.executescript(PHASE2);c.executescript(PHASE3)
        for table,column,definition in [('avatar_profiles','parts',"TEXT NOT NULL DEFAULT ''"),('zone_presence','world_id',"TEXT NOT NULL DEFAULT 'nobis'"),('zone_presence','channel_id',"TEXT NOT NULL DEFAULT 'ch1'"),('users','account_origin',"TEXT NOT NULL DEFAULT 'legacy'")]:
            c.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}')
        c.executescript(MULTICHANNEL)
        for table in ('coin_transactions','announcements','user_reports'):c.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS _rowid BIGSERIAL')
        c.execute('INSERT OR IGNORE INTO schema_migrations(version) VALUES (5)')
        c.executescript(PHASE4);c.executescript(SOCIAL_SCHEMA);c.executescript(COLLECTIBLES_SCHEMA);c.executescript(COIN_GACHA_SCHEMA);c.executescript(PHASE6);c.executescript(ROOM_SCHEMA)
        if runtime_cleanup:c.execute("UPDATE zone_presence SET presence='offline'")
        import time
        c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
