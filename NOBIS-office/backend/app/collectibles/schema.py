COLLECTIBLES_SCHEMA="""
CREATE TABLE IF NOT EXISTS attendance_settings(id TEXT PRIMARY KEY,reward_tickets INTEGER NOT NULL CHECK(reward_tickets BETWEEN 0 AND 10));
INSERT OR IGNORE INTO attendance_settings VALUES ('default',1);
CREATE TABLE IF NOT EXISTS ticket_balances(user_id TEXT PRIMARY KEY REFERENCES users(id),balance INTEGER NOT NULL DEFAULT 0 CHECK(balance>=0));
CREATE TABLE IF NOT EXISTS daily_attendance(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),attendance_date TEXT NOT NULL,streak INTEGER NOT NULL CHECK(streak>=1),reward_tickets INTEGER NOT NULL CHECK(reward_tickets>=0),created_at REAL NOT NULL,UNIQUE(user_id,attendance_date));
CREATE TABLE IF NOT EXISTS gacha_banners(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,enabled INTEGER NOT NULL,current_version INTEGER NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS gacha_pool_versions(banner_id TEXT NOT NULL REFERENCES gacha_banners(id),version INTEGER NOT NULL,rarity_weights TEXT NOT NULL,created_at REAL NOT NULL,PRIMARY KEY(banner_id,version));
CREATE TABLE IF NOT EXISTS gacha_pool_items(banner_id TEXT NOT NULL,version INTEGER NOT NULL,item_id TEXT NOT NULL REFERENCES furniture_catalog(item_id),rarity TEXT NOT NULL,weight_bps INTEGER NOT NULL CHECK(weight_bps>0),PRIMARY KEY(banner_id,version,item_id),FOREIGN KEY(banner_id,version) REFERENCES gacha_pool_versions(banner_id,version));
CREATE TABLE IF NOT EXISTS gacha_draws(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),banner_id TEXT NOT NULL REFERENCES gacha_banners(id),pool_version INTEGER NOT NULL,tickets_used INTEGER NOT NULL CHECK(tickets_used IN (1,5)),request_id TEXT NOT NULL,created_at REAL NOT NULL,UNIQUE(user_id,request_id),FOREIGN KEY(banner_id,pool_version) REFERENCES gacha_pool_versions(banner_id,version));
CREATE TABLE IF NOT EXISTS gacha_draw_items(draw_id TEXT NOT NULL REFERENCES gacha_draws(id),position INTEGER NOT NULL,item_id TEXT NOT NULL REFERENCES furniture_catalog(item_id),instance_id TEXT NOT NULL UNIQUE REFERENCES furniture_instances(id),rarity TEXT NOT NULL,PRIMARY KEY(draw_id,position));
CREATE TABLE IF NOT EXISTS ticket_transactions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),amount INTEGER NOT NULL,balance_after INTEGER NOT NULL CHECK(balance_after>=0),kind TEXT NOT NULL CHECK(kind IN ('attendance','draw','admin_grant')),attendance_id TEXT UNIQUE REFERENCES daily_attendance(id),draw_id TEXT UNIQUE REFERENCES gacha_draws(id),request_id TEXT NOT NULL,actor_id TEXT REFERENCES users(id),created_at REAL NOT NULL,UNIQUE(user_id,request_id));
CREATE INDEX IF NOT EXISTS ticket_history_owner ON ticket_transactions(user_id,created_at);
CREATE TABLE IF NOT EXISTS collectible_alerts(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,created_at REAL NOT NULL);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (7);
"""

COIN_GACHA_SCHEMA="""
CREATE TABLE IF NOT EXISTS gacha_coin_pool_items(banner_id TEXT NOT NULL,version INTEGER NOT NULL,coin_amount INTEGER NOT NULL CHECK(coin_amount BETWEEN 10 AND 1000 AND coin_amount % 10=0),weight_bps INTEGER NOT NULL CHECK(weight_bps BETWEEN 1 AND 10000),PRIMARY KEY(banner_id,version,coin_amount),FOREIGN KEY(banner_id,version) REFERENCES gacha_pool_versions(banner_id,version));
CREATE TABLE IF NOT EXISTS gacha_coin_draw_items(draw_id TEXT NOT NULL REFERENCES gacha_draws(id),position INTEGER NOT NULL CHECK(position BETWEEN 0 AND 4),coin_amount INTEGER NOT NULL CHECK(coin_amount BETWEEN 10 AND 1000 AND coin_amount % 10=0),coin_transaction_id TEXT NOT NULL UNIQUE REFERENCES coin_transactions(id),PRIMARY KEY(draw_id,position));
INSERT OR IGNORE INTO schema_migrations(version) VALUES (8);
"""
