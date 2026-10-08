import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snip_url.common.config import Settings
from snip_url.main import create_app


# Settings that point at a temporary SQLite file.
@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(db_path=str(tmp_path / "t.db"), base_url="http://testserver")


# A test client that does not follow redirects.
@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    return TestClient(app, follow_redirects=False)


# Count rows in a table of the temporary database.
def count_rows(db_path: str, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()
        return int(row[0])
    finally:
        conn.close()


# Assert a response body has the standard error shape.
def assert_error_shape(body: dict, code: str) -> None:
    assert "error" in body
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"] != ""
