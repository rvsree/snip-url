import importlib.util
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from snip_url.common.config import DEFAULT_IP_HASH_SALT
from snip_url.repo import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = PROJECT_ROOT / "db_scripts" / "seed_data.py"
SCHEMA_PATH = PROJECT_ROOT / "db_scripts" / "schema.sql"
TABLES = ["short_links", "click_events", "link_visitors", "api_clients", "daily_link_stats"]
TODAY = date(2026, 6, 15)


# Load the seed script as a module from its file path.
def load_seed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_data_under_test", str(SEED_PATH))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Run a SELECT and return all rows.
def query(db_path: str, sql: str) -> list:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# Dump all five tables, ordered, for comparison.
def dump_tables(db_path: str) -> dict:
    result = {}
    for table in TABLES:
        result[table] = query(db_path, "SELECT * FROM " + table + " ORDER BY 1, 2")
    return result


# AC19: the seed creates the exact counts and consistent daily stats.
def test_AC19_seed_creates_expected_counts(tmp_path: Path) -> None:
    module = load_seed_module()
    db_path = str(tmp_path / "seed.db")
    counts = module.run_seed(db_path, DEFAULT_IP_HASH_SALT, TODAY)
    assert counts["short_links"] == 30
    assert counts["click_events"] == 300
    assert counts["link_visitors"] == 40
    assert counts["api_clients"] == 5
    custom = query(db_path, "SELECT COUNT(*) FROM short_links WHERE is_custom_alias = 1")
    assert custom[0][0] >= 5
    bounds = query(db_path, "SELECT MIN(clicked_at), MAX(clicked_at) FROM click_events")
    first_day = (TODAY - timedelta(days=13)).isoformat()
    assert bounds[0][0][:10] >= first_day
    assert bounds[0][1][:10] <= TODAY.isoformat()
    expected = query(
        db_path,
        "SELECT code, substr(clicked_at, 1, 10), COUNT(*), COUNT(DISTINCT visitor) "
        "FROM click_events GROUP BY code, substr(clicked_at, 1, 10) ORDER BY 1, 2",
    )
    actual = query(
        db_path,
        "SELECT code, day, click_count, unique_visitors FROM daily_link_stats ORDER BY 1, 2",
    )
    assert actual == expected
    assert counts["daily_link_stats"] == len(expected)


# AC19: no plain fake IP is stored.
def test_AC19_seed_stores_only_hashed_ips(tmp_path: Path) -> None:
    module = load_seed_module()
    db_path = str(tmp_path / "seed_hash.db")
    module.run_seed(db_path, DEFAULT_IP_HASH_SALT, TODAY)
    hashes = query(db_path, "SELECT ip_hash FROM link_visitors")
    hashes += query(db_path, "SELECT ip_hash FROM api_clients")
    for row in hashes:
        assert len(row[0]) == 64
        assert not row[0].startswith("10.0.0.")
        assert not row[0].startswith("192.168.")


# AC20: two empty databases get identical seed data.
def test_AC20_seed_is_identical_on_two_databases(tmp_path: Path) -> None:
    module = load_seed_module()
    first = str(tmp_path / "one.db")
    second = str(tmp_path / "two.db")
    module.run_seed(first, DEFAULT_IP_HASH_SALT, TODAY)
    module.run_seed(second, DEFAULT_IP_HASH_SALT, TODAY)
    assert dump_tables(first) == dump_tables(second)


# AC21: a second run adds and deletes nothing and still prints counts.
def test_AC21_seed_rerun_adds_and_deletes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    module = load_seed_module()
    db_path = str(tmp_path / "rerun.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.delenv("IP_HASH_SALT", raising=False)
    module.main()
    capsys.readouterr()
    before = dump_tables(db_path)
    module.main()
    printed = capsys.readouterr().out
    after = dump_tables(db_path)
    assert before == after
    for table in TABLES:
        assert table + ":" in printed


# AC22: main prints one "<table>: <n>" line per table.
def test_AC22_seed_prints_count_per_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    module = load_seed_module()
    db_path = str(tmp_path / "print.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.delenv("IP_HASH_SALT", raising=False)
    module.main()
    lines = []
    for line in capsys.readouterr().out.splitlines():
        if line.strip() != "":
            lines.append(line.strip())
    assert len(lines) == 5
    wanted = {"short_links": 30, "click_events": 300, "link_visitors": 40,
              "api_clients": 5}
    for index in range(5):
        name, number = lines[index].split(": ")
        assert name == TABLES[index]
        assert int(number) >= 0
        if name in wanted:
            assert int(number) == wanted[name]


# Return table name to sorted column names for a database file.
def columns_by_table(db_path: str) -> dict:
    result = {}
    for table in TABLES:
        rows = query(db_path, "PRAGMA table_info(" + table + ")")
        names = []
        for row in rows:
            names.append(row[1])
        result[table] = sorted(names)
    return result


# AC23: schema.sql defines the five tables and matches init_db.
def test_AC23_schema_sql_defines_five_tables(tmp_path: Path) -> None:
    sql_text = SCHEMA_PATH.read_text(encoding="utf-8")
    sql_db = str(tmp_path / "from_sql.db")
    conn = sqlite3.connect(sql_db)
    try:
        conn.executescript(sql_text)
        conn.commit()
    finally:
        conn.close()
    app_db = str(tmp_path / "from_app.db")
    db.init_db(app_db)
    assert columns_by_table(sql_db) == columns_by_table(app_db)
    for table in TABLES:
        assert len(columns_by_table(sql_db)[table]) > 0


# AC23: the app source never refers to schema.sql.
def test_AC23_app_does_not_use_schema_sql() -> None:
    for path in (PROJECT_ROOT / "src" / "snip_url").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "schema.sql" not in text
