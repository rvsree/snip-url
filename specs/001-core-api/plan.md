# Plan: Core URL shortener (S1)

Decisions: validation failures return **422** (always, for every validation error). Paths: `POST /api/links`, `GET /api/links/{code}/stats`, `GET /health`, `GET /{code}`. Python 3.12, stdlib `sqlite3`, no new libraries.

## 1. Impact analysis

Existing files that change:
- None in `src/` (only an empty `src/snip_url/__init__.py` exists). `tests/` has only `.gitkeep`.

New files (all risk: low, greenfield):
- `src/snip_url/main.py` - app factory and module-level `app`. Risk: wiring mistakes (route order).
- `src/snip_url/common/__init__.py`, `config.py`, `errors.py` - settings, error class, handlers.
- `src/snip_url/models/__init__.py`, `link.py` - Pydantic models.
- `src/snip_url/repo/__init__.py`, `db.py`, `link_repo.py` - SQL only.
- `src/snip_url/services/__init__.py`, `link_service.py` - business rules.
- `src/snip_url/api/__init__.py`, `routes.py` - routes.
- `tests/conftest.py`, `tests/test_links.py`, `tests/test_redirect.py`, `tests/test_stats.py`, `tests/test_persistence.py`, `tests/test_health.py`, `tests/test_service.py`.

Risks: `GET /{code}` is a catch-all, so it must be registered last. Do not read `.env*` files; settings come from `os.environ` with defaults.

## 2. Contract

### common/config.py
```python
# A plain settings holder.
class Settings:
    db_path: str
    base_url: str
    def __init__(self, db_path: str, base_url: str) -> None: ...

# Build Settings from env vars SNIP_DB_PATH (default "snip_url.db") and SNIP_BASE_URL (default "http://localhost:8000"); strip trailing "/" from base_url.
def load_settings() -> Settings: ...
```

### common/errors.py
```python
# App error carrying status, code and message.
class AppError(Exception):
    status_code: int
    code: str
    message: str
    def __init__(self, status_code: int, code: str, message: str) -> None: ...

# Build the standard error JSON body.
def error_body(code: str, message: str) -> dict: ...   # {"error": {"code": code, "message": message}}

# Handler: AppError -> JSONResponse(status_code, error_body).
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse: ...

# Handler: FastAPI RequestValidationError (bad JSON / wrong types) -> 422, code "invalid_request", message "Request body is invalid".
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse: ...
```
Error codes used: `invalid_url` (422), `link_not_found` (404), `code_generation_failed` (500), `invalid_request` (422).

### models/link.py
```python
class CreateLinkRequest(BaseModel):
    url: str | None = None           # missing/null allowed here; service rejects it

class CreateLinkResponse(BaseModel):
    code: str
    short_url: str
    original_url: str
    created_at: str                  # UTC ISO 8601

class LinkStatsResponse(BaseModel):
    code: str
    original_url: str
    created_at: str                  # UTC ISO 8601
    click_count: int

class HealthResponse(BaseModel):
    status: str                      # "ok"
```

### repo/db.py
```python
# Open a sqlite3 connection to db_path with Row factory and foreign keys on.
def get_connection(db_path: str) -> sqlite3.Connection: ...

# Create tables if they do not exist (idempotent).
def init_db(db_path: str) -> None: ...
```

### repo/link_repo.py (SQL only; each function takes an open `conn`)
```python
# Return True if a link with this code exists.
def code_exists(conn: sqlite3.Connection, code: str) -> bool: ...

# Insert a link row and commit.
def insert_link(conn: sqlite3.Connection, code: str, original_url: str, created_at: str) -> None: ...

# Return the link row as dict {code, original_url, created_at} or None.
def get_link(conn: sqlite3.Connection, code: str) -> dict | None: ...

# Insert a click row and commit.
def insert_click(conn: sqlite3.Connection, code: str, clicked_at: str) -> None: ...

# Return number of clicks for the code.
def count_clicks(conn: sqlite3.Connection, code: str) -> int: ...
```

### services/link_service.py (business rules, no SQL; calls repo only)
Constants: `MAX_URL_LENGTH = 2048`, `CODE_LENGTH = 7`, `ALPHABET = string.ascii_letters + string.digits`, `MAX_CODE_ATTEMPTS = 10`.
```python
# Raise AppError(422, "invalid_url", ...) if url is None/empty/blank, longer than 2048, or scheme not http/https or has no host.
def validate_url(url: str | None) -> str: ...        # returns the url unchanged when valid

# Return a random 7-char base62 code using secrets.choice in a for loop.
def generate_code() -> str: ...

# Return current UTC time as ISO 8601 string (datetime.now(timezone.utc).isoformat()).
def utc_now_iso() -> str: ...

# Pick a code not in the db (up to 10 tries, else AppError(500, "code_generation_failed", ...)).
def make_unique_code(conn: sqlite3.Connection) -> str: ...

# Validate, generate unique code, store, return CreateLinkResponse (short_url = base_url + "/" + code).
def create_link(conn: sqlite3.Connection, base_url: str, url: str | None) -> CreateLinkResponse: ...

# Look up code (case-sensitive); if missing raise AppError(404, "link_not_found", ...); else record click and return original_url.
def resolve_and_record_click(conn: sqlite3.Connection, code: str) -> str: ...

# Return LinkStatsResponse or raise AppError(404, "link_not_found", "Short code not found").
def get_stats(conn: sqlite3.Connection, code: str) -> LinkStatsResponse: ...
```
`create_link` must be split into small helpers if over 29 lines. Validation must happen before any DB write (nothing stored on rejection).

### api/routes.py
`router = APIRouter()`. Each handler opens a connection with `get_connection(request.app.state.settings.db_path)`, calls the service, closes it in `try/finally`. Helper:
```python
# Return a new connection using the app settings.
def open_conn(request: Request) -> sqlite3.Connection: ...
```
Endpoints (registration order matters; `/{code}` last):

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | `/health` | 200 `{"status": "ok"}` | none |
| POST | `/api/links` | 201 `CreateLinkResponse` | 422 `invalid_url` / `invalid_request` |
| GET | `/api/links/{code}/stats` | 200 `LinkStatsResponse` | 404 `link_not_found` |
| GET | `/{code}` | 302, `Location: <original_url>`, empty body | 404 `link_not_found` |

Request `POST /api/links`: `{"url": "https://example.com/a"}`.
Response 201: `{"code": "aB3xY9z", "short_url": "http://localhost:8000/aB3xY9z", "original_url": "https://example.com/a", "created_at": "2026-10-07T12:00:00+00:00"}`.
Stats 200: `{"code": "aB3xY9z", "original_url": "...", "created_at": "...", "click_count": 0}`.
Error example 404: `{"error": {"code": "link_not_found", "message": "Short code not found"}}`.
The redirect uses `RedirectResponse(url, status_code=302)`. The tester's client must use `follow_redirects=False`.

### main.py
```python
# Build the FastAPI app: store settings in app.state.settings, call init_db, register exception handlers, include router.
def create_app(settings: Settings | None = None) -> FastAPI: ...

app = create_app()   # used by uvicorn snip_url.main:app
```
Tests call `create_app(Settings(db_path=str(tmp_path / "t.db"), base_url="http://testserver"))`. Restart simulation: call `create_app` again with the same db_path.

## 3. Data model (SQLite)

```sql
CREATE TABLE IF NOT EXISTS links (
    code TEXT PRIMARY KEY,            -- 7 chars, case-sensitive (default BINARY collation)
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL          -- UTC ISO 8601
);
CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL REFERENCES links(code),
    clicked_at TEXT NOT NULL          -- UTC ISO 8601
);
CREATE INDEX IF NOT EXISTS idx_clicks_code ON clicks(code);
```
Tests may read `clicks` directly with `sqlite3` to check AC7/AC8.

## 4. Test plan

| AC | Test name | File |
|---|---|---|
| AC1 | `test_AC1_create_returns_7_char_alnum_code_and_short_url` | test_links.py |
| AC1 | `test_AC1_url_of_exactly_2048_chars_is_accepted` | test_links.py |
| AC2 | `test_AC2_non_http_scheme_rejected_and_not_stored` (ftp, javascript) | test_links.py |
| AC3 | `test_AC3_url_over_2048_chars_rejected_and_not_stored` | test_links.py |
| AC4 | `test_AC4_missing_url_rejected` | test_links.py |
| AC4 | `test_AC4_empty_url_rejected` | test_links.py |
| AC5 | `test_AC5_redirect_302_with_location` | test_redirect.py |
| AC6 | `test_AC6_unknown_code_redirect_404_json_error` | test_redirect.py |
| AC7 | `test_AC7_each_redirect_records_click_with_time` | test_redirect.py |
| AC8 | `test_AC8_unknown_code_records_no_click` | test_redirect.py |
| AC9 | `test_AC9_stats_zero_then_n_clicks` | test_stats.py |
| AC10 | `test_AC10_unknown_code_stats_404_json_error` | test_stats.py |
| AC11 | `test_AC11_data_survives_app_restart` | test_persistence.py |
| AC12 | `test_AC12_health_returns_200_ok` | test_health.py |
| AC13 | `test_AC13_collision_retries_to_new_code` (monkeypatch `generate_code` in `snip_url.services.link_service` to return a taken code first, then a new one; use a def, no lambda) | test_service.py |
| AC13 | `test_AC13_code_exhaustion_raises_500` (generate_code always returns a taken code) | test_service.py |

All error tests assert status 422/404 and body shape `{"error": {"code", "message"}}` with non-empty message. All tests use `tmp_path` DB via `tests/conftest.py` fixtures `settings`, `client` (TestClient, `follow_redirects=False`). Coverage must be at least 80%.

## 5. Risks

- Route order: `/{code}` swallowing other routes. Mitigation: register it last; `/health` is 6 chars so it cannot clash with 7-char codes anyway.
- Pydantic type errors (e.g. `url: 123`) bypass the service. Mitigation: `validation_error_handler` returns the standard error format with 422.
- Code collisions. Mitigation: existence check plus retry up to 10 times; primary key as backstop.
- SQLite connections across threads. Mitigation: one short-lived connection per request.
- Windows temp DB file locks. Mitigation: always close connections in `finally`.
- URL validation too loose. Mitigation: use `urllib.parse.urlparse`; require scheme in (`http`, `https`) and non-empty `netloc`.
- Env settings: `.env` files are not read by agents; defaults apply.
