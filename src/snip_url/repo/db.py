import os
import sqlite3

SCHEMA = """
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
"""

NEW_LINK_COLUMNS = (
    ("is_custom_alias", "INTEGER NOT NULL DEFAULT 0"),
    ("created_by_client", "INTEGER REFERENCES api_clients(id)"),
    ("last_clicked_at", "TEXT"),
)

NEW_CLICK_COLUMNS = (
    ("visitor", "INTEGER REFERENCES link_visitors(id)"),
    ("user_agent", "TEXT"),
    ("referrer", "TEXT"),
)


# Open a sqlite3 connection with Row factory and foreign keys on.
def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Commit the current transaction.
def commit(conn: sqlite3.Connection) -> None:
    conn.commit()


# Roll back the current transaction.
def rollback(conn: sqlite3.Connection) -> None:
    conn.rollback()


# Return True if the table exists.
def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    if row is None:
        return False
    return True


# Return True if the table has the column.
def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
    for row in rows:
        if row["name"] == column:
            return True
    return False


# Rename old tables links and clicks to the new names, if needed.
def rename_old_tables(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "links") and not table_exists(conn, "short_links"):
        conn.execute("ALTER TABLE links RENAME TO short_links")
    if table_exists(conn, "clicks") and not table_exists(conn, "click_events"):
        conn.execute("ALTER TABLE clicks RENAME TO click_events")
    conn.execute("DROP INDEX IF EXISTS idx_clicks_code")


# Add the new columns to migrated tables when they are missing.
def add_missing_columns(conn: sqlite3.Connection) -> None:
    for name, definition in NEW_LINK_COLUMNS:
        if not column_exists(conn, "short_links", name):
            conn.execute("ALTER TABLE short_links ADD COLUMN " + name + " " + definition)
    for name, definition in NEW_CLICK_COLUMNS:
        if not column_exists(conn, "click_events", name):
            conn.execute("ALTER TABLE click_events ADD COLUMN " + name + " " + definition)


# Migrate old tables, create missing tables and columns (idempotent).
def init_db(db_path: str) -> None:
    folder = os.path.dirname(db_path)
    if folder != "":
        os.makedirs(folder, exist_ok=True)
    conn = get_connection(db_path)
    try:
        rename_old_tables(conn)
        conn.executescript(SCHEMA)
        add_missing_columns(conn)
        commit(conn)
    finally:
        conn.close()
