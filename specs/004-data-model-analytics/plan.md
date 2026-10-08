# Plan: Data model, analytics and seed data (004)

Follows `spec.md` (approved) and `specs/constitution.md`. Layers: api -> services -> repo. Every function under 30 lines, one-line comment above it, type hints, no list comprehensions, no lambdas.

## 1. Impact analysis

### Changed files

| File | Change | Risk |
|---|---|---|
| `src/snip_url/common/config.py` | Add `DEFAULT_IP_HASH_SALT`, `Settings.ip_hash_salt` (optional 3rd arg, default), read `IP_HASH_SALT` | Low. `Settings(db_path=, base_url=)` calls in existing tests must keep working, so the new arg has a default. |
| `src/snip_url/repo/db.py` | New schema (5 tables), rename migration, add-missing-columns, `init_db` calls them | High. Data loss if wrong. Migration must be idempotent and run before the new `CREATE TABLE IF NOT EXISTS`. |
| `src/snip_url/repo/link_repo.py` | SQL uses `short_links`/`click_events`; new optional args and new functions | Medium. Existing callers (tests/test_service.py) must still work, so all new args are optional. |
| `src/snip_url/services/link_service.py` | `create_link` and `resolve_and_record_click` get optional tracking args and call `tracking_service` | Medium. Old call signatures must still work. Functions must stay under 30 lines (split into helpers). |
| `src/snip_url/api/routes.py` | `limit_create` records rate-limit hits; create and redirect pass IP, User-Agent, Referer, salt; adds 2 analytics routes | Medium. `/{code}` catch-all stays declared last. |
| `src/snip_url/main.py` | No logic change expected (router already included). Only touch if needed. | Low |
| `tests/test_links.py`, `tests/test_alias.py`, `tests/test_redirect.py`, `tests/test_startup_db.py` | Table names `links`->`short_links`, `clicks`->`click_events` in raw SQL and `count_rows` calls. Names only; assertions are not weakened. | Low. This is a rename, not a weakening. |
| `README.md` | NOT in the coder's work. The README (5 tables, 2 analytics endpoints, seed script, IP_HASH_SALT) is updated in the DOCS step by the orchestrator. | None for coder |

### New files

| File | Purpose |
|---|---|
| `src/snip_url/services/privacy.py` | `hash_ip` |
| `src/snip_url/services/tracking_service.py` | Recording of visits, link creations, rate-limit hits |
| `src/snip_url/services/analytics_service.py` | Builds the two analytics responses |
| `src/snip_url/repo/visitor_repo.py` | SQL for `link_visitors` |
| `src/snip_url/repo/client_repo.py` | SQL for `api_clients` |
| `src/snip_url/repo/stats_repo.py` | SQL for `daily_link_stats` and analytics queries |
| `src/snip_url/models/analytics.py` | Pydantic response models |
| `db_scripts/seed_data.py` | Deterministic, re-runnable seed |
| `db_scripts/schema.sql` | Reference schema (not read by the app) |
| `tests/test_data_model.py`, `tests/test_tracking.py`, `tests/test_privacy.py`, `tests/test_analytics.py`, `tests/test_seed.py` | New tests |

### Cross-cutting risks
- Old tests that touch the old table names must be renamed in the same change (tester task T7).
- Click recording (click event, visitor, last_clicked_at, daily stats) is ONE transaction; see 2.8.
- The coder writes only in `src/snip_url/` and `db_scripts/`. README is handled by the DOCS step.

## 2. Contract

### 2.1 `common/config.py`

```
DEFAULT_IP_HASH_SALT: str = "dev-only-salt-change-me"

class Settings:
    db_path: str
    base_url: str
    ip_hash_salt: str
    def __init__(self, db_path: str, base_url: str, ip_hash_salt: str = DEFAULT_IP_HASH_SALT) -> None

def load_settings() -> Settings
```
`load_settings` reads env `IP_HASH_SALT`. Unset or empty string -> `DEFAULT_IP_HASH_SALT`.

### 2.2 `services/privacy.py`

```
def hash_ip(ip: str, salt: str) -> str
```
Returns `hashlib.sha256((salt + ":" + ip).encode("utf-8")).hexdigest()` (64 lowercase hex chars). Same ip and salt -> same hash. Different salt -> different hash.

IP source: `request.client.host`, or the string `"unknown"` if `request.client` is None (same as the rate limiter). Under FastAPI TestClient the host is `"testclient"`.

### 2.3 `repo/db.py`

```
SCHEMA: str   # CREATE TABLE/INDEX IF NOT EXISTS for the 5 tables, new names (see section 3)
def get_connection(db_path: str) -> sqlite3.Connection          # unchanged
def commit(conn: sqlite3.Connection) -> None                    # conn.commit()
def rollback(conn: sqlite3.Connection) -> None                  # conn.rollback()
def table_exists(conn: sqlite3.Connection, name: str) -> bool
def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool
def rename_old_tables(conn: sqlite3.Connection) -> None
def add_missing_columns(conn: sqlite3.Connection) -> None
def init_db(db_path: str) -> None
```
- `rename_old_tables`: if `links` exists and `short_links` does not -> `ALTER TABLE links RENAME TO short_links`. Same for `clicks` -> `click_events`. Then `DROP INDEX IF EXISTS idx_clicks_code`. Does nothing on a new-name or empty database.
- `init_db` order: make folder, connect, `rename_old_tables`, `executescript(SCHEMA)`, `add_missing_columns`, commit, close. `add_missing_columns` uses `ALTER TABLE ... ADD COLUMN` only when `column_exists` is False, for the 3 new `short_links` columns and 3 new `click_events` columns (old rows get NULL; `is_custom_alias` gets default 0).
- Running `init_db` twice changes no data.

### 2.4 `repo/link_repo.py` (SQL only)

Commit rule: `insert_link`, `try_insert_link` keep committing as today. The click-path functions `insert_click`, `set_last_clicked` and `visitor_clicked_on_day` do NOT commit; the service ends the transaction with `db.commit` / `db.rollback` (see 2.8). Same for `visitor_repo.upsert_visitor` and `stats_repo.bump_daily_stat`. (`insert_click` no longer commits by itself; no existing test calls it directly.)

```
def code_exists(conn, code: str) -> bool                                  # table short_links
def insert_link(conn, code: str, original_url: str, created_at: str,
                is_custom_alias: bool = False, created_by_client: int | None = None) -> None
def try_insert_link(conn, code: str, original_url: str, created_at: str,
                    is_custom_alias: bool = False, created_by_client: int | None = None) -> bool
def get_link(conn, code: str) -> dict | None
    # keys: code, original_url, created_at, is_custom_alias (bool), created_by_client (int|None), last_clicked_at (str|None)
def insert_click(conn, code: str, clicked_at: str, visitor: int | None = None,
                 user_agent: str | None = None, referrer: str | None = None) -> None
def count_clicks(conn, code: str) -> int                                  # table click_events
def set_last_clicked(conn, code: str, clicked_at: str) -> None
def visitor_clicked_on_day(conn, code: str, visitor: int, day: str) -> bool
    # True if click_events has a row with this code, visitor and substr(clicked_at,1,10) == day
```
(all `conn` parameters are `sqlite3.Connection`.)

### 2.5 `repo/visitor_repo.py`

```
def upsert_visitor(conn, ip_hash: str, user_agent: str, now: str) -> int
```
Insert a new row (`visit_count` 1, `first_seen` = `last_seen` = now) or on conflict on `ip_hash`: `visit_count + 1`, `last_seen = now`, `user_agent = user_agent`. Does NOT commit. Return the row `id`.

### 2.6 `repo/client_repo.py`

```
def ensure_client(conn, ip_hash: str, now: str) -> int
    # INSERT OR IGNORE a row (links_created 0, times_rate_limited 0, first_seen=last_seen=now); return id. No counters change.
def add_link_created(conn, client_id: int, now: str) -> None
    # links_created + 1, last_seen = now
def add_rate_limited(conn, ip_hash: str, now: str) -> None
    # upsert by ip_hash: times_rate_limited + 1, last_seen = now (creates the row if missing)
```

### 2.7 `repo/stats_repo.py`

```
def bump_daily_stat(conn, code: str, day: str, new_visitor: bool) -> None
    # upsert (code, day): click_count + 1; unique_visitors + 1 only when new_visitor. Does NOT commit.
def get_daily_stats(conn, code: str, start_day: str) -> list[dict]
    # rows with day >= start_day: [{"day": str, "click_count": int, "unique_visitors": int}], ordered by day
def count_window_visitors_for_code(conn, code: str, start_day: str) -> int
    # COUNT(DISTINCT visitor) in click_events where code matches and substr(clicked_at,1,10) >= start_day (NULL visitors ignored)
def top_links(conn, start_day: str, limit: int) -> list[dict]
    # [{"code","original_url","clicks"}] from click_events joined to short_links, window clicks, ORDER BY clicks DESC, code ASC, LIMIT limit
def count_links_since(conn, start_day: str) -> int      # short_links with substr(created_at,1,10) >= start_day
def count_clicks_since(conn, start_day: str) -> int     # click_events in window
def count_visitors_since(conn, start_day: str) -> int   # COUNT(DISTINCT visitor) of click_events in window
def count_clients_since(conn, start_day: str) -> int    # api_clients with substr(last_seen,1,10) >= start_day
```

### 2.8 `services/tracking_service.py`

```
def visitor_user_agent(user_agent: str | None) -> str            # None -> ""
def record_click(conn, code: str, now: str, ip_hash: str,
                 user_agent: str | None, referrer: str | None) -> None
def record_link_created(conn, client_id: int, now: str) -> None
def client_id_for(conn, client_ip: str | None, salt: str, now: str) -> int | None
    # None when client_ip is None; else client_repo.ensure_client(conn, hash_ip(client_ip, salt), now)
def enforce_create_limit(conn, limiter: RateLimiter, client_ip: str, salt: str) -> None
    # calls limiter.enforce(client_ip); on AppError with code "rate_limited": client_repo.add_rate_limited(conn, hash_ip(client_ip, salt), utc_now_iso()) then re-raise the same error. Other AppErrors re-raise untouched.
```
`record_click` is ONE transaction: the click event, the visitor upsert, `last_clicked_at` and the daily stat are saved together or not at all. Steps (order decides "earlier click today"), all inside `try:`:
1. `visitor_id = visitor_repo.upsert_visitor(conn, ip_hash, visitor_user_agent(user_agent), now)`
2. `day = now[:10]`; `seen = link_repo.visitor_clicked_on_day(conn, code, visitor_id, day)` (before inserting this click)
3. `link_repo.insert_click(conn, code, now, visitor_id, user_agent, referrer)` (user_agent and referrer stored as given: None -> NULL)
4. `link_repo.set_last_clicked(conn, code, now)`
5. `stats_repo.bump_daily_stat(conn, code, day, not seen)`
6. `db.commit(conn)` once, after step 5.

`except Exception:` -> `db.rollback(conn)` then `raise`. No repo function in steps 1 to 5 commits. If any step fails, no click_events row, no visitor change, no last_clicked_at change and no daily_link_stats change remain. The redirect then returns the error (500) as today for unexpected errors. The tester proves this by monkeypatching `stats_repo.bump_daily_stat` (the last write) to raise; `record_click` must be called through `tracking_service.record_click` so the patch on `snip_url.repo.stats_repo.bump_daily_stat` is honoured (the service must call it as `stats_repo.bump_daily_stat(...)`, not via a from-import).

`utc_now_iso()` stays in `link_service`; tracking_service takes `now` as a parameter, except `enforce_create_limit`, which may import a copy-free helper by calling `datetime.now(timezone.utc).isoformat()` itself.

### 2.9 `services/link_service.py` (backward compatible)

```
def create_alias_link(conn, base_url: str, valid_url: str, alias: str,
                      client_id: int | None = None) -> CreateLinkResponse
    # try_insert_link(..., is_custom_alias=True, created_by_client=client_id); on success and client_id not None: tracking_service.record_link_created
def create_link(conn, base_url: str, url: str | None, alias: str | None = None,
                client_ip: str | None = None, salt: str = DEFAULT_IP_HASH_SALT) -> CreateLinkResponse
    # validate url (and alias) first; THEN client_id = tracking_service.client_id_for(...); insert with is_custom_alias False (no alias) or True (alias); after a successful insert call record_link_created if client_id is not None
def resolve_and_record_click(conn, code: str, client_ip: str | None = None, salt: str = DEFAULT_IP_HASH_SALT,
                             user_agent: str | None = None, referrer: str | None = None) -> str
    # 404 link_not_found if missing (nothing recorded). If client_ip is None: only insert the click row (visitor NULL) and `db.commit(conn)`. Else tracking_service.record_click.
def get_stats(...)  # unchanged
```
Failed validation (422) and alias conflict (409) must not increase `links_created`. Invalid requests that fail before the client step create no `api_clients` row.

### 2.10 `models/analytics.py`

```
class DailyStat(BaseModel):          day: str; clicks: int; unique_visitors: int
class LinkAnalyticsResponse(BaseModel): code: str; days: int; daily: list[DailyStat]; total_clicks: int; total_unique_visitors: int
class TopLink(BaseModel):            code: str; original_url: str; clicks: int
class SummaryResponse(BaseModel):    days: int; top_links: list[TopLink]; total_links: int; total_clicks: int; total_visitors: int; total_api_clients: int
```

### 2.11 `services/analytics_service.py`

```
def window_start_day(today: date, days: int) -> str     # (today - (days-1)).isoformat()
def build_day_list(today: date, days: int) -> list[str] # oldest first, ends with today, length == days, "YYYY-MM-DD"
def get_link_analytics(conn, code: str, days: int, today: date | None = None) -> LinkAnalyticsResponse
def get_summary(conn, days: int, today: date | None = None) -> SummaryResponse
```
`today` defaults to the current UTC date. Days are UTC calendar days; the window includes today.

`get_link_analytics`: 404 `AppError(404, "link_not_found", "Short code not found")` if the code is unknown. `daily` has exactly `days` entries, oldest first; a day with no `daily_link_stats` row has `clicks` 0 and `unique_visitors` 0. `total_clicks` = sum of `daily[].clicks`. `total_unique_visitors` = `stats_repo.count_window_visitors_for_code` (distinct visitors in the window; not the sum of daily values).

`get_summary`: `top_links` = `stats_repo.top_links(conn, start, 10)`; the four totals come from the `count_*_since` functions (window semantics from the spec Assumptions). Empty database -> `top_links` is `[]` and all totals 0.

### 2.12 `api/routes.py`

```
def client_ip_of(request: Request) -> str        # request.client.host or "unknown"
def limit_create(request: Request) -> None       # opens conn, calls tracking_service.enforce_create_limit(conn, request.app.state.rate_limiter, client_ip_of(request), settings.ip_hash_salt), closes conn
def create_link(...)    # passes client_ip=client_ip_of(request), salt=settings.ip_hash_salt
def redirect(...)       # passes client_ip, salt, user_agent=request.headers.get("user-agent"), referrer=request.headers.get("referer")
def link_analytics(code: str, request: Request, days: int = Query(7, ge=1, le=90)) -> LinkAnalyticsResponse
def analytics_summary(request: Request, days: int = Query(7, ge=1, le=90)) -> SummaryResponse
```
The two analytics routes are declared before the `/{code}` route.

### 2.13 Endpoints

Existing endpoints keep their status codes and bodies (201/409/422/429 create; 302/404 redirect; 200/404 stats; 200 health).

**GET /api/analytics/links/{code}?days=N**
- `days`: integer 1..90, default 7.
- 200:
```json
{"code": "abc", "days": 7,
 "daily": [{"day": "2026-10-02", "clicks": 0, "unique_visitors": 0}, "... 7 entries, oldest first, last is today (UTC)"],
 "total_clicks": 5, "total_unique_visitors": 3}
```
- 404 unknown code: `{"error": {"code": "link_not_found", "message": "Short code not found"}}`
- 422 bad `days` (0, 91, -1, `abc`, `2.5`): `{"error": {"code": "invalid_request", "message": "Request body is invalid"}}` (existing validation handler, unchanged).

**GET /api/analytics/summary?days=N**
- 200:
```json
{"days": 7,
 "top_links": [{"code": "abc", "original_url": "https://example.com", "clicks": 9}],
 "total_links": 3, "total_clicks": 12, "total_visitors": 4, "total_api_clients": 2}
```
- `top_links` has at most 10 entries ordered by clicks descending (ties by code ascending).
- 422 bad `days`: same body as above.

### 2.14 Hashing and recording rules (shared by coder and tester)
- Stored `ip_hash` = `sha256(salt + ":" + ip)` hex. Plain IPs never appear in any column.
- Missing User-Agent/Referer: `click_events.user_agent` and `.referrer` are NULL; `link_visitors.user_agent` is `""`.
- `daily_link_stats.day` and "today" come from the UTC timestamp used for the click (`now[:10]`).
- Timestamps are `datetime.now(timezone.utc).isoformat()` strings, so the first 10 chars are the UTC date.

### 2.15 `db_scripts/seed_data.py`

Run: `uv run python db_scripts/seed_data.py` (reads `DATABASE_PATH` through `load_settings()`; salt from `IP_HASH_SALT`).
```
SEED_RANDOM = 20260101        # fixed random seed
TABLES: tuple[str, ...]       # the 5 table names
def build_link_specs() -> list[dict]
    # 30 entries: 25 random-style fixed codes "seed01".."seed25" and 5 custom aliases "promo-1".."promo-5" (is_custom_alias true)
def build_click_plan(rng: random.Random, today: date) -> list[dict]
    # exactly 300 clicks; visitor index 0..39 (the first 40 clicks use each visitor once, rest random); day offset 0..13 days back; time of day from rng
def seed_exists(conn: sqlite3.Connection) -> bool         # True if "seed01" exists in short_links
def insert_seed(conn, salt: str, today: date) -> None      # one transaction
def count_tables(conn) -> dict[str, int]
def run_seed(db_path: str, salt: str, today: date | None = None) -> dict[str, int]
    # init_db(db_path) (creates missing tables), then if not seed_exists: insert_seed; returns counts per table
def main() -> None            # prints "<table>: <count>" one line per table in TABLES order
```
Seed content: 30 `short_links`; exactly 300 `click_events` between `today-13` and `today`; exactly 40 `link_visitors` (fake IPs `10.0.0.1`..`10.0.0.40`, hashed); exactly 5 `api_clients` (fake IPs `192.168.1.1`..`192.168.1.5`, hashed); every link gets `created_by_client` from the 5 clients; `link_visitors.visit_count/first_seen/last_seen/user_agent` computed from the clicks; `short_links.last_clicked_at` = latest click of the link (NULL if none); `daily_link_stats` computed from the clicks (clicks per link per day, distinct visitors per link per day); `api_clients.links_created` = number of links assigned to that client. All random choices use `random.Random(SEED_RANDOM)` only. Re-run: `seed_exists` is True -> nothing inserted or deleted, counts still printed. The script imports `snip_url` (installed by `uv sync`).

### 2.16 `db_scripts/schema.sql`
The 5 `CREATE TABLE` statements from section 3 as plain SQL with comments saying it is reference only. Must run cleanly in an empty SQLite database. Table and column names must match section 3 (same as `repo/db.py`).

## 3. Data model

All timestamps are ISO 8601 UTC text. Booleans are INTEGER 0/1.

**short_links** (renamed from links)
| Column | Type | Constraint |
|---|---|---|
| code | TEXT | PRIMARY KEY |
| original_url | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL |
| is_custom_alias | INTEGER | NOT NULL DEFAULT 0 |
| created_by_client | INTEGER | NULL, REFERENCES api_clients(id) |
| last_clicked_at | TEXT | NULL |

**click_events** (renamed from clicks)
| Column | Type | Constraint |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| code | TEXT | NOT NULL REFERENCES short_links(code) |
| clicked_at | TEXT | NOT NULL |
| visitor | INTEGER | NULL, REFERENCES link_visitors(id) |
| user_agent | TEXT | NULL |
| referrer | TEXT | NULL |

Index: `idx_click_events_code` on `click_events(code)`.

**link_visitors**
| Column | Type | Constraint |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| ip_hash | TEXT | NOT NULL UNIQUE |
| user_agent | TEXT | NOT NULL DEFAULT '' |
| first_seen | TEXT | NOT NULL |
| last_seen | TEXT | NOT NULL |
| visit_count | INTEGER | NOT NULL DEFAULT 0 |

**api_clients**
| Column | Type | Constraint |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| ip_hash | TEXT | NOT NULL UNIQUE |
| first_seen | TEXT | NOT NULL |
| last_seen | TEXT | NOT NULL |
| links_created | INTEGER | NOT NULL DEFAULT 0 |
| times_rate_limited | INTEGER | NOT NULL DEFAULT 0 |

**daily_link_stats**
| Column | Type | Constraint |
|---|---|---|
| code | TEXT | NOT NULL REFERENCES short_links(code) |
| day | TEXT | NOT NULL (YYYY-MM-DD, UTC) |
| click_count | INTEGER | NOT NULL DEFAULT 0 |
| unique_visitors | INTEGER | NOT NULL DEFAULT 0 |
| | | PRIMARY KEY (code, day) |

Migration of old rows: new columns NULL; `is_custom_alias` 0. No backfill. In the SQLite `ALTER ... ADD COLUMN` path, `is_custom_alias` is added as `INTEGER NOT NULL DEFAULT 0`.

## 4. Test plan

Tests use `tmp_path` databases (conftest `settings`/`client`). The tester reads the DB with plain `sqlite3`. Hash expectations use `hashlib.sha256(("<salt>:testclient").encode()).hexdigest()`.

| AC | Test (file) | What it checks |
|---|---|---|
| AC1 | `test_AC1_old_database_is_migrated_without_data_loss` (test_data_model) | Build old-schema DB (`links`, `clicks`, `idx_clicks_code`) with rows; start app; new names exist, old names gone, rows equal, new columns NULL / `is_custom_alias` 0 |
| AC2 | `test_AC2_second_startup_changes_nothing` | Start twice on migrated DB; row dumps equal |
| AC3 | `test_AC3_fresh_db_has_five_tables_with_columns` | Table names and column names per section 3 |
| AC4 | `test_AC4_custom_alias_flag_true_and_false` (test_tracking) | alias -> 1, none -> 0 |
| AC5 | `test_AC5_created_by_client_and_counters` | `created_by_client` = api_clients.id of the hashed IP; links_created 1 then 2; last_seen updated; failed validation / 409 does not increase it |
| AC6 | `test_AC6_rate_limited_counter_increments` | 10 creates then 429 x2: times_rate_limited 2, links_created 10 |
| AC7 | `test_AC7_redirect_stores_user_agent_and_referrer`, `test_AC7_missing_headers_stored_empty` | 302 + Location; row values; no headers -> NULL (click) and "" (visitor) |
| AC8 | `test_AC8_one_visitor_row_per_hash_with_counts` | 3 visits same IP: one row, visit_count 3, last_seen >= first_seen, user_agent = latest |
| AC9 | `test_AC9_last_clicked_at_set_on_redirect` | NULL before, equals latest click_events.clicked_at after |
| AC7-AC10 (atomicity) | `test_AC10_failure_midway_saves_no_click_data` (test_tracking) | Monkeypatch `snip_url.repo.stats_repo.bump_daily_stat` to raise; call `tracking_service.record_click` (or redirect with `raise_server_exceptions=False`); then click_events, link_visitors, daily_link_stats have unchanged counts and `last_clicked_at` is still NULL. A second test `test_AC10_failure_on_insert_click_saves_nothing` patches `link_repo.insert_click` to raise and checks the same (visitor visit_count unchanged, no new visitor row). A third `test_AC10_success_saves_all_four` checks all four are present together after a normal redirect. |
| AC10 | `test_AC10_daily_stats_clicks_and_unique_visitors` | 2 clicks same visitor same day -> click_count 2, unique_visitors 1; a pre-inserted click of another visitor same day then this visitor -> unique +1; second code independent |
| AC11 | `test_AC11_no_plain_ip_in_any_column`, `test_AC11_stored_hash_matches_salted_sha256` (test_privacy) | Scan every text value of all 5 tables for "testclient"; hash equality |
| AC12 | `test_AC12_default_salt_used_when_unset`, `test_AC12_different_salt_gives_different_hash` | `load_settings` with env unset/empty; `hash_ip` with 2 salts; app with custom salt stores that hash |
| AC13 | `test_AC13_default_7_days_with_zero_days` | Insert stats and click rows for some days directly; 7 entries, oldest first, last is today, zero days, totals |
| AC14 | `test_AC14_days_param_returns_exactly_n_entries` | days = 1, 30, 90 |
| AC15 | `test_AC15_unknown_code_404_error_shape` | `link_not_found`, error shape |
| AC16 | `test_AC16_invalid_days_returns_422` | 0, 91, -1, abc, 2.5 on both endpoints; error shape `invalid_request` |
| AC17 | `test_AC17_summary_top_links_and_totals` | 12 links with different click counts: 10 returned, descending, totals in window; rows older than the window excluded |
| AC18 | `test_AC18_summary_on_empty_db` | `top_links == []`, totals 0 |
| AC19 | `test_AC19_seed_creates_expected_counts` (test_seed) | 30 links (>=5 custom), 300 clicks within 14 days, 40 visitors, 5 clients; daily stats equal recomputed values from click_events |
| AC20 | `test_AC20_seed_is_identical_on_two_databases` | Same `today` passed; full table dumps equal |
| AC21 | `test_AC21_seed_rerun_adds_and_deletes_nothing` | Counts and dumps equal after second run; output printed |
| AC22 | `test_AC22_seed_prints_count_per_table` | `main()` output (capsys) has 5 lines `<table>: <n>` |
| AC23 | `test_AC23_schema_sql_defines_five_tables` | Execute the file in empty SQLite; 5 tables; columns equal to init_db's; `src/snip_url` has no reference to `schema.sql` |
| AC24 | `test_AC24_existing_suite_and_coverage` | Not a pytest test: verified by `uv run pytest --cov=snip_url` (all pass, >= 80%). Existing tests updated only by table-name rename (T8). |
| AC25 | No pytest test. README is updated by the orchestrator in the DOCS step; AC25 is verified there (README lists the 5 tables, both analytics paths, and the `seed_data.py` command). |

Also unit tests (named by AC): `test_AC5_hash_ip_is_stable_sha256` etc. in test_privacy are fine under AC11/AC12.

Seed tests load the script with `importlib.util.spec_from_file_location` from `db_scripts/seed_data.py` and call `run_seed(db_path, salt, today)`.

## 5. Risks

| Risk | Handling |
|---|---|
| Migration loses data or fails on old DBs | Use `ALTER TABLE RENAME` (no copy); AC1 test builds a real old-schema DB; `init_db` is idempotent (AC2). |
| SQLite FK references after rename | Modern SQLite rewrites FK targets on rename. AC1 test inserts a click referencing a link and checks FK integrity with `PRAGMA foreign_key_check`. |
| Old index name stays after rename | Dropped by `rename_old_tables`; new index created by SCHEMA. |
| Existing tests that use old table names fail | T8 renames them (names only). |
| Click, visitor, last_clicked_at and daily stats getting out of step | One transaction in `record_click`: repo click-path functions never commit; one `db.commit` at the end; `db.rollback` and re-raise on any error. Proven by the atomicity tests (failure in the last write and in the first write save nothing). Link creation (insert + client counter) is a separate, non-click flow and keeps its own commits; a failure there cannot corrupt click data. |
| README not updated by coder | By design: DOCS step (orchestrator) owns README and AC25. |
| Failed create (409 alias taken) leaves an `api_clients` row with 0 links | Counter not bumped; accepted and documented. |
| Rate-limit DB write fails or limiter error | `enforce_create_limit` only intercepts `rate_limited` and re-raises the original error, so the 429 and `Retry-After` stay unchanged. |
| Summary and per-link totals mix data sources | Defined: per-day values from `daily_link_stats`; distinct visitors and summary from `click_events`. Tests insert both consistently. |
| Window edges (UTC midnight) | All comparisons use the `YYYY-MM-DD` prefix of ISO UTC strings; tests pass `today` to services where needed. |
| Seed differs between days ("last 14 days" is relative) | `run_seed` takes `today`; tests fix it. Content is otherwise fully determined by `SEED_RANDOM`. |
| Seed partial state (interrupted run) | `insert_seed` runs in one transaction. |
| 422 message says "Request body is invalid" for query errors | Existing handler unchanged (out of scope); tests check status, code and shape only. |
| IP behind proxy | Direct client IP only (spec assumption). |
