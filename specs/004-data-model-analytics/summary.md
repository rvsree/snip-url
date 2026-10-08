# Summary: 004-data-model-analytics

## What was built
- Five-table data model: `short_links`, `click_events` (renamed from `links` and `clicks` by a startup migration, no data copy), plus new `link_visitors`, `api_clients`, `daily_link_stats`. New columns on existing tables.
- Tracking: link creation, rate-limit hits and redirects are recorded. Visitors and API clients are identified by `sha256(salt:ip)`; salt from `IP_HASH_SALT`. A click, its visitor update, `last_clicked_at` and the daily stat are saved in one transaction.
- Endpoints: `GET /api/analytics/links/{code}?days=N` and `GET /api/analytics/summary?days=N` (days default 7, 1 to 90, else 422).
- `db_scripts/seed_data.py` (deterministic: 30 links, 40 visitors, 300 clicks; re-run adds nothing) and `db_scripts/schema.sql`.
- Config: `.claude/agents/coder.md` now allows the coder to write in `db_scripts/`.
- README updated in the DOCS step.

## Tests and coverage
- `uv run pytest --cov=snip_url --cov-fail-under=80`: 81 passed, 0 failed. Coverage 98.53%.
- Existing tests: table names only were renamed (test_links, test_alias, test_redirect, test_startup_db); no assertion changed.

## Approvals (exact replies)
- Open-question answers: paths `/api/analytics/...`; invalid N rejected with 422; summary takes the same N; totals limited to last N days; migrated old rows keep empty visitor data and `is_custom_alias` false; seed exactly 300 clicks and 40 visitors.
- Approval 1 (spec): "yes"
- Approval 2 (plan), first round: "no: 1) Fix risk 2: record the click event, the visitor update and the daily_link_stats update in ONE database transaction, so they can never get out of step. Add a test that proves a failure in the middle saves none of them. 2) Remove T7: README is updated in the DOCS step; the coder writes only in src/ and db_scripts/. Then show the plan again."
- Approval 2 (plan), second round: "yes"
- Approval 3 (merge): "yes"

## Retries and rollbacks
- One re-plan at Approval 2 (above).
- The stop hook fired once while the coder was still writing (6 seed tests failed with FileNotFoundError because `db_scripts/schema.sql` did not exist yet). It was not a code or test fault; verify passed after the coder finished. No fix rounds, no rollback.

## Open items
- Summary totals definition (links created in window, clicks in window, distinct visitors in window, clients last seen in window) was an assumption shown at Approval 1.
- A failed create (409) can leave an `api_clients` row with 0 links created.
- Analytics tests build dates from the current UTC date, so a run across UTC midnight could fail.
- `tests/test_seed.py` and the seed script were not run by the subagents; they were first run in VERIFY.
