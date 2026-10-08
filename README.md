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
| POST | `/api/links` | 201 with `code`, `short_url`, `original_url`, `created_at` |
| GET | `/{code}` | 302 redirect to the original URL; records a click |
| GET | `/api/links/{code}/stats` | 200 with `code`, `original_url`, `created_at`, `click_count` |
| GET | `/health` | 200 `{"status": "ok"}` |

Only http/https URLs up to 2048 characters are accepted. Bad input gives 422 and an unknown code gives 404,
both as `{"error": {"code": "...", "message": "..."}}`.

Settings (environment variables): `SNIP_DB_PATH` (default `snip_url.db`), `SNIP_BASE_URL` (default `http://localhost:8000`).

## Try it

```powershell
uv run uvicorn snip_url.main:app --reload
curl.exe -X POST http://localhost:8000/api/links -H "Content-Type: application/json" -d '{\"url\": \"https://example.com\"}'
curl.exe -i http://localhost:8000/<code>
curl.exe http://localhost:8000/api/links/<code>/stats
curl.exe http://localhost:8000/health
```

## Limitations

- Same URL submitted twice gives two codes; no custom aliases, expiry, edit, delete or list.
