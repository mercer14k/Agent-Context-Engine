CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO meta VALUES ('schema_version','1');
CREATE TABLE IF NOT EXISTS events (
 event_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, mode TEXT NOT NULL,
 run_id TEXT NOT NULL, kind TEXT NOT NULL, timestamp REAL NOT NULL,
 received REAL NOT NULL, request_id TEXT, revision INTEGER NOT NULL,
 data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_scope ON events(workspace,mode,run_id,kind);
CREATE TABLE IF NOT EXISTS settings (workspace TEXT PRIMARY KEY, data TEXT NOT NULL);
