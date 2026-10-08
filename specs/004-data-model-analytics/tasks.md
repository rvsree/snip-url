# Tasks: Data model, analytics and seed data (004)

Coder writes only in `src/snip_url/` and `db_scripts/`. Tester writes in `tests/` only. README is updated by the orchestrator in the DOCS step (not a coder task). Tester tasks depend only on the contract in `plan.md`, not on coder tasks. [P] = can run in parallel.

## Coder tasks

| ID | Owner | Files | Depends on | Notes |
|---|---|---|---|---|
| T1 [P] | coder | `src/snip_url/common/config.py`, `src/snip_url/services/privacy.py`, `src/snip_url/models/analytics.py` | none | Plan 2.1, 2.2, 2.10 |
| T2 [P] | coder | `src/snip_url/repo/db.py` | none | Schema, rename migration, add missing columns, `commit`/`rollback` helpers (2.3, section 3) |
| T3 | coder | `src/snip_url/repo/link_repo.py`, `src/snip_url/repo/visitor_repo.py`, `src/snip_url/repo/client_repo.py`, `src/snip_url/repo/stats_repo.py` | T2 | Plan 2.4 to 2.7. Click-path functions do not commit. |
| T4 | coder | `src/snip_url/services/tracking_service.py`, `src/snip_url/services/analytics_service.py`, `src/snip_url/services/link_service.py` | T1, T3 | Plan 2.8, 2.9, 2.11. `record_click` is one transaction (commit once, rollback on error). Old call signatures keep working. |
| T5 | coder | `src/snip_url/api/routes.py` (and `src/snip_url/main.py` only if needed) | T4 | Plan 2.12, 2.13. Analytics routes before `/{code}`. |
| T6 [P] | coder | `db_scripts/seed_data.py`, `db_scripts/schema.sql` | T1, T2 | Plan 2.15, 2.16 |

## Tester tasks

| ID | Owner | Files | Depends on | Notes |
|---|---|---|---|---|
| T7 [P] | tester | `tests/test_links.py`, `tests/test_alias.py`, `tests/test_redirect.py`, `tests/test_startup_db.py` | none | Rename `links`->`short_links`, `clicks`->`click_events` in raw SQL and `count_rows` calls only. Do not weaken assertions. (AC24) |
| T8 [P] | tester | `tests/test_data_model.py` | none | AC1, AC2, AC3 |
| T9 [P] | tester | `tests/test_tracking.py`, `tests/test_privacy.py` | none | AC4 to AC12, plus the atomicity tests: a failure in the middle of recording saves no click event, visitor update, last_clicked_at or daily stat (plan section 4) |
| T10 [P] | tester | `tests/test_analytics.py` | none | AC13 to AC18 |
| T11 [P] | tester | `tests/test_seed.py` | none | AC19 to AC23 |

## Not a task here

- README and AC25: handled by the orchestrator in the DOCS step.

## Final check (after T1 to T11)

Run `uv run pytest --cov=snip_url`: all tests pass and coverage is at least 80% (AC24). No test is weakened, skipped or deleted.
