from fastapi.testclient import TestClient


# AC12: health returns 200 with status ok.
def test_AC12_health_returns_200_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
