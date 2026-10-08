import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snip_url.common.config import Settings, load_settings
from snip_url.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# List table names in a SQLite file.
def list_tables(db_path: Path) -> list[str]:
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


# AC18: importing the app creates no database file or data folder.
def test_AC18_import_creates_no_database_file(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["DATABASE_PATH"] = str(tmp_path / "sub" / "import_test.db")
    env.pop("PYTHONPATH", None)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    result = subprocess.run(
        [sys.executable, "-I", "-c", "import snip_url.main"],
        cwd=str(work_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    found = []
    for path in tmp_path.rglob("*"):
        if path.suffix == ".db" or path.name == "data" or path.name == "sub":
            found.append(str(path))
    assert found == []


# AC19: startup creates a missing folder, the db file and the tables.
def test_AC19_startup_creates_missing_folder_and_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "missing" / "deeper" / "app.db"
    settings = Settings(db_path=str(db_file), base_url="http://testserver")
    app = create_app(settings)
    assert not db_file.exists()
    with TestClient(app):
        assert db_file.exists()
    tables = list_tables(db_file)
    assert "links" in tables
    assert "clicks" in tables


# AC20: with DATABASE_PATH unset the database is data/snip_url.db.
def test_AC20_default_path_is_data_snip_url_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    settings = load_settings()
    assert settings.db_path.replace("\\", "/") == "data/snip_url.db"
    app = create_app(settings)
    with TestClient(app):
        pass
    assert (tmp_path / "data" / "snip_url.db").exists()


# AC20: DATABASE_PATH from the environment is used by load_settings.
def test_AC20_database_path_env_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = str(tmp_path / "custom.db")
    monkeypatch.setenv("DATABASE_PATH", target)
    assert load_settings().db_path == target


# AC21: the fixture app uses a database under tmp_path only.
def test_AC21_tests_use_tmp_database_only(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    db_path = Path(settings.db_path).resolve()
    assert tmp_path.resolve() in db_path.parents
    assert db_path.exists()
    assert not (PROJECT_ROOT / "data" / "t.db").exists()
    assert not (PROJECT_ROOT / "t.db").exists()


# AC22: the README documents alias, the rate limit and DATABASE_PATH.
def test_AC22_readme_mentions_alias_rate_limit_and_database_path() -> None:
    text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ["alias", "429", "Retry-After", "DATABASE_PATH"]:
        assert needle in text
