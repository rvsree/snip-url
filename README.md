# snip-url

A small URL shortener built with FastAPI and SQLite.
It is built through a controlled agentic workflow: specs, plans, tests and human approvals.

## Setup (Windows PowerShell)

```powershell
uv sync
uv run pytest --cov=snip_url
uv run uvicorn snip_url.main:app --reload
```

## Limitations
