# Tasks: 001-core-api

Coder tasks follow the contract in plan.md. Tester tasks depend only on the contract, not on coder tasks.

## Coder

- T1 [P] owner: coder
  files: `src/snip_url/common/__init__.py`, `common/config.py`, `common/errors.py`, `models/__init__.py`, `models/link.py`
  depends on: none

- T2 [P] owner: coder
  files: `src/snip_url/repo/__init__.py`, `repo/db.py`, `repo/link_repo.py`
  depends on: none

- T3 owner: coder
  files: `src/snip_url/services/__init__.py`, `services/link_service.py`
  depends on: T1, T2

- T4 owner: coder
  files: `src/snip_url/api/__init__.py`, `api/routes.py`, `src/snip_url/main.py`
  depends on: T1, T3

## Tester

- T5 [P] owner: tester
  files: `tests/conftest.py` (fixtures `settings`, `client`)
  depends on: none (contract only)

- T6 [P] owner: tester
  files: `tests/test_links.py` (AC1-AC4), `tests/test_health.py` (AC12)
  depends on: T5

- T7 [P] owner: tester
  files: `tests/test_redirect.py` (AC5-AC8), `tests/test_stats.py` (AC9, AC10)
  depends on: T5

- T8 [P] owner: tester
  files: `tests/test_persistence.py` (AC11), `tests/test_service.py` (AC13)
  depends on: T5

## Final

- T9 owner: tester
  files: none (run `uv run pytest --cov=snip_url`; report results, coverage at least 80%)
  depends on: T4, T6, T7, T8
