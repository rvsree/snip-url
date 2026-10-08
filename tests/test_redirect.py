import sqlite3

from fastapi.testclient import TestClient

from conftest import assert_error_shape, count_rows
from snip_url.common.config import Settings


# Create a link through the API and return its code.
def make_link(client: TestClient, url: str) -> str:
    response = client.post("/api/links", json={"url": url})
    assert response.status_code == 201
    return response.json()["code"]


# AC5: redirect is 302 with Location equal to the original URL.
def test_AC5_redirect_302_with_location(client: TestClient) -> None:
    url = "https://example.com/a?b=1"
    code = make_link(client, url)
    response = client.get("/" + code)
    assert response.status_code in (301, 302)
    assert response.headers["location"] == url


# AC6: an unknown code gives 404 with a JSON error.
def test_AC6_unknown_code_redirect_404_json_error(client: TestClient) -> None:
    response = client.get("/zzzzzzz")
    assert response.status_code == 404
    assert_error_shape(response.json(), "link_not_found")


# AC7: each redirect records one click with a time.
def test_AC7_each_redirect_records_click_with_time(
    client: TestClient, settings: Settings
) -> None:
    code = make_link(client, "https://example.com/a")
    for _ in range(3):
        response = client.get("/" + code)
        assert response.status_code in (301, 302)
    conn = sqlite3.connect(settings.db_path)
    try:
        rows = conn.execute(
            "SELECT code, clicked_at FROM clicks WHERE code = ?", (code,)
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 3
    for row in rows:
        assert row[0] == code
        assert row[1] is not None
        assert row[1] != ""


# AC8: an unknown code records no click.
def test_AC8_unknown_code_records_no_click(
    client: TestClient, settings: Settings
) -> None:
    make_link(client, "https://example.com/a")
    response = client.get("/zzzzzzz")
    assert response.status_code == 404
    assert count_rows(settings.db_path, "clicks") == 0
