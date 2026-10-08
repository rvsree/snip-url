# Summary: 001-core-api

## What was built
Core URL shortener API (FastAPI + SQLite):
- `POST /api/links` (201), `GET /{code}` (302, records a click), `GET /api/links/{code}/stats`, `GET /health`.
- Layers: common (config, errors), models, repo (SQLite), services, api, `main.create_app`.
- Validation errors return 422; unknown codes return 404; errors use `{"error": {"code", "message"}}`.

## Tests and coverage
- 17 tests passed, 0 failed (covers AC1-AC13).
- Coverage 98.25% (gate 80%). Misses: 3 lines in `services/link_service.py`.

## Approvals (human's exact replies)
1. Approval 1 (spec): "yes"
2. Approval 2 (plan and tasks): "yes"
3. Approval 3 (merge): "yes"

## Retries and rollbacks
- Fix rounds: 0. Rollbacks: 0.

## Open items
- `snip_url.db` is created in the working directory when `snip_url.main` is imported; it was not committed and should be git-ignored.
- `logs/audit.jsonl` is tracked despite being documented as git-ignored; its modification was not committed.
- Git warns about LF to CRLF conversion on the committed files.
- The human still needs to push (not done by the workflow).
