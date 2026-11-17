PHASE4="""
CREATE TABLE IF NOT EXISTS game_settings(game_id TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS game_sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),game_id TEXT NOT NULL,request_id TEXT NOT NULL,seed TEXT NOT NULL,config TEXT NOT NULL,started_at REAL NOT NULL,expires_at REAL NOT NULL,status TEXT NOT NULL CHECK(status IN ('active','completed','cancelled','expired')),last_input_at REAL NOT NULL DEFAULT 0,UNIQUE(user_id,request_id));
CREATE UNIQUE INDEX IF NOT EXISTS one_active_game ON game_sessions(user_id) WHERE status='active';
CREATE INDEX IF NOT EXISTS games_user_started ON game_sessions(user_id,started_at);
CREATE TABLE IF NOT EXISTS game_inputs(session_id TEXT NOT NULL REFERENCES game_sessions(id),event_id TEXT NOT NULL,cell INTEGER NOT NULL,wave INTEGER NOT NULL,challenge TEXT NOT NULL,received_at REAL NOT NULL,hit INTEGER NOT NULL CHECK(hit IN (0,1)),PRIMARY KEY(session_id,event_id));
CREATE UNIQUE INDEX IF NOT EXISTS one_hit_per_mole ON game_inputs(session_id,wave) WHERE hit=1;
CREATE TABLE IF NOT EXISTS game_results(session_id TEXT PRIMARY KEY REFERENCES game_sessions(id),score INTEGER NOT NULL,hits INTEGER NOT NULL,finished_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS game_reward_transactions(session_id TEXT PRIMARY KEY REFERENCES game_results(session_id),coin_transaction_id TEXT NOT NULL UNIQUE REFERENCES coin_transactions(id),reward_date TEXT NOT NULL,reason TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS game_reward_date ON game_reward_transactions(reward_date);
CREATE TABLE IF NOT EXISTS game_validation_events(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),session_id TEXT,reason TEXT NOT NULL,created_at REAL NOT NULL);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (6);
"""
