from fastapi.testclient import TestClient

from conftest import assert_error_shape


# AC9: stats show 0 clicks for a new link and N after N redirects.
def test_AC9_stats_zero_then_n_clicks(client: TestClient) -> None:
    url = "https://example.com/a"
    created = client.post("/api/links", json={"url": url}).json()
    code = created["code"]

    first = client.get("/api/links/" + code + "/stats")
    assert first.status_code == 200
    body = first.json()
    assert body["code"] == code
    assert body["original_url"] == url
    assert body["created_at"] == created["created_at"]
    assert body["click_count"] == 0

    for _ in range(4):
        client.get("/" + code)
    second = client.get("/api/links/" + code + "/stats")
    assert second.status_code == 200
    assert second.json()["click_count"] == 4


# AC10: stats for an unknown code give 404 with a JSON error.
def test_AC10_unknown_code_stats_404_json_error(client: TestClient) -> None:
    response = client.get("/api/links/zzzzzzz/stats")
    assert response.status_code == 404
    assert_error_shape(response.json(), "link_not_found")
