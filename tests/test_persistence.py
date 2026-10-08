from fastapi.testclient import TestClient

from snip_url.common.config import Settings
from snip_url.main import create_app


# AC11: links and clicks survive an app restart on the same database file.
def test_AC11_data_survives_app_restart(settings: Settings) -> None:
    first = TestClient(create_app(settings), follow_redirects=False)
    url = "https://example.com/persist"
    code = first.post("/api/links", json={"url": url}).json()["code"]
    for _ in range(2):
        first.get("/" + code)

    second = TestClient(create_app(settings), follow_redirects=False)
    redirect = second.get("/" + code)
    assert redirect.status_code in (301, 302)
    assert redirect.headers["location"] == url

    stats = second.get("/api/links/" + code + "/stats")
    assert stats.status_code == 200
    # Two clicks before the restart plus one redirect after it.
    assert stats.json()["click_count"] == 3
