# Plan: Custom alias, rate limiting, BUG-01 fix, DEF-02 refactor

Error codes chosen by the planner: **`alias_taken`** (409), **`rate_limited`** (429). Codes fixed by the spec: `invalid_alias`, `reserved_alias` (both 422).

## 1. Impact analysis

### Changed files (src)

| File | Change | Risk |
|---|---|---|
| `src/snip_url/common/config.py` | Env var `SNIP_DB_PATH` -> `DATABASE_PATH`; default `data/snip_url.db`. Attribute stays `Settings.db_path`. | Low. Old name is dropped on purpose; README must say so. |
| `src/snip_url/common/errors.py` | `AppError` gets optional `headers`; `app_error_handler` passes them to the response (needed for `Retry-After`). | Low. Default `None` keeps all current call sites valid. |
| `src/snip_url/repo/db.py` | `init_db` creates the parent folder before opening the file. | Low. Idempotent. |
| `src/snip_url/repo/link_repo.py` | New `try_insert_link` (returns False on duplicate code). Existing functions unchanged. | Low. |
| `src/snip_url/models/link.py` | `CreateLinkRequest` gets `alias: str | None = None`. | Low. Response models unchanged. |
| `src/snip_url/services/link_service.py` | `create_link` takes optional `alias`; new alias validation and alias path. | Medium. Must keep random-code path unchanged (AC3). Keep each function < 30 lines. |
| `src/snip_url/api/routes.py` | Redirect 301 -> 302 (BUG-01). `create_link` route passes `body.alias` and depends on the rate-limit dependency. | Medium. The limiter must run even when the body is invalid (AC11); a FastAPI dependency does this because dependencies are solved before the body is validated. |
| `src/snip_url/main.py` | `create_app` no longer calls `init_db`; a `lifespan` does it at startup. `create_app(settings, clock)` builds the limiter. Module-level `app = create_app()` stays but must not touch the disk. | High. Tests that do not enter `with TestClient(...)` never run lifespan, so the DB would not exist. Tests must use the context manager (see conftest below). |

### New files (src)

| File | Purpose |
|---|---|
| `src/snip_url/services/rate_limiter.py` | In-memory sliding-window limiter with an injectable clock. |

### Changed files (tests)

The coder writes only in `src/`. `README.md` is not a coder or tester file: the orchestrator updates it in the DOCS step (alias option and 409/reserved behaviour, rate limit, `DATABASE_PATH`, removal of `SNIP_DB_PATH`; AC22).

| File | Change |
|---|---|
| `tests/conftest.py` | `client` fixture uses `with TestClient(app, follow_redirects=False) as c: yield c` so lifespan runs. Every test gets a fresh app, and therefore a fresh `RateLimiter` (see Test isolation in section 4). |
| `tests/test_redirect.py` | Restore two assertions to `== 302` (lines for AC5, AC7). |
| `tests/test_persistence.py` | Restore the redirect assertion to `== 302`; the second `create_app` must also run under `with TestClient(...)`. |

### New files (tests)

`tests/test_alias.py`, `tests/test_rate_limit.py`, `tests/test_startup_db.py`, plus the BUG-01 regression tests in `tests/test_redirect.py`.

### Not touched

`.env*` files (agents may not read them; the human updates `.env.example` to `DATABASE_PATH` if needed). The root `snip_url.db` is not deleted. `docs/`, `scripts/`.

## 2. Contract

All functions need type hints, a one-line comment above them, and < 30 lines. No list comprehensions, no lambdas.

### 2.1 `common/config.py`

```python
class Settings:
    db_path: str
    base_url: str
    def __init__(self, db_path: str, base_url: str) -> None: ...   # unchanged

def load_settings() -> Settings
```
`load_settings` reads `DATABASE_PATH` (default `"data/snip_url.db"`) and `SNIP_BASE_URL` (default `"http://localhost:8000"`, trailing `/` stripped). Reads env only; creates no file or folder.

### 2.2 `common/errors.py`

```python
class AppError(Exception):
    status_code: int; code: str; message: str; headers: dict[str, str] | None
    def __init__(self, status_code: int, code: str, message: str,
                 headers: dict[str, str] | None = None) -> None
```
`app_error_handler` returns `JSONResponse(status_code, content=error_body(code, message), headers=exc.headers)`.

### 2.3 `repo/db.py`

- `get_connection(db_path: str) -> sqlite3.Connection` (unchanged).
- `init_db(db_path: str) -> None`: first `os.makedirs(os.path.dirname(db_path), exist_ok=True)` only if the dirname is not `""`, then create the tables as before.

### 2.4 `repo/link_repo.py` (existing functions unchanged)

```python
def try_insert_link(conn: sqlite3.Connection, code: str, original_url: str, created_at: str) -> bool
```
Inserts and commits, returns `True`. On `sqlite3.IntegrityError` (duplicate code) it returns `False` and changes nothing.

### 2.5 `models/link.py`

`CreateLinkRequest`: `url: str | None = None`, `alias: str | None = None`. Other models unchanged.

### 2.6 `services/rate_limiter.py`

```python
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW_SECONDS = 60

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, clock: Callable[[], float]) -> None
    # Raise AppError(429, "rate_limited", ...) with Retry-After header if key is over the limit; else record the hit.
    def enforce(self, key: str) -> None
    # Return 0 and record the hit if allowed, else return whole seconds (>= 1) until a slot frees.
    def check(self, key: str) -> int
```
- Sliding window: per key a list of timestamps; entries with `now - t >= window_seconds` are dropped first. Allowed if fewer than `max_requests` remain.
- A rejected request is not recorded (so the window can recover, AC13).
- Retry-After = `ceil(oldest + window_seconds - now)`, at least 1. Header value is the integer as a string.
- 429 message: `"Too many requests. Try again later."`.
- The default clock is `time.monotonic`.

### 2.7 `services/link_service.py` (existing functions unchanged unless listed)

```python
ALIAS_MIN_LENGTH = 3
ALIAS_MAX_LENGTH = 30
ALIAS_CHARS = string.ascii_letters + string.digits + "-"
RESERVED_ALIASES = ("api", "health", "docs", "openapi")

# Raise AppError(422, "invalid_alias") on bad length or characters; AppError(422, "reserved_alias") on a reserved word (compared in lower case); else return alias.
def validate_alias(alias: str) -> str

# Store the link under the alias; AppError(409, "alias_taken") if the code exists.
def create_alias_link(conn, base_url: str, valid_url: str, alias: str) -> CreateLinkResponse

def create_link(conn: sqlite3.Connection, base_url: str, url: str | None, alias: str | None = None) -> CreateLinkResponse
```
Order inside `create_link`: `validate_url` first, then (if `alias is not None`) `validate_alias` and `create_alias_link`; if `alias is None` the existing random-code path runs unchanged. An empty string alias is an alias and fails with `invalid_alias`.
`create_alias_link` calls `link_repo.try_insert_link`; `False` -> `AppError(409, "alias_taken", "Alias is already taken")`. An alias equal to an existing random code is also taken (AC10). Matching is case-sensitive.
Messages: invalid -> `"Alias must be 3 to 30 characters: letters, digits and hyphens only"`; reserved -> `"Alias is reserved"`.

### 2.8 `main.py`

```python
# Build the app; lifespan runs init_db(settings.db_path) at startup only.
def create_app(settings: Settings | None = None, clock: Callable[[], float] | None = None) -> FastAPI
```
- `app.state.settings = settings`; `app.state.rate_limiter = RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_SECONDS, clock or time.monotonic)`.
- `init_db` is called inside a `lifespan` async context manager passed to `FastAPI(lifespan=...)`, never in `create_app` or at import.
- `app = create_app()` stays at module level (reads env only; no file I/O).

### 2.9 `api/routes.py`

```python
# Dependency: count this create request against the direct client IP (ignores X-Forwarded-For).
def limit_create(request: Request) -> None
```
Key = `request.client.host`, or `"unknown"` if `request.client is None`. Calls `request.app.state.rate_limiter.enforce(key)`.

### 2.10 Endpoints

| Method / path | Success | Errors |
|---|---|---|
| `GET /health` | 200 `{"status":"ok"}` | none (unchanged) |
| `POST /api/links` (`dependencies=[Depends(limit_create)]`) | 201 | 429, 409, 422 |
| `GET /api/links/{code}/stats` | 200 (unchanged) | 404 `link_not_found` (unchanged), not rate limited |
| `GET /{code}` | **302** with `Location` = original URL (was 301) | 404 `link_not_found`, not rate limited |

`POST /api/links` request: `{"url": "https://example.com", "alias": "my-link"}` (`alias` optional).
201 response (unchanged shape): `{"code": "my-link", "short_url": "<base_url>/my-link", "original_url": "...", "created_at": "..."}`.

| Status | `error.code` | When |
|---|---|---|
| 422 | `invalid_url` | existing URL rules (unchanged) |
| 422 | `invalid_request` | body is not valid JSON/shape (existing handler), including a non-string alias |
| 422 | `invalid_alias` | alias length < 3 or > 30, or a character outside letters/digits/hyphen |
| 422 | `reserved_alias` | alias is api, health, docs, openapi in any case |
| 409 | `alias_taken` | alias already used as a code; message contains "taken" |
| 429 | `rate_limited` | 11th create request from one IP inside 60 s; header `Retry-After: <positive int>` |

All errors use `{"error": {"code": "...", "message": "..."}}`.
The rate limit runs before body validation, so 422 and 409 requests count too (AC11). Redirects and stats never call the limiter (AC15).

## 3. Data model

No schema change.
- `links(code TEXT PRIMARY KEY, original_url TEXT NOT NULL, created_at TEXT NOT NULL)`. A custom alias is stored in `code`; the primary key enforces uniqueness and is case-sensitive (SQLite TEXT compares with BINARY collation by default).
- `clicks(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL REFERENCES links(code), clicked_at TEXT NOT NULL)` with index `idx_clicks_code`.
- Rate-limit state is in memory only (`dict[str, list[float]]` inside `RateLimiter`), lost on restart.
- Database file default location: `data/snip_url.db`, created with its folder at startup.

## 4. Test plan

Test isolation (binding): `tests/conftest.py` builds a new app with `create_app(settings)` inside every test's `client` fixture (function scope, `settings` uses `tmp_path`). Each app owns its own `RateLimiter` in `app.state`, so every test starts with an empty limiter and a new temporary database, and tests never affect each other. No limiter or app is module-level or shared between tests. Tests that need another IP or a fake clock build their own app the same way. Tests must not import the module-level `snip_url.main.app`.

Testing notes: use `with TestClient(app, follow_redirects=False)` so lifespan runs. A test IP is set with `TestClient(app, client=("10.0.0.1", 50000))`. Clock tests use `create_app(settings, clock=fake)` where `fake` is a small class with `now` and `__call__`.

| AC | Test name | File |
|---|---|---|
| 1 | `test_AC1_alias_creates_link_with_that_code` | test_alias.py |
| 2 | `test_AC2_alias_redirects_to_original_url` | test_alias.py |
| 3 | `test_AC3_no_alias_gives_random_7_char_code` | test_alias.py |
| 4 | `test_AC4_duplicate_alias_returns_409_alias_taken_and_keeps_original` | test_alias.py |
| 5 | `test_AC5_alias_of_3_and_30_chars_accepted` | test_alias.py |
| 6 | `test_AC6_alias_too_short_or_too_long_returns_422_invalid_alias` | test_alias.py |
| 7 | `test_AC7_alias_with_bad_characters_returns_422_invalid_alias` (space, underscore, slash) | test_alias.py |
| 8 | `test_AC8_reserved_alias_any_case_returns_422_reserved_alias` | test_alias.py |
| 9 | `test_AC9_aliases_are_case_sensitive` | test_alias.py |
| 10 | `test_AC10_alias_equal_to_existing_random_code_returns_409` | test_alias.py |
| 11 | `test_AC11_failed_requests_count_and_forwarded_for_is_ignored` | test_rate_limit.py |
| 12 | `test_AC12_eleventh_create_returns_429_with_retry_after` | test_rate_limit.py |
| 13 | `test_AC13_create_accepted_after_window_passes` (fake clock) | test_rate_limit.py |
| 14 | `test_AC14_other_ip_is_not_limited` | test_rate_limit.py |
| 15 | `test_AC15_redirect_and_stats_not_rate_limited` | test_rate_limit.py |
| 16 | `test_AC16_redirect_is_302_with_location` | test_redirect.py |
| 17 | `test_AC17_three_visits_all_302_and_click_count_3` | test_redirect.py |
| 16, 17 | `test_BUG01_redirect_is_302_and_counts_clicks` (BUG-01 regression: create a link, open it twice; assert each status is exactly 302, not 301, and stats `click_count` == 2) | test_redirect.py |
| 18 | `test_AC18_import_creates_no_database_file` (subprocess `python -I -c "import snip_url.main"` with cwd = tmp_path and `DATABASE_PATH` inside tmp_path; assert no `.db` file and no `data/` folder) | test_startup_db.py |
| 19 | `test_AC19_startup_creates_missing_folder_and_tables` | test_startup_db.py |
| 20 | `test_AC20_default_path_is_data_snip_url_db` (`monkeypatch.chdir(tmp_path)`, `delenv("DATABASE_PATH")`, start app from `load_settings()`) | test_startup_db.py |
| 21 | `test_AC21_tests_use_tmp_database_only` (settings path is under `tmp_path`; project-root `data/` mtime/existence not created by the fixture app) | test_startup_db.py |
| 22 | README is written by the orchestrator in the DOCS step; reviewer check, plus optional `test_AC22_readme_mentions_alias_rate_limit_and_database_path` that reads README.md and asserts the strings `alias`, `429`, `Retry-After`, `DATABASE_PATH` | test_startup_db.py |

Unit tests for the limiter (`RateLimiter.check` and `enforce` with a fake clock) go in `test_rate_limit.py` and are named under AC12/AC13 (for example `test_AC12_limiter_unit_retry_after_is_positive_int`). Existing tests (AC numbers from 001) keep their names; the loosened assertions become `== 302`. The seed-script file `scripts/seed_bug01.py` is not changed.
Coverage target stays at least 80%.

## 5. Risks

| Risk | Handling |
|---|---|
| Lifespan does not run unless the client is used as a context manager, so existing tests could fail with "no such table". | Contract says conftest `client` fixture uses `with`; `test_persistence.py` is updated the same way. Both are tester tasks. |
| The limiter must count requests with an invalid body (AC11). | It is a route dependency, solved before body validation. Tester's AC11 test sends invalid bodies to prove it. If it fails, coder moves the check into a middleware limited to `POST /api/links`. |
| `X-Forwarded-For` spoofing. | Key is `request.client.host` only; header never read. |
| Alias race (two requests, same alias). | `try_insert_link` relies on the primary key and returns False, giving 409 instead of 500. |
| Alias collides with a route (`/api`, `/health`, `/docs`, `/openapi`). | Reserved list rejects them (case-insensitive). |
| Rate-limit memory grows with many IPs. | Accepted for single-server, in-memory scope (README "Limitations"); old timestamps pruned per key on each check. |
| Windows: `os.path.dirname` of a bare filename is `""`. | `init_db` skips `makedirs` when the dirname is empty. |
| Parallel coder/tester drift. | Names, signatures, error codes, status codes and the `create_app(settings, clock)` signature above are binding. |
| Env var rename breaks existing users. | Documented in README; spec says the old name is dropped. |
