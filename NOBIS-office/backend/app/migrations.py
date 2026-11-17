"""Additive versioned migrations. Existing Phase 1 users/sessions are preserved."""
PHASE2 = """
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS avatar_profiles(user_id TEXT PRIMARY KEY REFERENCES users(id),avatar_id TEXT NOT NULL DEFAULT 'placeholder-v1',palette TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS user_status(user_id TEXT PRIMARY KEY REFERENCES users(id),work_status TEXT NOT NULL,message TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS zone_presence(user_id TEXT PRIMARY KEY REFERENCES users(id),scope TEXT NOT NULL DEFAULT 'office',zone TEXT NOT NULL DEFAULT 'office',x REAL NOT NULL,y REAL NOT NULL,presence TEXT NOT NULL DEFAULT 'offline',action TEXT NOT NULL DEFAULT 'idle',active_object TEXT,return_x REAL,return_y REAL);
CREATE TABLE IF NOT EXISTS chat_channels(id TEXT PRIMARY KEY,kind TEXT NOT NULL,name TEXT NOT NULL,owner_id TEXT REFERENCES users(id),meeting_id TEXT,status TEXT NOT NULL DEFAULT 'open',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chat_messages(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,channel TEXT NOT NULL REFERENCES chat_channels(id),user_id TEXT NOT NULL REFERENCES users(id),nickname TEXT NOT NULL,text TEXT NOT NULL,time TEXT NOT NULL,mentions TEXT NOT NULL DEFAULT '[]');
CREATE INDEX IF NOT EXISTS messages_channel_sequence ON chat_messages(channel,seq);
CREATE TABLE IF NOT EXISTS channel_members(channel_id TEXT NOT NULL REFERENCES chat_channels(id),user_id TEXT NOT NULL REFERENCES users(id),state TEXT NOT NULL CHECK(state IN ('active','invited','left')),role TEXT NOT NULL DEFAULT 'member',invited_by TEXT REFERENCES users(id),PRIMARY KEY(channel_id,user_id));
CREATE TABLE IF NOT EXISTS personal_rooms(id TEXT PRIMARY KEY,user_id TEXT NOT NULL UNIQUE REFERENCES users(id),name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS room_settings(room_id TEXT PRIMARY KEY REFERENCES personal_rooms(id),dashboard_url TEXT NOT NULL DEFAULT '');
INSERT OR IGNORE INTO user_status SELECT id,work_status,message FROM users;
INSERT OR IGNORE INTO avatar_profiles(user_id) SELECT id FROM users;
INSERT OR IGNORE INTO personal_rooms SELECT 'personal:'||id,id,nickname||'의 방' FROM users;
INSERT OR IGNORE INTO room_settings(room_id) SELECT id FROM personal_rooms;
INSERT OR IGNORE INTO schema_migrations(version) VALUES (2);
"""

PHASE3 = """
CREATE TABLE IF NOT EXISTS personal_homes(id TEXT PRIMARY KEY REFERENCES personal_rooms(id),owner_id TEXT NOT NULL UNIQUE REFERENCES users(id),revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS furniture_catalog(item_id TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS furniture_instances(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id),item_id TEXT NOT NULL REFERENCES furniture_catalog(item_id),acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS instances_owner ON furniture_instances(owner_id);
CREATE TABLE IF NOT EXISTS furniture_placements(instance_id TEXT PRIMARY KEY REFERENCES furniture_instances(id),room_id TEXT NOT NULL REFERENCES personal_homes(id),grid_x INTEGER NOT NULL,grid_y INTEGER NOT NULL,rotation INTEGER NOT NULL CHECK(rotation IN (0,90,180,270)));
CREATE TABLE IF NOT EXISTS user_wallets(user_id TEXT PRIMARY KEY REFERENCES users(id),balance INTEGER NOT NULL CHECK(balance>=0));
CREATE TABLE IF NOT EXISTS shop_purchases(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),request_id TEXT NOT NULL,item_id TEXT NOT NULL REFERENCES furniture_catalog(item_id),instance_id TEXT NOT NULL UNIQUE REFERENCES furniture_instances(id),price INTEGER NOT NULL CHECK(price>=0),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,request_id));
CREATE TABLE IF NOT EXISTS coin_transactions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),amount INTEGER NOT NULL,balance_after INTEGER NOT NULL CHECK(balance_after>=0),kind TEXT NOT NULL,purchase_id TEXT UNIQUE REFERENCES shop_purchases(id),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT OR IGNORE INTO personal_homes(id,owner_id) SELECT id,user_id FROM personal_rooms;
INSERT OR IGNORE INTO schema_migrations(version) VALUES (3);
"""

MULTICHANNEL = """
CREATE TABLE IF NOT EXISTS worlds(id TEXT PRIMARY KEY,name TEXT NOT NULL);
INSERT OR IGNORE INTO worlds VALUES ('nobis','NOBIS World');
CREATE TABLE IF NOT EXISTS world_channels(id TEXT PRIMARY KEY,world_id TEXT NOT NULL REFERENCES worlds(id),name TEXT NOT NULL,capacity INTEGER NOT NULL CHECK(capacity BETWEEN 1 AND 15),enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS channel_locations(user_id TEXT NOT NULL REFERENCES users(id),channel_id TEXT NOT NULL REFERENCES world_channels(id),x REAL NOT NULL,y REAL NOT NULL,PRIMARY KEY(user_id,channel_id));
CREATE TABLE IF NOT EXISTS user_roles(user_id TEXT PRIMARY KEY REFERENCES users(id),role TEXT NOT NULL CHECK(role IN ('user','moderator','admin','super_admin')),assigned_by TEXT REFERENCES users(id),updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT OR IGNORE INTO user_roles(user_id,role) SELECT id,CASE WHEN role IN ('admin','moderator','super_admin') THEN role ELSE 'user' END FROM users;
CREATE TABLE IF NOT EXISTS role_permissions(role TEXT NOT NULL,permission TEXT NOT NULL,PRIMARY KEY(role,permission));
CREATE TABLE IF NOT EXISTS user_chat_preferences(user_id TEXT PRIMARY KEY REFERENCES users(id),chat_bubbles_enabled INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS private_messages(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,sender_id TEXT NOT NULL REFERENCES users(id),recipient_id TEXT NOT NULL REFERENCES users(id),text TEXT NOT NULL,time TEXT NOT NULL,delivery TEXT NOT NULL CHECK(delivery IN ('stored','delivered')));
CREATE INDEX IF NOT EXISTS private_participants ON private_messages(recipient_id,seq);
CREATE TABLE IF NOT EXISTS announcements(id TEXT PRIMARY KEY,author_id TEXT NOT NULL REFERENCES users(id),title TEXT NOT NULL,text TEXT NOT NULL,target_channel_id TEXT REFERENCES world_channels(id),duration_seconds INTEGER NOT NULL,time TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_audit_logs(seq INTEGER PRIMARY KEY AUTOINCREMENT,actor_id TEXT REFERENCES users(id),action TEXT NOT NULL,target_id TEXT,details TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS system_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS user_chat_restrictions(user_id TEXT PRIMARY KEY REFERENCES users(id),until_time REAL NOT NULL,reason TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS user_reports(id TEXT PRIMARY KEY,reporter_id TEXT NOT NULL REFERENCES users(id),target_id TEXT NOT NULL REFERENCES users(id),reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT OR IGNORE INTO announcements SELECT id,user_id,'이전 공지',text,NULL,8,time FROM chat_messages WHERE channel='announcements';
INSERT OR IGNORE INTO schema_migrations(version) VALUES (4);
"""
