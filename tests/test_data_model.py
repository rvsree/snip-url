import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from snip_url.common.config import Settings
from snip_url.main import create_app

OLD_SCHEMA = """
CREATE TABLE links (
    code TEXT PRIMARY KEY,
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL REFERENCES links(code),
    clicked_at TEXT NOT NULL
);
CREATE INDEX idx_clicks_code ON clicks(code);
"""

EXPECTED_COLUMNS = {
    "short_links": [
        "code",
        "original_url",
        "created_at",
        "is_custom_alias",
        "created_by_client",
        "last_clicked_at",
    ],
    "click_events": ["id", "code", "clicked_at", "visitor", "user_agent", "referrer"],
    "link_visitors": ["id", "ip_hash", "user_agent", "first_seen", "last_seen", "visit_count"],
    "api_clients": [
        "id",
        "ip_hash",
        "first_seen",
        "last_seen",
        "links_created",
        "times_rate_limited",
    ],
    "daily_link_stats": ["code", "day", "click_count", "unique_visitors"],
}


# Build a database in the old (pre-004) layout with some rows.
def make_old_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(OLD_SCHEMA)
        conn.execute(
            "INSERT INTO links (code, original_url, created_at) VALUES (?, ?, ?)",
            ("old1", "https://example.com/1", "2026-01-01T10:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO links (code, original_url, created_at) VALUES (?, ?, ?)",
            ("old2", "https://example.com/2", "2026-01-02T10:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO clicks (code, clicked_at) VALUES (?, ?)",
            ("old1", "2026-01-03T10:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO clicks (code, clicked_at) VALUES (?, ?)",
            ("old1", "2026-01-04T10:00:00+00:00"),
        )
        conn.commit()
    finally:
        conn.close()


# Return all table names of a database file.
def table_names(db_path: Path) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        conn.close()
    names = []
    for row in rows:
        names.append(row[0])
    return names


# Return the column names of one table.
def column_names(db_path: Path, table: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
    finally:
        conn.close()
    names = []
    for row in rows:
        names.append(row[1])
    return names


# Dump every row of every user table for comparison.
def dump_all(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        result = {}
        for name in sorted(table_names(db_path)):
            if name.startswith("sqlite_"):
                continue
            rows = conn.execute("SELECT * FROM " + name + " ORDER BY 1, 2").fetchall()
            result[name] = rows
    finally:
        conn.close()
    return result


# Start the app once on a database file and stop it.
def start_app(db_path: Path) -> None:
    settings = Settings(db_path=str(db_path), base_url="http://testserver")
    with TestClient(create_app(settings)):
        pass


# AC1: an old database is migrated by renaming, with no data loss.
def test_AC1_old_database_is_migrated_without_data_loss(tmp_path: Path) -> None:
    db_path = tmp_path / "old.db"
    make_old_db(db_path)
    start_app(db_path)
    names = table_names(db_path)
    assert "short_links" in names
    assert "click_events" in names
    assert "links" not in names
    assert "clicks" not in names
    conn = sqlite3.connect(str(db_path))
    try:
        links = conn.execute(
            "SELECT code, original_url, created_at, is_custom_alias, "
            "created_by_client, last_clicked_at FROM short_links ORDER BY code"
        ).fetchall()
        clicks = conn.execute(
            "SELECT code, clicked_at, visitor, user_agent, referrer "
            "FROM click_events ORDER BY id"
        ).fetchall()
        fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    assert links == [
        ("old1", "https://example.com/1", "2026-01-01T10:00:00+00:00", 0, None, None),
        ("old2", "https://example.com/2", "2026-01-02T10:00:00+00:00", 0, None, None),
    ]
    assert clicks == [
        ("old1", "2026-01-03T10:00:00+00:00", None, None, None),
        ("old1", "2026-01-04T10:00:00+00:00", None, None, None),
    ]
    assert fk_problems == []


# AC1: the migrated database still works for new requests.
def test_AC1_migrated_database_accepts_new_requests(tmp_path: Path) -> None:
    db_path = tmp_path / "old2.db"
    make_old_db(db_path)
    settings = Settings(db_path=str(db_path), base_url="http://testserver")
    with TestClient(create_app(settings), follow_redirects=False) as client:
        response = client.get("/old1")
        assert response.status_code == 302
        stats = client.get("/api/links/old1/stats")
        assert stats.status_code == 200
        assert stats.json()["click_count"] == 3


# AC2: a second startup changes nothing.
def test_AC2_second_startup_changes_nothing(tmp_path: Path) -> None:
    db_path = tmp_path / "again.db"
    make_old_db(db_path)
    start_app(db_path)
    before = dump_all(db_path)
    start_app(db_path)
    after = dump_all(db_path)
    assert before == after
    assert len(before["short_links"]) == 2
    assert len(before["click_events"]) == 2


# AC3: a fresh database has the five tables with the planned columns.
def test_AC3_fresh_db_has_five_tables_with_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.db"
    start_app(db_path)
    names = table_names(db_path)
    for table in EXPECTED_COLUMNS:
        assert table in names
        actual = column_names(db_path, table)
        assert sorted(actual) == sorted(EXPECTED_COLUMNS[table])
    assert "links" not in names
    assert "clicks" not in names
