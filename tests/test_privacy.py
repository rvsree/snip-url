import hashlib
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snip_url.common.config import DEFAULT_IP_HASH_SALT, Settings, load_settings
from snip_url.main import create_app
from snip_url.services.privacy import hash_ip

URL = "https://example.com/page"
TABLES = ["short_links", "click_events", "link_visitors", "api_clients", "daily_link_stats"]


# Compute the expected salted hash for the TestClient host.
def expected_hash(salt: str) -> str:
    return hashlib.sha256((salt + ":testclient").encode("utf-8")).hexdigest()


# Create a link and open it once; return the code.
def create_and_open(client: TestClient) -> str:
    response = client.post("/api/links", json={"url": URL})
    assert response.status_code == 201
    code = response.json()["code"]
    opened = client.get("/" + code, headers={"User-Agent": "UA", "Referer": "https://r/"})
    assert opened.status_code == 302
    return code


# Read one column from a table as a list of values.
def read_column(db_path: str, table: str, column: str) -> list:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT " + column + " FROM " + table).fetchall()
    finally:
        conn.close()
    values = []
    for row in rows:
        values.append(row[0])
    return values


# AC11: no text value in any table contains the plain IP.
def test_AC11_no_plain_ip_in_any_column(
    client: TestClient, settings: Settings
) -> None:
    create_and_open(client)
    conn = sqlite3.connect(settings.db_path)
    try:
        for table in TABLES:
            rows = conn.execute("SELECT * FROM " + table).fetchall()
            for row in rows:
                for value in row:
                    if isinstance(value, str):
                        assert "testclient" not in value
                        assert "127.0.0.1" not in value
    finally:
        conn.close()


# AC11: stored hashes equal sha256(salt:ip).
def test_AC11_stored_hash_matches_salted_sha256(
    client: TestClient, settings: Settings
) -> None:
    create_and_open(client)
    want = expected_hash(DEFAULT_IP_HASH_SALT)
    assert read_column(settings.db_path, "link_visitors", "ip_hash") == [want]
    assert read_column(settings.db_path, "api_clients", "ip_hash") == [want]


# AC11: hash_ip is a stable 64-char lowercase sha256 hex string.
def test_AC11_hash_ip_is_stable_sha256() -> None:
    first = hash_ip("testclient", "salt-a")
    second = hash_ip("testclient", "salt-a")
    assert first == second
    assert first == expected_hash("salt-a")
    assert len(first) == 64
    assert first == first.lower()


# AC12: with IP_HASH_SALT unset or empty the default salt is used.
def test_AC12_default_salt_used_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IP_HASH_SALT", raising=False)
    assert load_settings().ip_hash_salt == DEFAULT_IP_HASH_SALT
    monkeypatch.setenv("IP_HASH_SALT", "")
    assert load_settings().ip_hash_salt == DEFAULT_IP_HASH_SALT
    monkeypatch.setenv("IP_HASH_SALT", "other-salt")
    assert load_settings().ip_hash_salt == "other-salt"


# AC12: a different salt gives a different hash for the same IP.
def test_AC12_different_salt_gives_different_hash() -> None:
    one = hash_ip("10.0.0.1", "salt-one")
    two = hash_ip("10.0.0.1", "salt-two")
    assert one != two


# AC12: the app stores the hash made with its own configured salt.
def test_AC12_app_with_custom_salt_stores_that_hash(tmp_path: Path) -> None:
    db_path = str(tmp_path / "salt.db")
    settings = Settings(
        db_path=db_path, base_url="http://testserver", ip_hash_salt="my-custom-salt"
    )
    with TestClient(create_app(settings), follow_redirects=False) as client:
        create_and_open(client)
    want = expected_hash("my-custom-salt")
    assert read_column(db_path, "link_visitors", "ip_hash") == [want]
    assert read_column(db_path, "api_clients", "ip_hash") == [want]
    assert want != expected_hash(DEFAULT_IP_HASH_SALT)
