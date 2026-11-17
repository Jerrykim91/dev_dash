ROOM_SCHEMA='''
CREATE TABLE IF NOT EXISTS room_definitions(room_type TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS room_instances(id TEXT PRIMARY KEY,room_type TEXT NOT NULL REFERENCES room_definitions(room_type),channel_id TEXT NOT NULL REFERENCES world_channels(id),room_id TEXT NOT NULL,owner_id TEXT REFERENCES users(id),access_policy TEXT NOT NULL,max_occupancy INTEGER NOT NULL CHECK(max_occupancy>0),UNIQUE(channel_id,room_type,room_id));
CREATE TABLE IF NOT EXISTS room_portals(id TEXT PRIMARY KEY,from_room_type TEXT NOT NULL,to_room_type TEXT NOT NULL REFERENCES room_definitions(room_type),data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS room_presence(user_id TEXT NOT NULL REFERENCES users(id),channel_id TEXT NOT NULL,room_instance_id TEXT NOT NULL REFERENCES room_instances(id),room_type TEXT NOT NULL,x REAL NOT NULL,y REAL NOT NULL,updated_at REAL NOT NULL,PRIMARY KEY(user_id,channel_id));
INSERT OR IGNORE INTO schema_migrations(version) VALUES(10);
'''
