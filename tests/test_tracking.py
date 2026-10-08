import hashlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

from snip_url.common.config import DEFAULT_IP_HASH_SALT, Settings
from snip_url.main import create_app
from snip_url.repo import db
from snip_url.services import tracking_service

URL = "https://example.com/page"


# Hash the TestClient host with the default salt, as the plan says.
def client_hash(salt: str = DEFAULT_IP_HASH_SALT) -> str:
    return hashlib.sha256((salt + ":testclient").encode("utf-8")).hexdigest()


# Run a SELECT on the temporary database and return all rows.
def query(db_path: str, sql: str, params: tuple = ()) -> list:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


# Create a link through the API and return its code.
def make_link(client: TestClient, alias: str | None = None) -> str:
    body = {"url": URL}
    if alias is not None:
        body["alias"] = alias
    response = client.post("/api/links", json=body)
    assert response.status_code == 201
    return response.json()["code"]


# Take a snapshot of all click-related data for one code.
def click_snapshot(db_path: str, code: str) -> dict:
    snap = {}
    snap["clicks"] = query(db_path, "SELECT * FROM click_events ORDER BY id")
    snap["visitors"] = query(db_path, "SELECT * FROM link_visitors ORDER BY id")
    snap["stats"] = query(db_path, "SELECT * FROM daily_link_stats ORDER BY code, day")
    snap["last"] = query(
        db_path, "SELECT last_clicked_at FROM short_links WHERE code = ?", (code,)
    )
    return snap


# A stand-in that always fails, used to break one write step.
def explode(*args, **kwargs) -> None:
    raise RuntimeError("boom")


# AC4: alias gives is_custom_alias 1, no alias gives 0.
def test_AC4_custom_alias_flag_true_and_false(
    client: TestClient, settings: Settings
) -> None:
    custom = make_link(client, alias="my-alias")
    plain = make_link(client)
    rows = query(
        settings.db_path, "SELECT code, is_custom_alias FROM short_links ORDER BY code"
    )
    flags = {}
    for row in rows:
        flags[row[0]] = row[1]
    assert flags[custom] == 1
    assert flags[plain] == 0


# AC5: created_by_client points to the hashed IP row and counters move.
def test_AC5_created_by_client_and_counters(
    client: TestClient, settings: Settings
) -> None:
    code1 = make_link(client)
    clients = query(settings.db_path, "SELECT id, ip_hash, links_created FROM api_clients")
    assert len(clients) == 1
    assert clients[0][1] == client_hash()
    assert clients[0][2] == 1
    owner = query(
        settings.db_path,
        "SELECT created_by_client FROM short_links WHERE code = ?",
        (code1,),
    )
    assert owner[0][0] == clients[0][0]
    first_seen = query(settings.db_path, "SELECT last_seen FROM api_clients")[0][0]
    make_link(client)
    after = query(settings.db_path, "SELECT links_created, last_seen FROM api_clients")
    assert after[0][0] == 2
    assert after[0][1] >= first_seen


# AC5: failed validation and alias conflicts do not raise links_created.
def test_AC5_failed_creates_do_not_increase_links_created(
    client: TestClient, settings: Settings
) -> None:
    make_link(client, alias="taken-one")
    bad = client.post("/api/links", json={"url": "nope"})
    assert bad.status_code == 422
    dup = client.post("/api/links", json={"url": URL, "alias": "taken-one"})
    assert dup.status_code == 409
    rows = query(settings.db_path, "SELECT links_created FROM api_clients")
    assert len(rows) == 1
    assert rows[0][0] == 1


# AC6: each 429 raises times_rate_limited by 1.
def test_AC6_rate_limited_counter_increments(
    client: TestClient, settings: Settings
) -> None:
    for _ in range(10):
        response = client.post("/api/links", json={"url": URL})
        assert response.status_code == 201
    for _ in range(2):
        blocked = client.post("/api/links", json={"url": URL})
        assert blocked.status_code == 429
    rows = query(
        settings.db_path, "SELECT links_created, times_rate_limited FROM api_clients"
    )
    assert len(rows) == 1
    assert rows[0][0] == 10
    assert rows[0][1] == 2


# AC7: redirect stores User-Agent and Referer on the click.
def test_AC7_redirect_stores_user_agent_and_referrer(
    client: TestClient, settings: Settings
) -> None:
    code = make_link(client)
    response = client.get(
        "/" + code, headers={"User-Agent": "TestAgent/1.0", "Referer": "https://ref.example/"}
    )
    assert response.status_code == 302
    assert response.headers["location"] == URL
    rows = query(
        settings.db_path,
        "SELECT visitor, user_agent, referrer FROM click_events WHERE code = ?",
        (code,),
    )
    assert len(rows) == 1
    assert rows[0][0] is not None
    assert rows[0][1] == "TestAgent/1.0"
    assert rows[0][2] == "https://ref.example/"


# AC7: missing headers are stored as NULL (click) and empty (visitor).
def test_AC7_missing_headers_stored_empty(
    client: TestClient, settings: Settings
) -> None:
    code = make_link(client)
    response = client.get("/" + code, headers={"User-Agent": ""})
    assert response.status_code == 302
    clicks = query(
        settings.db_path, "SELECT user_agent, referrer FROM click_events"
    )
    assert len(clicks) == 1
    assert clicks[0][1] is None
    assert clicks[0][0] in (None, "")
    visitors = query(settings.db_path, "SELECT user_agent FROM link_visitors")
    assert visitors[0][0] == ""


# AC8: one visitor row per hash, counts and latest user agent.
def test_AC8_one_visitor_row_per_hash_with_counts(
    client: TestClient, settings: Settings
) -> None:
    code = make_link(client)
    agents = ["Agent/1", "Agent/2", "Agent/3"]
    for agent in agents:
        response = client.get("/" + code, headers={"User-Agent": agent})
        assert response.status_code == 302
    rows = query(
        settings.db_path,
        "SELECT ip_hash, visit_count, first_seen, last_seen, user_agent FROM link_visitors",
    )
    assert len(rows) == 1
    assert rows[0][0] == client_hash()
    assert rows[0][1] == 3
    assert rows[0][3] >= rows[0][2]
    assert rows[0][4] == "Agent/3"


# AC9: last_clicked_at is NULL before and equals the latest click after.
def test_AC9_last_clicked_at_set_on_redirect(
    client: TestClient, settings: Settings
) -> None:
    code = make_link(client)
    before = query(
        settings.db_path, "SELECT last_clicked_at FROM short_links WHERE code = ?", (code,)
    )
    assert before[0][0] is None
    client.get("/" + code)
    client.get("/" + code)
    after = query(
        settings.db_path, "SELECT last_clicked_at FROM short_links WHERE code = ?", (code,)
    )
    latest = query(settings.db_path, "SELECT MAX(clicked_at) FROM click_events")
    assert after[0][0] is not None
    assert after[0][0] == latest[0][0]


# AC10: daily stats count clicks and unique visitors per link and day.
def test_AC10_daily_stats_clicks_and_unique_visitors(
    client: TestClient, settings: Settings
) -> None:
    code_a = make_link(client)
    code_b = make_link(client)
    conn = db.get_connection(settings.db_path)
    try:
        now = "2026-03-05T10:00:00+00:00"
        later = "2026-03-05T11:00:00+00:00"
        tracking_service.record_click(conn, code_a, now, "hash-x", None, None)
        tracking_service.record_click(conn, code_a, later, "hash-x", None, None)
        stats = query(
            settings.db_path,
            "SELECT click_count, unique_visitors FROM daily_link_stats "
            "WHERE code = ? AND day = ?",
            (code_a, "2026-03-05"),
        )
        assert stats == [(2, 1)]
        tracking_service.record_click(conn, code_a, later, "hash-y", None, None)
        stats = query(
            settings.db_path,
            "SELECT click_count, unique_visitors FROM daily_link_stats "
            "WHERE code = ? AND day = ?",
            (code_a, "2026-03-05"),
        )
        assert stats == [(3, 2)]
        tracking_service.record_click(conn, code_b, later, "hash-x", None, None)
        other = query(
            settings.db_path,
            "SELECT click_count, unique_visitors FROM daily_link_stats WHERE code = ?",
            (code_b,),
        )
        assert other == [(1, 1)]
        next_day = "2026-03-06T09:00:00+00:00"
        tracking_service.record_click(conn, code_a, next_day, "hash-x", None, None)
        day2 = query(
            settings.db_path,
            "SELECT click_count, unique_visitors FROM daily_link_stats "
            "WHERE code = ? AND day = ?",
            (code_a, "2026-03-06"),
        )
        assert day2 == [(1, 1)]
    finally:
        conn.close()


# AC10: a failure in the last write (daily stat) saves nothing.
def test_AC10_failure_midway_saves_no_click_data(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = make_link(client)
    client.get("/" + code)
    before = click_snapshot(settings.db_path, code)
    monkeypatch.setattr("snip_url.repo.stats_repo.bump_daily_stat", explode)
    conn = db.get_connection(settings.db_path)
    try:
        with pytest.raises(RuntimeError):
            tracking_service.record_click(
                conn, code, "2026-03-05T10:00:00+00:00", client_hash(), "UA", "ref"
            )
    finally:
        conn.close()
    after = click_snapshot(settings.db_path, code)
    assert after == before


# AC10: a failure through the redirect route saves nothing either.
def test_AC10_failure_midway_via_redirect_saves_nothing(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(settings)
    with TestClient(
        app, follow_redirects=False, raise_server_exceptions=False
    ) as client:
        code = make_link(client)
        before = click_snapshot(settings.db_path, code)
        monkeypatch.setattr("snip_url.repo.stats_repo.bump_daily_stat", explode)
        response = client.get("/" + code, headers={"User-Agent": "X"})
        assert response.status_code == 500
        after = click_snapshot(settings.db_path, code)
        assert after == before
        assert after["last"][0][0] is None


# AC10: a failure in the first write (click insert) saves nothing.
def test_AC10_failure_on_insert_click_saves_nothing(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = make_link(client)
    client.get("/" + code)
    before = click_snapshot(settings.db_path, code)
    monkeypatch.setattr("snip_url.repo.link_repo.insert_click", explode)
    conn = db.get_connection(settings.db_path)
    try:
        with pytest.raises(RuntimeError):
            tracking_service.record_click(
                conn, code, "2026-03-05T10:00:00+00:00", client_hash(), "UA", None
            )
        with pytest.raises(RuntimeError):
            tracking_service.record_click(
                conn, code, "2026-03-05T10:00:00+00:00", "brand-new-hash", "UA", None
            )
    finally:
        conn.close()
    after = click_snapshot(settings.db_path, code)
    assert after == before
    assert after["visitors"][0][5] == 1


# AC10: on success the click, visitor, last_clicked_at and daily stat are all saved.
def test_AC10_success_saves_all_four(
    client: TestClient, settings: Settings
) -> None:
    code = make_link(client)
    response = client.get("/" + code, headers={"User-Agent": "UA1"})
    assert response.status_code == 302
    snap = click_snapshot(settings.db_path, code)
    assert len(snap["clicks"]) == 1
    assert len(snap["visitors"]) == 1
    assert len(snap["stats"]) == 1
    assert snap["stats"][0][2] == 1
    assert snap["stats"][0][3] == 1
    assert snap["last"][0][0] == snap["clicks"][0][2]
