"""Explicit offline SQLite -> PostgreSQL copy. Never changes the source file."""
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

TABLES=('users','worlds','world_channels','sessions','avatar_profiles','user_status','zone_presence','chat_channels','channel_members','chat_messages','personal_rooms','room_settings','personal_homes','furniture_catalog','furniture_instances','furniture_placements','user_wallets','shop_purchases','coin_transactions','channel_locations','user_roles','role_permissions','user_chat_preferences','private_messages','announcements','admin_audit_logs','system_settings','user_chat_restrictions','user_reports','schema_migrations','game_settings','game_sessions','game_inputs','game_results','game_reward_transactions','game_validation_events','user_profiles','friend_requests','friendships','user_blocks','social_groups','group_memberships','group_invitations','shared_logs','log_media','log_comments','log_reactions','user_notifications','content_reports','attendance_settings','ticket_balances','daily_attendance','gacha_banners','gacha_pool_versions','gacha_pool_items','gacha_draws','gacha_draw_items','ticket_transactions','collectible_alerts','gacha_coin_pool_items','gacha_coin_draw_items','home_visit_settings','home_visit_requests','home_visit_permissions','home_visitors','multiplayer_game_sessions','multiplayer_game_participants','multiplayer_game_actions','multiplayer_game_rewards','multiplayer_validation_events','integration_reports','room_definitions','room_instances','room_portals','room_presence')
ROWIDS={'coin_transactions','announcements','user_reports'}

def import_sqlite(repo,source):
    if repo.kind!='postgresql':raise ValueError('import-sqlite requires a PostgreSQL DATABASE_URL')
    original=Path(source).resolve()
    if not original.is_file():raise ValueError('SQLite backup source not found')
    from .repository import Repository
    with TemporaryDirectory(prefix='nobis-sqlite-import-') as directory:
        copy=Path(directory)/'source.sqlite3'
        with sqlite3.connect(original.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(copy) as dst:
            if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity check failed')
            if not src.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone():raise ValueError('Not a NOBIS SQLite backup')
            src.backup(dst)
        source_repo=Repository(str(copy));source_repo.initialize(runtime_cleanup=False);counts={}
        with source_repo.connect() as src,repo.connect() as target:
            target.execute('BEGIN IMMEDIATE');target.execute('LOCK TABLE users IN ACCESS EXCLUSIVE MODE')
            if target.execute('SELECT COUNT(*) FROM users').fetchone()[0]:raise ValueError('Target must be an empty PostgreSQL application database; no existing users are overwritten')
            target.execute('TRUNCATE TABLE '+','.join(TABLES)+' RESTART IDENTITY CASCADE')
            for table in TABLES:
                select='rowid AS _rowid,*' if table in ROWIDS else '*'
                rows=src.execute(f'SELECT {select} FROM {table}').fetchall();counts[table]=len(rows)
                if not rows:continue
                columns=list(rows[0].keys());names=','.join('"'+c+'"' for c in columns);placeholders=','.join('?' for _ in columns)
                for row in rows:target.execute(f'INSERT INTO {table} ({names}) VALUES ({placeholders})',tuple(row[c] for c in columns))
            for table,column in [('chat_messages','seq'),('private_messages','seq'),('admin_audit_logs','seq')]+[(t,'_rowid') for t in ROWIDS]:
                target.execute(f"SELECT setval(pg_get_serial_sequence('{table}','{column}'),COALESCE(MAX({column}),1),COUNT(*)>0) FROM {table}")
            from .social import SocialService
            SocialService(repo).audit(target,None,'sqlite_imported',details={'users':counts['users'],'tables':len(counts)})
        return {'imported':True,'counts':counts,'source_unchanged':True}
