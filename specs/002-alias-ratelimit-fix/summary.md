# Summary: 002-alias-ratelimit-fix

## What was built
- Custom `alias` on `POST /api/links` (3-30 chars: letters, digits, `-`; case-sensitive).
  - 422 `invalid_alias`, 422 `reserved_alias` (matched ignoring case), 409 `alias_taken` (also when equal to an existing random code).
- Rate limit on `POST /api/links`: 10 requests per 60 s per direct client IP, all attempts count, `X-Forwarded-For` ignored.
  - 429 `rate_limited` with a `Retry-After` header. In-memory, per process.
- BUG-01 fixed: redirect returns 302 instead of 301; the three loosened test assertions are restored to `== 302`.
- DEF-02 fixed: `init_db` runs in the FastAPI lifespan, so importing the app creates no database.
  - `SNIP_DB_PATH` renamed to `DATABASE_PATH` (default `data/snip_url.db`, folder created at startup).
- Regression test: `test_BUG01_redirect_is_302_and_counts_clicks` (exactly 302, two visits give click_count 2).
- `conftest.py` builds a fresh app and rate limiter per test.

## Tests and coverage
- `uv run pytest --cov=snip_url --cov-fail-under=80`: 45 passed, 0 failed.
- Coverage 98.81% (252 statements, 3 missed, all in `link_service.py`).

## Approvals (human's exact replies)
- Spec questions (6): invalid and reserved alias both 422; alias case-sensitive with reserved matched case-insensitively; field `alias`; count all requests, direct IP only; rename to `DATABASE_PATH` only; alias equal to a random code is 409.
- Approval 1 (spec): first reply "no: renumber the acceptance criteria in order, AC1 to AC22 with no gaps, keeping the same content. Then show the summary again."; second reply "yes".
- Approval 2 (plan): first reply "no: 1) Remove T6. README is updated in the DOCS step; the coder writes only in src/. 2) Add a named regression test for BUG-01 that asserts the redirect is exactly 302 and that two visits to the same link give a click count of 2. 3) State in the plan that conftest.py gives every test a fresh rate limiter, so tests never affect each other. Then show the plan again."; second reply "yes".
- Approval 3 (merge): "yes".

## Retries and rollbacks
- Fix rounds: 0. Rollbacks: none.
- First verify run had 1 failure (AC22 README check), expected until the DOCS step updated `README.md`; it passed after.

## Open items
- `.env.example` still needs `SNIP_DB_PATH` renamed to `DATABASE_PATH` (agents may not read or edit `.env.*`).
- Untracked leftover `snip_url.db` at the repo root is not deleted or committed.
- AC9-AC11 sit before AC12-AC15 in the spec, though AC11 conceptually depends on the limit; not reordered.
