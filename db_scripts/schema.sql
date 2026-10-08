-- REFERENCE ONLY. The app does not read this file.
-- The real schema lives in src/snip_url/repo/db.py (SCHEMA).
-- All timestamps are ISO 8601 UTC text. Booleans are INTEGER 0/1.

CREATE TABLE IF NOT EXISTS api_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_hash TEXT NOT NULL UNIQUE,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    links_created INTEGER NOT NULL DEFAULT 0,
    times_rate_limited INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS link_visitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_hash TEXT NOT NULL UNIQUE,
    user_agent TEXT NOT NULL DEFAULT '',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    visit_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS short_links (
    code TEXT PRIMARY KEY,
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_custom_alias INTEGER NOT NULL DEFAULT 0,
    created_by_client INTEGER REFERENCES api_clients(id),
    last_clicked_at TEXT
);

CREATE TABLE IF NOT EXISTS click_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL REFERENCES short_links(code),
    clicked_at TEXT NOT NULL,
    visitor INTEGER REFERENCES link_visitors(id),
    user_agent TEXT,
    referrer TEXT
);
CREATE INDEX IF NOT EXISTS idx_click_events_code ON click_events(code);

CREATE TABLE IF NOT EXISTS daily_link_stats (
    code TEXT NOT NULL REFERENCES short_links(code),
    day TEXT NOT NULL,
    click_count INTEGER NOT NULL DEFAULT 0,
    unique_visitors INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (code, day)
);
