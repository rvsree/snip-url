# snip-url

A small URL shortener built with FastAPI and SQLite.
It is built through a controlled agentic workflow: specs, plans, tests and human approvals.

## Setup (Windows PowerShell)

```powershell
uv sync
uv run pytest --cov=snip_url
uv run uvicorn snip_url.main:app --reload
```

## Endpoints

| Method | Path | Result |
|---|---|---|
| POST | `/api/links` | 201 with `code`, `short_url`, `original_url`, `created_at`; optional `alias` sets a custom code |
| GET | `/{code}` | 302 redirect to the original URL; records a click |
| GET | `/api/links/{code}/stats` | 200 with `code`, `original_url`, `created_at`, `click_count` |
| GET | `/api/analytics/links/{code}?days=N` | 200 with `code`, `days`, `daily` (clicks and unique visitors per UTC day, oldest first, ending today), `total_clicks`, `total_unique_visitors`; unknown code gives 404 |
| GET | `/api/analytics/summary?days=N` | 200 with `days`, `top_links`, `total_links`, `total_clicks`, `total_visitors`, `total_api_clients`, all for the last N days |
| GET | `/health` | 200 `{"status": "ok"}` |

`days` is optional: default 7, from 1 to 90. Anything else gives 422.

Only http/https URLs up to 2048 characters are accepted. Bad input gives 422 and an unknown code gives 404,
both as `{"error": {"code": "...", "message": "..."}}`.

### Custom alias

`alias` is optional: 3 to 30 characters of letters, digits or `-`; case-sensitive.
- Bad length or characters gives 422 `invalid_alias`.
- A reserved word (any case) gives 422 `reserved_alias`.
- An alias already in use gives 409 `alias_taken`.

### Rate limit

`POST /api/links` allows 10 requests per 60 seconds per client IP (all attempts count, including failed ones).
The 11th gives 429 `rate_limited` with a `Retry-After` header (seconds). Redirects and stats are not limited.

Settings (environment variables): `DATABASE_PATH` (default `data/snip_url.db`; the folder is created at startup),
`SNIP_BASE_URL` (default `http://localhost:8000`).

## Data model

Five SQLite tables (full DDL in `db_scripts/schema.sql`; the app creates them itself at startup and renames the old `links` and `clicks` tables if found):

- `short_links`: the short codes and their URLs (plus `is_custom_alias`, `created_by_client`, `last_clicked_at`).
- `click_events`: one row per redirect (with user agent and referrer).
- `link_visitors`: one row per visitor, identified by a salted hash of the client IP.
- `api_clients`: one row per API client, with links created and rate-limited counts.
- `daily_link_stats`: clicks and unique visitors per link per UTC day.

IP addresses are never stored, only `sha256(salt:ip)`. Set the salt with `IP_HASH_SALT` (a development default is used if unset).

## Seed sample data

```powershell
uv run python db_scripts/seed_data.py
```

Adds 30 links, 40 visitors and 300 clicks in the configured database, the same every time. Running it again adds nothing.
It prints one row count per table.

## Try it

```powershell
uv run uvicorn snip_url.main:app --reload
curl.exe -X POST http://localhost:8000/api/links -H "Content-Type: application/json" -d '{\"url\": \"https://example.com\"}'
curl.exe -X POST http://localhost:8000/api/links -H "Content-Type: application/json" -d '{\"url\": \"https://example.com\", \"alias\": \"my-link\"}'
curl.exe -i http://localhost:8000/<code>
curl.exe http://localhost:8000/api/links/<code>/stats
curl.exe "http://localhost:8000/api/analytics/links/<code>?days=7"
curl.exe "http://localhost:8000/api/analytics/summary?days=7"
curl.exe http://localhost:8000/health
```

## Limitations

- Same URL submitted twice gives two codes; no expiry, edit, delete or list.
- The rate limit is in memory and per process; it resets on restart.
