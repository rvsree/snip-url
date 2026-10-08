from fastapi.testclient import TestClient

from conftest import assert_error_shape
from snip_url.common.config import Settings
from snip_url.common.errors import AppError
from snip_url.main import create_app
from snip_url.services.rate_limiter import RateLimiter

URL = "https://example.com/page"


# A small controllable clock for rate-limit tests.
class FakeClock:
    # Start the clock at a given time.
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    # Return the current fake time.
    def __call__(self) -> float:
        return self.now


# Build an app and a client with a chosen IP and optional fake clock.
def make_client(
    settings: Settings, ip: str, clock: FakeClock | None = None
) -> TestClient:
    app = create_app(settings, clock=clock)
    return TestClient(app, follow_redirects=False, client=(ip, 50000))


# Send n valid create requests and return the last response.
def send_creates(client: TestClient, count: int):
    response = None
    for _ in range(count):
        response = client.post("/api/links", json={"url": URL})
    return response


# AC11: 409 and 422 requests count, and X-Forwarded-For does not matter.
def test_AC11_failed_requests_count_and_forwarded_for_is_ignored(
    settings: Settings,
) -> None:
    with make_client(settings, "10.0.0.1") as client:
        first = client.post("/api/links", json={"url": URL, "alias": "dup-one"})
        assert first.status_code == 201
        # 3 requests that return 409.
        for i in range(3):
            headers = {"X-Forwarded-For": "9.9.9." + str(i)}
            response = client.post(
                "/api/links", json={"url": URL, "alias": "dup-one"}, headers=headers
            )
            assert response.status_code == 409
        # 3 requests with an invalid alias (422).
        for _ in range(3):
            response = client.post("/api/links", json={"url": URL, "alias": "no"})
            assert response.status_code == 422
        # 2 requests with an invalid URL and 1 with a broken body (422).
        for _ in range(2):
            response = client.post("/api/links", json={"url": "nope"})
            assert response.status_code == 422
        response = client.post("/api/links", content="not json")
        assert response.status_code == 422
        # 10 requests are used up; a new spoofed header does not help.
        headers = {"X-Forwarded-For": "1.2.3.4"}
        blocked = client.post("/api/links", json={"url": URL}, headers=headers)
        assert blocked.status_code == 429
        assert_error_shape(blocked.json(), "rate_limited")


# AC12: the 11th create gives 429 with a positive whole-number Retry-After.
def test_AC12_eleventh_create_returns_429_with_retry_after(
    settings: Settings,
) -> None:
    with make_client(settings, "10.0.0.1") as client:
        for _ in range(10):
            response = client.post("/api/links", json={"url": URL})
            assert response.status_code == 201
        blocked = client.post("/api/links", json={"url": URL})
        assert blocked.status_code == 429
        assert_error_shape(blocked.json(), "rate_limited")
        retry_after = blocked.headers["retry-after"]
        assert retry_after.isdigit()
        assert int(retry_after) >= 1


# AC12: limiter unit test, Retry-After is a positive int.
def test_AC12_limiter_unit_retry_after_is_positive_int() -> None:
    clock = FakeClock()
    limiter = RateLimiter(10, 60, clock)
    for _ in range(10):
        assert limiter.check("k") == 0
    wait = limiter.check("k")
    assert isinstance(wait, int)
    assert wait >= 1
    assert wait <= 60
    clock.now += 20.5
    later = limiter.check("k")
    assert later >= 1
    assert later < wait


# AC12: enforce raises a 429 AppError with a Retry-After header.
def test_AC12_limiter_unit_enforce_raises_rate_limited() -> None:
    limiter = RateLimiter(2, 60, FakeClock())
    limiter.enforce("k")
    limiter.enforce("k")
    raised = None
    try:
        limiter.enforce("k")
    except AppError as exc:
        raised = exc
    assert raised is not None
    assert raised.status_code == 429
    assert raised.code == "rate_limited"
    assert raised.headers is not None
    assert int(raised.headers["Retry-After"]) >= 1


# AC13: after the window passes a create is accepted again (fake clock).
def test_AC13_create_accepted_after_window_passes(settings: Settings) -> None:
    clock = FakeClock()
    with make_client(settings, "10.0.0.1", clock) as client:
        last = send_creates(client, 10)
        assert last.status_code == 201
        assert client.post("/api/links", json={"url": URL}).status_code == 429
        clock.now += 61
        again = client.post("/api/links", json={"url": URL})
        assert again.status_code == 201


# AC13: limiter unit test, a rejected hit is not recorded and window recovers.
def test_AC13_limiter_unit_window_recovers_with_fake_clock() -> None:
    clock = FakeClock()
    limiter = RateLimiter(3, 60, clock)
    for _ in range(3):
        assert limiter.check("k") == 0
    assert limiter.check("k") >= 1
    clock.now += 30
    assert limiter.check("k") >= 1
    clock.now += 31
    assert limiter.check("k") == 0


# AC14: another IP is not affected by the first IP being limited.
def test_AC14_other_ip_is_not_limited(settings: Settings) -> None:
    app = create_app(settings)
    client_a = TestClient(app, follow_redirects=False, client=("10.0.0.1", 50000))
    client_b = TestClient(app, follow_redirects=False, client=("10.0.0.2", 50000))
    with client_a:
        send_creates(client_a, 10)
        assert client_a.post("/api/links", json={"url": URL}).status_code == 429
        response = client_b.post("/api/links", json={"url": URL})
        assert response.status_code == 201


# AC14: limiter unit test, keys are independent.
def test_AC14_limiter_unit_keys_are_independent() -> None:
    limiter = RateLimiter(1, 60, FakeClock())
    assert limiter.check("a") == 0
    assert limiter.check("a") >= 1
    assert limiter.check("b") == 0


# AC15: redirect and stats are not limited for an IP over the create limit.
def test_AC15_redirect_and_stats_not_rate_limited(settings: Settings) -> None:
    with make_client(settings, "10.0.0.1") as client:
        created = client.post("/api/links", json={"url": URL})
        code = created.json()["code"]
        send_creates(client, 9)
        assert client.post("/api/links", json={"url": URL}).status_code == 429
        for _ in range(15):
            redirect = client.get("/" + code)
            assert redirect.status_code == 302
            stats = client.get("/api/links/" + code + "/stats")
            assert stats.status_code == 200
