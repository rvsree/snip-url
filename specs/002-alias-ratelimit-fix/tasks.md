# Tasks: 002-alias-ratelimit-fix

Coder tasks follow plan.md section 2 and write only in `src/`. Tester tasks depend only on the contract, not on coder tasks. `[P]` = can run in parallel. README.md is updated by the orchestrator in the DOCS step, not by a task here.

| ID | Owner | Files | Depends on | Notes |
|---|---|---|---|---|
| T1 [P] | coder | `src/snip_url/common/config.py`, `src/snip_url/common/errors.py`, `src/snip_url/repo/db.py` | none | `DATABASE_PATH` default `data/snip_url.db`; `AppError.headers`; `init_db` makes parent folder |
| T2 [P] | coder | `src/snip_url/repo/link_repo.py`, `src/snip_url/models/link.py` | none | `try_insert_link`; `alias` field |
| T3 [P] | coder | `src/snip_url/services/rate_limiter.py` | none | `RateLimiter` with injectable clock, `rate_limited` 429 + Retry-After |
| T4 | coder | `src/snip_url/services/link_service.py` | T1, T2 | `validate_alias`, `create_alias_link`, `create_link(..., alias=None)`; codes `invalid_alias`, `reserved_alias`, `alias_taken` |
| T5 | coder | `src/snip_url/api/routes.py`, `src/snip_url/main.py` | T1, T3, T4 | 302 redirect (BUG-01), `limit_create` dependency, lifespan `init_db`, `create_app(settings, clock)` |
| T6 [P] | tester | `tests/conftest.py`, `tests/test_redirect.py`, `tests/test_persistence.py` | none | `client` fixture uses `with` and builds a fresh app and limiter per test; restore 302 assertions; add AC16, AC17 and `test_BUG01_redirect_is_302_and_counts_clicks` (exactly 302, two visits give click_count 2) |
| T7 [P] | tester | `tests/test_alias.py` | none | AC1 to AC10 |
| T8 [P] | tester | `tests/test_rate_limit.py` | none | AC11 to AC15 plus limiter unit tests with fake clock |
| T9 [P] | tester | `tests/test_startup_db.py` | none | AC18 to AC22 |
| T10 | tester | (no new files) run `uv run pytest --cov=snip_url`; report failures to the orchestrator without editing `src/` | T1 to T9 | VERIFY step, coverage at least 80% |

Parallel groups: T1, T2, T3 run together; T4 then T5 follow. T6 to T9 start at the same time as T1 (contract only). Join at T10. README (AC22) is done by the orchestrator in the DOCS step after VERIFY.
