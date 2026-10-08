# snip-url

A small URL shortener (FastAPI + SQLite), built through a controlled agentic workflow: Claude Code subagents write specs, plans, code and tests; hooks enforce the rules in code; a human approves the spec, the plan and the merge.

## For reviewers (5 minutes)

snip-url is two things: a working URL shortener, and the agentic SDLC workflow that built it. The workflow is what is assessed; the app is the example product. A requirement goes in through `/sdlc`, and a reviewed, tested result comes out, with human approvals at the high-impact steps. Start here:

1. [docs/SCHWAB_SPEC_MAPPER.md](docs/SCHWAB_SPEC_MAPPER.md): every Schwab requirement, where it is met, the evidence, and the gaps.
2. [docs/architecture.md](docs/architecture.md): workflow, current application and target design (not built).
3. [docs/data-model.html](docs/data-model.html): the five tables (open in a browser).
4. [docs/scenarios.md](docs/scenarios.md): S1-S4 and the two hook drills, with results.
5. [docs/metrics.md](docs/metrics.md): success rate, retries, rollbacks, MTTR, latency, from the audit log.
6. [.claude/](.claude/): the four subagents, the `/sdlc` skill, the three hooks and `settings.json`.
7. [prompts/](prompts/): every prompt given to Claude Code, with approval replies and results.
8. Run it (Windows PowerShell):

```powershell
uv sync
uv run pytest --cov=snip_url
uv run python db_scripts/seed_data.py
uv run uvicorn snip_url.main:app --reload
```

Then open http://localhost:8000/docs.

## Quick start (Windows PowerShell)

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync                                  # install packages
uv run pytest --cov=snip_url             # run tests (81 tests, coverage gate 80%)
uv run python db_scripts/seed_data.py    # optional: 30 links, 40 visitors, 300 clicks
uv run uvicorn snip_url.main:app --reload
```

Open http://localhost:8000/docs for the Swagger page. The database is `data/snip_url.db`, created at startup.

Settings (environment variables): `DATABASE_PATH` (default `data/snip_url.db`), `SNIP_BASE_URL` (default `http://localhost:8000`), `IP_HASH_SALT` (a development default is used if unset).

## Endpoints

Errors always look like `{"error": {"code": "...", "message": "..."}}`. Full list of codes: [docs/design.md](docs/design.md) section 3.

| Method | Path | Result |
|---|---|---|
| POST | `/api/links` | 201 with `code`, `short_url`, `original_url`, `created_at`. Optional `alias` sets a custom code |
| GET | `/{code}` | 302 redirect to the original URL; records a click |
| GET | `/api/links/{code}/stats` | 200 with `code`, `original_url`, `created_at`, `click_count` |
| GET | `/api/analytics/links/{code}?days=N` | 200 with clicks and unique visitors per UTC day; unknown code gives 404 |
| GET | `/api/analytics/summary?days=N` | 200 with top links and totals for the last N days |
| GET | `/health` | 200 `{"status": "ok"}` |

`days` is optional: default 7, from 1 to 90; anything else gives 422.

```powershell
curl.exe -X POST http://localhost:8000/api/links -H "Content-Type: application/json" -d '{\"url\": \"https://example.com\"}'
curl.exe -X POST http://localhost:8000/api/links -H "Content-Type: application/json" -d '{\"url\": \"https://example.com\", \"alias\": \"my-link\"}'
curl.exe -i http://localhost:8000/my-link
curl.exe http://localhost:8000/api/links/my-link/stats
curl.exe "http://localhost:8000/api/analytics/links/my-link?days=7"
curl.exe "http://localhost:8000/api/analytics/summary?days=7"
curl.exe http://localhost:8000/health
```

Rules:
- Only http/https URLs up to 2048 characters. Bad input gives 422; an unknown code gives 404.
- `alias`: 3 to 30 characters of letters, digits or `-`; case-sensitive. Bad format gives 422 `invalid_alias`, a reserved word (any case) 422 `reserved_alias`, one already used 409 `alias_taken`.
- `POST /api/links` allows 10 requests per 60 seconds per client IP (all attempts count). The 11th gives 429 `rate_limited` with a `Retry-After` header. Redirects, stats and analytics are not limited.

## Features

- Create short links with a random 7-character base62 code, or a custom alias.
- 302 redirect (not 301, so every click reaches the server and is counted).
- Click tracking in one database transaction: click event, visitor update, last-clicked time and daily stat are saved together or not at all.
- Per-link and summary analytics (clicks and unique visitors per day).
- Create rate limit per IP (in memory).
- IP addresses are never stored: only `sha256(salt:ip)`.
- Five SQLite tables; re-runnable seed script; startup migration of the old table names.
- Workflow: `/sdlc` skill, four subagents, three hooks, three human approvals, audit log, metrics.

## How the /sdlc workflow works

Run it from the terminal with `claude` in the project folder. `/sdlc` does not appear in the VS Code chat panel.

```powershell
claude
# then, inside Claude Code:
/sdlc specs/005-my-feature       # the folder must contain request.md
```

Steps (see [.claude/skills/sdlc/SKILL.md](.claude/skills/sdlc/SKILL.md)):

1. **SPEC**: `spec-writer` writes `spec.md`, asking questions if the request is vague. **Approval 1** (spec).
2. **PLAN**: `planner` writes `plan.md` (impact analysis and file/function contract) and `tasks.md`. **Approval 2** (plan and tasks).
3. **BUILD**: `coder` (src/, db_scripts/) and `tester` (tests/) run in parallel.
4. **VERIFY**: the `verify_gate` hook runs pytest and coverage (80%). Fail: up to 2 fix rounds, then rollback of `src/` and `tests/` and a stop for the human.
5. **DOCS**, then the summary is written. **Approval 3** (merge): the human approves; the commit uses named `git add` only. The human pushes.

Hooks (code, not AI): `policy_guard.py` blocks unsafe writes and commands, `audit_log.py` writes `logs/audit.jsonl`, `verify_gate.py` is the test gate. Deny rules in `.claude/settings.json` block reading `.env` files and `git push`.

## Metrics

```powershell
uv run python scripts/metrics.py
```

Reads `logs/audit.jsonl` and git; prints runs, success rate, retries, rollbacks, MTTR and minutes per run, and writes [docs/metrics.md](docs/metrics.md).

## Project structure

```
src/snip_url/     api/ services/ repo/ models/ common/ main.py   the app
tests/            pytest tests
db_scripts/       schema.sql (reference), seed_data.py
scripts/          metrics.py, seed_bug01.py
specs/            constitution.md; 001-core-api, 002-alias-ratelimit-fix,
                  003-viral-traffic, 004-data-model-analytics
.claude/          agents/, skills/sdlc/, hooks/, settings.json
prompts/          one file per prompt given to Claude Code
docs/             documentation (index below)
logs/             audit.jsonl (tracked as evidence)
data/             snip_url.db (git-ignored)
```

## Documentation index

| File | What it is |
|---|---|
| [docs/project_brief.md](docs/project_brief.md) | Approved brief: problem, approach, trade-offs, risks, plan |
| [docs/SCHWAB_SPEC_MAPPER.md](docs/SCHWAB_SPEC_MAPPER.md) | Schwab requirements mapped to evidence and status |
| [docs/architecture.md](docs/architecture.md) | Workflow, application and target design diagrams |
| [docs/architecture.html](docs/architecture.html) | Rendered architecture diagrams |
| [docs/diagrams/](docs/diagrams/) | Diagram images: workflow, application, target design, data model |
| [docs/data-model.html](docs/data-model.html) | Data model, conceptual and physical |
| [docs/design.md](docs/design.md) | API, data model, key flows, NFRs, estimates, limitations |
| [docs/decisions.md](docs/decisions.md) | Key decisions with alternatives and trade-offs |
| [docs/scenarios.md](docs/scenarios.md) | S1-S4 and hook drills |
| [docs/metrics.md](docs/metrics.md) | Reliability metrics (generated) |
| [docs/review-checklist.md](docs/review-checklist.md) | Progress, golden tests G1-G24, deviation log |
| `specs/<feature>/` | request, spec, plan, tasks, summary per feature |
| `prompts/` | Prompt log |

## Claude Code version

Built with Claude Code **2.1.294** (checked with `claude --version`). It was updated during the project, from 2.1.270 to 2.1.293 (V7); behavior may differ in other versions.

## Limitations

Full list with IDs: [docs/design.md](docs/design.md) section 7.

- Step order of `/sdlc` is followed by the AI, not enforced by code; only tests, writes and logging are enforced by hooks (V8).
- Rate limiter is in memory and per process; it resets on restart.
- Same URL submitted twice gives two codes; no expiry, edit, delete or list.
- No authentication; analytics endpoints are open.
- Identity is the direct IP hash; `X-Forwarded-For` is ignored on purpose.
- SQLite allows one writer and every redirect writes; not suitable for high traffic. No load test; the viral-traffic target (S3) is undecided.
- Random-code insert has a check-then-insert race that is not retried (V13).
- A failed create can leave an `api_clients` row with 0 links created.
- `/docs` does not list 404/409/429 and shows FastAPI's default 422 format (V10); a bad `?days` says "Request body is invalid" (V11).
- Menu choices at approvals are logged as "a decision" only (V12); exact replies are in each `summary.md`.
- MTTR rests on one fail-to-pass pair; no per-stage latency.
- The target design (CDN, gateway, Kafka, Redis, Postgres) is documented, not built.
