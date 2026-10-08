from fastapi.testclient import TestClient

from conftest import assert_error_shape, count_rows
from snip_url.common.config import Settings


# AC1: create returns a 7-char alphanumeric code and a short URL ending in it.
def test_AC1_create_returns_7_char_alnum_code_and_short_url(client: TestClient) -> None:
    response = client.post("/api/links", json={"url": "https://example.com/a"})
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 7
    assert body["code"].isascii()
    assert body["code"].isalnum()
    assert body["short_url"].endswith("/" + body["code"])
    assert body["short_url"] == "http://testserver/" + body["code"]
    assert body["original_url"] == "https://example.com/a"


# AC1: a URL of exactly 2048 characters is accepted.
def test_AC1_url_of_exactly_2048_chars_is_accepted(client: TestClient) -> None:
    prefix = "https://example.com/"
    url = prefix + "a" * (2048 - len(prefix))
    assert len(url) == 2048
    response = client.post("/api/links", json={"url": url})
    assert response.status_code == 201


# AC2: non-http schemes are rejected and nothing is stored.
def test_AC2_non_http_scheme_rejected_and_not_stored(
    client: TestClient, settings: Settings
) -> None:
    bad_urls = ["ftp://x.com", "javascript:alert(1)"]
    for bad in bad_urls:
        response = client.post("/api/links", json={"url": bad})
        assert response.status_code == 422
        assert_error_shape(response.json(), "invalid_url")
    assert count_rows(settings.db_path, "short_links") == 0


# AC3: URLs over 2048 characters are rejected and nothing is stored.
def test_AC3_url_over_2048_chars_rejected_and_not_stored(
    client: TestClient, settings: Settings
) -> None:
    prefix = "https://example.com/"
    url = prefix + "a" * (2049 - len(prefix))
    assert len(url) == 2049
    response = client.post("/api/links", json={"url": url})
    assert response.status_code == 422
    assert_error_shape(response.json(), "invalid_url")
    assert count_rows(settings.db_path, "short_links") == 0


# AC4: a missing url value is rejected.
def test_AC4_missing_url_rejected(client: TestClient, settings: Settings) -> None:
    response = client.post("/api/links", json={})
    assert response.status_code == 422
    assert_error_shape(response.json(), "invalid_url")
    assert count_rows(settings.db_path, "short_links") == 0


# AC4: an empty url value is rejected.
def test_AC4_empty_url_rejected(client: TestClient, settings: Settings) -> None:
    response = client.post("/api/links", json={"url": ""})
    assert response.status_code == 422
    assert_error_shape(response.json(), "invalid_url")
    assert count_rows(settings.db_path, "short_links") == 0


# AC4: a wrong-typed url value gives the standard invalid_request error.
def test_AC4_wrong_type_url_rejected_with_standard_error(client: TestClient) -> None:
    response = client.post("/api/links", json={"url": 123})
    assert response.status_code == 422
    assert_error_shape(response.json(), "invalid_request")
