import sqlite3
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from conftest import assert_error_shape
from snip_url.common.config import Settings


# Return today's UTC date.
def utc_today() -> date:
    return datetime.now(timezone.utc).date()


# Build an ISO timestamp for a day offset back from today.
def stamp(days_back: int, hour: int = 12) -> str:
    day = utc_today() - timedelta(days=days_back)
    return day.isoformat() + "T" + str(hour).zfill(2) + ":00:00+00:00"


# Insert a link row directly.
def add_link(conn: sqlite3.Connection, code: str, created_back: int = 0) -> None:
    conn.execute(
        "INSERT INTO short_links (code, original_url, created_at) VALUES (?, ?, ?)",
        (code, "https://example.com/" + code, stamp(created_back)),
    )


# Insert a click row directly.
def add_click(conn: sqlite3.Connection, code: str, days_back: int, visitor: int) -> None:
    conn.execute(
        "INSERT INTO click_events (code, clicked_at, visitor) VALUES (?, ?, ?)",
        (code, stamp(days_back), visitor),
    )


# Insert a daily stat row directly.
def add_stat(
    conn: sqlite3.Connection, code: str, days_back: int, clicks: int, uniques: int
) -> None:
    day = (utc_today() - timedelta(days=days_back)).isoformat()
    conn.execute(
        "INSERT INTO daily_link_stats (code, day, click_count, unique_visitors) "
        "VALUES (?, ?, ?, ?)",
        (code, day, clicks, uniques),
    )


# Seed the known-code scenario used by the per-link tests.
def seed_abc(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        add_link(conn, "abc", 20)
        add_click(conn, "abc", 1, 1)
        add_click(conn, "abc", 1, 2)
        add_click(conn, "abc", 1, 1)
        add_click(conn, "abc", 3, 1)
        add_click(conn, "abc", 10, 3)
        add_stat(conn, "abc", 1, 3, 2)
        add_stat(conn, "abc", 3, 1, 1)
        add_stat(conn, "abc", 10, 1, 1)
        conn.commit()
    finally:
        conn.close()


# AC13: default is 7 days, oldest first, zero days shown, totals computed.
def test_AC13_default_7_days_with_zero_days(
    client: TestClient, settings: Settings
) -> None:
    seed_abc(settings.db_path)
    response = client.get("/api/analytics/links/abc")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "abc"
    assert body["days"] == 7
    daily = body["daily"]
    assert len(daily) == 7
    assert daily[-1]["day"] == utc_today().isoformat()
    assert daily[0]["day"] == (utc_today() - timedelta(days=6)).isoformat()
    days_list = []
    for entry in daily:
        days_list.append(entry["day"])
    assert days_list == sorted(days_list)
    by_day = {}
    for entry in daily:
        by_day[entry["day"]] = entry
    yesterday = (utc_today() - timedelta(days=1)).isoformat()
    three_back = (utc_today() - timedelta(days=3)).isoformat()
    assert by_day[yesterday]["clicks"] == 3
    assert by_day[yesterday]["unique_visitors"] == 2
    assert by_day[three_back]["clicks"] == 1
    assert by_day[three_back]["unique_visitors"] == 1
    assert by_day[utc_today().isoformat()]["clicks"] == 0
    assert by_day[utc_today().isoformat()]["unique_visitors"] == 0
    assert body["total_clicks"] == 4
    assert body["total_unique_visitors"] == 2


# AC14: the days parameter returns exactly N entries.
def test_AC14_days_param_returns_exactly_n_entries(
    client: TestClient, settings: Settings
) -> None:
    seed_abc(settings.db_path)
    for days in [1, 30, 90]:
        response = client.get("/api/analytics/links/abc?days=" + str(days))
        assert response.status_code == 200
        body = response.json()
        assert body["days"] == days
        assert len(body["daily"]) == days
    wide = client.get("/api/analytics/links/abc?days=30").json()
    assert wide["total_clicks"] == 5
    assert wide["total_unique_visitors"] == 3


# AC15: an unknown code gives 404 with the error shape.
def test_AC15_unknown_code_404_error_shape(client: TestClient) -> None:
    response = client.get("/api/analytics/links/zzzzzzz")
    assert response.status_code == 404
    assert_error_shape(response.json(), "link_not_found")


# AC16: invalid days values give 422 on both endpoints.
def test_AC16_invalid_days_returns_422(
    client: TestClient, settings: Settings
) -> None:
    seed_abc(settings.db_path)
    paths = ["/api/analytics/links/abc", "/api/analytics/summary"]
    for path in paths:
        for bad in ["0", "91", "-1", "abc", "2.5"]:
            response = client.get(path + "?days=" + bad)
            assert response.status_code == 422, path + " " + bad
            assert_error_shape(response.json(), "invalid_request")


# AC17: summary returns the top 10 by window clicks and window totals.
def test_AC17_summary_top_links_and_totals(
    client: TestClient, settings: Settings
) -> None:
    conn = sqlite3.connect(settings.db_path)
    try:
        for i in range(1, 13):
            code = "link" + str(i).zfill(2)
            add_link(conn, code, 1)
            for n in range(i):
                add_click(conn, code, 1, (n % 5) + 1)
        add_link(conn, "oldlink", 40)
        for n in range(100):
            add_click(conn, "oldlink", 30, 9)
        conn.execute(
            "INSERT INTO api_clients (ip_hash, first_seen, last_seen) VALUES (?, ?, ?)",
            ("c1", stamp(1), stamp(1)),
        )
        conn.execute(
            "INSERT INTO api_clients (ip_hash, first_seen, last_seen) VALUES (?, ?, ?)",
            ("c2", stamp(2), stamp(0)),
        )
        conn.execute(
            "INSERT INTO api_clients (ip_hash, first_seen, last_seen) VALUES (?, ?, ?)",
            ("c3", stamp(50), stamp(40)),
        )
        conn.commit()
    finally:
        conn.close()
    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    top = body["top_links"]
    assert len(top) == 10
    expected_codes = ["link12", "link11", "link10", "link09", "link08",
                      "link07", "link06", "link05", "link04", "link03"]
    for index in range(10):
        assert top[index]["code"] == expected_codes[index]
        assert top[index]["clicks"] == 12 - index
        assert top[index]["original_url"] == "https://example.com/" + expected_codes[index]
    assert body["total_links"] == 12
    assert body["total_clicks"] == 78
    assert body["total_visitors"] == 5
    assert body["total_api_clients"] == 2
    wide = client.get("/api/analytics/summary?days=90").json()
    assert wide["total_clicks"] == 178
    assert wide["total_links"] == 13
    assert wide["top_links"][0]["code"] == "oldlink"


# AC18: an empty database gives an empty list and zero totals.
def test_AC18_summary_on_empty_db(client: TestClient) -> None:
    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["top_links"] == []
    assert body["total_links"] == 0
    assert body["total_clicks"] == 0
    assert body["total_visitors"] == 0
    assert body["total_api_clients"] == 0
