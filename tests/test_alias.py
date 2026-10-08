from fastapi.testclient import TestClient

from conftest import assert_error_shape, count_rows
from snip_url.common.config import Settings

URL = "https://example.com/page"


# Post a create request with an alias and return the response.
def create_with_alias(client: TestClient, alias: str, url: str = URL):
    return client.post("/api/links", json={"url": url, "alias": alias})


# AC1: a valid alias becomes the code and ends the short_url.
def test_AC1_alias_creates_link_with_that_code(client: TestClient) -> None:
    response = create_with_alias(client, "my-link")
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "my-link"
    assert body["short_url"].endswith("/my-link")


# AC2: the alias redirects to the original URL.
def test_AC2_alias_redirects_to_original_url(client: TestClient) -> None:
    create_with_alias(client, "my-link")
    response = client.get("/my-link")
    assert response.status_code == 302
    assert response.headers["location"] == URL


# AC3: with no alias the code is a random 7-character code.
def test_AC3_no_alias_gives_random_7_char_code(client: TestClient) -> None:
    response = client.post("/api/links", json={"url": URL})
    assert response.status_code == 201
    code = response.json()["code"]
    assert len(code) == 7
    assert code.isalnum()


# AC4: a duplicate alias gives 409 alias_taken and keeps the original link.
def test_AC4_duplicate_alias_returns_409_alias_taken_and_keeps_original(
    client: TestClient, settings: Settings
) -> None:
    create_with_alias(client, "taken-one", "https://example.com/first")
    response = create_with_alias(client, "taken-one", "https://example.com/second")
    assert response.status_code == 409
    body = response.json()
    assert_error_shape(body, "alias_taken")
    assert "taken" in body["error"]["message"]
    assert count_rows(settings.db_path, "links") == 1
    redirect = client.get("/taken-one")
    assert redirect.headers["location"] == "https://example.com/first"


# AC5: aliases of exactly 3 and exactly 30 characters are accepted.
def test_AC5_alias_of_3_and_30_chars_accepted(client: TestClient) -> None:
    short_alias = "abc"
    long_alias = "a" * 30
    first = create_with_alias(client, short_alias)
    second = create_with_alias(client, long_alias)
    assert first.status_code == 201
    assert first.json()["code"] == short_alias
    assert second.status_code == 201
    assert second.json()["code"] == long_alias


# AC6: aliases shorter than 3 or longer than 30 are invalid_alias.
def test_AC6_alias_too_short_or_too_long_returns_422_invalid_alias(
    client: TestClient, settings: Settings
) -> None:
    for alias in ["ab", "a", "", "a" * 31]:
        response = create_with_alias(client, alias)
        assert response.status_code == 422
        assert_error_shape(response.json(), "invalid_alias")
    assert count_rows(settings.db_path, "links") == 0


# AC7: aliases with a space, underscore or slash are invalid_alias.
def test_AC7_alias_with_bad_characters_returns_422_invalid_alias(
    client: TestClient, settings: Settings
) -> None:
    for alias in ["has space", "under_score", "sla/sh"]:
        response = create_with_alias(client, alias)
        assert response.status_code == 422
        assert_error_shape(response.json(), "invalid_alias")
    assert count_rows(settings.db_path, "links") == 0


# AC8: reserved words in any case give reserved_alias, not invalid_alias.
def test_AC8_reserved_alias_any_case_returns_422_reserved_alias(
    client: TestClient, settings: Settings
) -> None:
    for alias in ["api", "health", "docs", "openapi", "API", "Docs", "HeAlTh"]:
        response = create_with_alias(client, alias)
        assert response.status_code == 422
        body = response.json()
        assert_error_shape(body, "reserved_alias")
        assert "reserved" in body["error"]["message"].lower()
    assert count_rows(settings.db_path, "links") == 0


# AC9: aliases are case-sensitive, so MyLink and mylink can coexist.
def test_AC9_aliases_are_case_sensitive(client: TestClient) -> None:
    first = create_with_alias(client, "MyLink")
    second = create_with_alias(client, "mylink")
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["code"] == "mylink"


# AC10: an alias equal to an existing random code is taken.
def test_AC10_alias_equal_to_existing_random_code_returns_409(
    client: TestClient,
) -> None:
    created = client.post("/api/links", json={"url": URL})
    code = created.json()["code"]
    response = create_with_alias(client, code, "https://example.com/other")
    assert response.status_code == 409
    assert_error_shape(response.json(), "alias_taken")
