# Reliability metrics

Generated 2026-10-08 14:57 UTC.

| Scenario | Start (UTC) | Minutes | Outcome | Replies | No replies | Menu decisions | Retries | Rollbacks | Agent calls |
|---|---|---|---|---|---|---|---|---|---|
| hook test | 2026-10-08 01:21 | 0.6 | incomplete | 0 | 0 | 0 | 2 | 1 | - |
| specs/001-core-api | 2026-10-08 01:43 | 45.7 | committed | 7 | 0 | 0 | 0 | 0 | spec-writer=1, planner=1, coder=1, tester=1 |
| specs/002-alias-ratelimit-fix | 2026-10-08 03:00 | 30.3 | committed | 13 | 2 | 2 | 0 | 0 | spec-writer=1, planner=1, coder=1, tester=1 |
| specs/003-viral-traffic | 2026-10-08 03:40 | 5.0 | stopped at spec | 4 | 0 | 0 | 0 | 0 | spec-writer=1 |
| hook test | 2026-10-08 13:29 | 14.3 | incomplete | 4 | 0 | 0 | 1 | 0 | - |
| specs/004-data-model-analytics | 2026-10-08 13:44 | 35.3 | committed | 6 | 0 | 6 | 1 | 0 | spec-writer=1, planner=1, coder=1, tester=1 |

- Runs: 6 (4 scored, 2 hook test)
- Success rate (committed or stopped at spec, hook tests excluded): 100%
- Total retries: 4
- Total rollbacks: 1
- MTTR (seconds): 7.8
- MTTR pairs (fail time, pass time, seconds):
  - 2026-10-08 13:30:02, 2026-10-08 13:30:10, 7.8
