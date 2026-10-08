# snip-url: Scenarios

Author: Sree | Date: 2026-10-08 | Status: Draft for review

Four feature scenarios ran live through `/sdlc`, and two hook drills tested the gates. Numbers come from the `summary.md` files and from [metrics.md](metrics.md) (generated 2026-10-08 14:57 UTC). Dates are the local commit dates (UTC-5); metrics.md shows UTC start times. "Approvals" are the human's replies; the exact text is in each `summary.md`.

| ID | Type | Result in one line |
|---|---|---|
| S1 | Greenfield, well-defined | Committed; 17 tests, 98.25% coverage |
| S2 | Brownfield (feature, bug fix, refactor) | Committed after 2 plan rejections; 45 tests, 98.81% |
| S3 | Ambiguous | Stopped at the approved spec; nothing built |
| S4 | Brownfield (schema, analytics, seed) | Committed after 1 plan rejection; 81 tests, 98.53% |
| Drill 1 | Gate retry and rollback | 2 blocks, then rollback |
| Drill 2 | Recovery | Fail, fix, pass; MTTR 7.8 s |

## S1: Core URL shortener

- **Request type:** Greenfield, well-defined. 8 numbered requirements: create, validate (http/https, 2048 characters), 302 redirect, 404, click record, stats, SQLite persistence, health.
- **What it proves:** Decomposition and a build from zero; contract-driven parallel build (coder and tester); the VERIFY gate; spec-to-summary lineage.
- **Human decisions:** Approval 1 "yes"; Approval 2 "yes"; Approval 3 "yes". No rejections.
- **Result:** 17 tests passed, coverage 98.25% (gate 80%), 0 retries, 0 rollbacks. 45.7 minutes end to end. Committed 2026-10-07 (`08c454b`).
- **Found for later:** the database file was created in the project root on import (DEF-02, fixed in S2).
- **Links:** [request](../specs/001-core-api/request.md), [spec](../specs/001-core-api/spec.md), [plan](../specs/001-core-api/plan.md), [tasks](../specs/001-core-api/tasks.md), [summary](../specs/001-core-api/summary.md); [prompts/04](../prompts/04-s1-core-api.md).

## S2: Custom alias, rate limit, BUG-01, DEF-02

- **Request type:** Brownfield on S1: enhancement (alias, rate limit), bug fix (BUG-01), refactor (DEF-02), tests and docs.
- **Setup:** BUG-01 (redirect 301 instead of 302) was planted by `scripts/seed_bug01.py` in a labelled commit, `f2d0c8f`. Three S1 test assertions were loosened to hide it, as a real test gap would ([prompts/05](../prompts/05-seed-bug01.md)).
- **What it proves:** Impact analysis on existing code; finding a bug cause from the code (spec-writer found the 301); a safe change with a regression test (`test_BUG01_redirect_is_302_and_counts_clicks`); re-planning on a human "no".
- **Human decisions:** 6 spec questions answered (422 for both bad and reserved alias; case-sensitive alias; field `alias`; count all create requests, direct IP only; rename to `DATABASE_PATH`; alias equal to a random code is 409). Approval 1: first "no" (renumber ACs 1 to 22), then "yes". Approval 2: first "no" (remove T6, add the BUG-01 regression test, state the per-test fresh rate limiter), then "yes". Approval 3 "yes".
- **Result:** 45 passed, coverage 98.81%, 0 fix rounds, 0 rollbacks. 30.3 minutes. Committed 2026-10-07 (`8375fdb`). The one failing verify run was the README check, expected until the DOCS step.
- **Links:** [request](../specs/002-alias-ratelimit-fix/request.md), [spec](../specs/002-alias-ratelimit-fix/spec.md), [plan](../specs/002-alias-ratelimit-fix/plan.md), [tasks](../specs/002-alias-ratelimit-fix/tasks.md), [summary](../specs/002-alias-ratelimit-fix/summary.md); [prompts/05](../prompts/05-seed-bug01.md), [prompts/06](../prompts/06-s2-alias-ratelimit-fix.md).

## S3: Viral traffic

- **Request type:** Ambiguous. The whole request is "Make it handle viral traffic."
- **What it proves:** The agent does not invent a target. It asks questions, records assumptions, and the workflow stops at the approved spec.
- **Human decisions:** The business has not decided questions 1 to 5, so each got a recommended default recorded as an assumption (A1-A5) and stayed open. Three firm decisions: stay inside the brief limits (no queue, cache or new infrastructure); keep the create rate limit and add none on redirects; build nothing. Approval 1: "yes, stop here". Approvals 2 and 3 not reached.
- **Result:** The spec has 4 non-regression acceptance criteria and no performance criteria. 5 open questions remain for the business. No plan, code or tests; no tests run. 5.0 minutes. The spec was committed 2026-10-07 (`75e39bf`). The sizing in [design.md](design.md) section 2 uses this spec's open questions as the list of inputs to confirm.
- **Links:** [request](../specs/003-viral-traffic/request.md), [spec](../specs/003-viral-traffic/spec.md), [summary](../specs/003-viral-traffic/summary.md); [prompts/07](../prompts/07-s3-viral-traffic.md).

## S4: Data model, analytics, seed data

- **Request type:** Brownfield on S2: schema refactor (rename two tables with no data loss), 3 new tables, 2 analytics endpoints, a deterministic re-runnable seed script, reference SQL.
- **Setup:** The coder agent's scope was widened by one folder (`db_scripts/`) with the human's approval before the run ([prompts/09](../prompts/09-s4-data-model-analytics.md) part A).
- **What it proves:** A schema migration on an existing database; a human catching a design risk at the plan (a consistency risk between click, visitor and daily stat); privacy by design (hashed IPs); a scope change to an agent made deliberately and recorded.
- **Human decisions:** Answers: paths `/api/analytics/...`; invalid N is 422; summary takes the same N; totals limited to the last N days; no backfill of old rows; seed exactly 300 clicks and 40 visitors. Approval 1 "yes". Approval 2 first round "no": put the click event, visitor update and daily stat in ONE transaction with a test that a mid-failure saves none; remove T7 (README belongs to the DOCS step). Second round "yes". Approval 3 "yes".
- **Result:** 81 passed, coverage 98.53%. Seed: 30 links, 40 visitors, 300 clicks; a re-run adds nothing. 35.3 minutes. Committed 2026-10-08 (`fe7c392`). The stop hook fired once while the coder was still writing (6 seed tests failed because `db_scripts/schema.sql` did not exist yet); it was not a code fault and passed when the coder finished. That event shows as 1 retry in the metrics. The re-plan was a menu choice, so `metrics.py` counts it as a menu decision, not a "no" reply (V12).
- **Links:** [request](../specs/004-data-model-analytics/request.md), [spec](../specs/004-data-model-analytics/spec.md), [plan](../specs/004-data-model-analytics/plan.md), [tasks](../specs/004-data-model-analytics/tasks.md), [summary](../specs/004-data-model-analytics/summary.md); [prompts/09](../prompts/09-s4-data-model-analytics.md).

## Hook drill 1: gate retry and rollback

- **Request type:** A deliberate failure: a test containing `assert False`, no `/sdlc`.
- **What it proves:** `verify_gate` blocks "done" while tests fail, allows 2 retries, then rolls back `src/` and `tests/` with `git stash` (brief section 9: test each hook by hand).
- **Human decisions:** The prompt told the agent not to fix anything. The human dropped the stash afterwards because it held only the fake test.
- **Result:** Stop 1 blocked (attempt 1 of 2), stop 2 blocked (attempt 2 of 2), stop 3 rolled back and the file was removed. Audit log: `verify_fail`, `verify_fail`, `rollback`. 0.6 minutes. Tests and coverage: not applicable.
- **Links:** [prompts/03](../prompts/03-hook-test.md); `logs/audit.jsonl`.

## Hook drill 2: recovery (fail, fix, pass)

- **Request type:** A deliberate failure that the agent is told to fix after the first block.
- **What it proves:** A real recovery path (deviation V3) and an MTTR measurement.
- **Human decisions:** The same session also fixed the SKILL.md order (V2) and the `policy_guard` false positive on `os.environ` (V4). The guard blocked the agent from writing its own file by design; the human copied the file, the agent edited the copy, the human copied it back ([prompts/08](../prompts/08-deviation-fixes.md) part A). Hand tests: `cat .env`, `Get-Content .env` and `cat ./.env.local` are blocked; `cat .env.example` and `echo os.environ` are allowed.
- **Result:** `verify_fail` ("attempt 1", 1 failed / 45 passed), then `verify_pass` after the fix, 7.8 seconds apart. That is the single MTTR pair. 14.3 minutes for the session. Committed 2026-10-08 (`6b85dd2`).
- **Links:** [prompts/08](../prompts/08-deviation-fixes.md); [metrics.md](metrics.md).

## Overall (from metrics.md)

- 6 runs: 4 scored scenarios and 2 hook drills. Success rate 100% (committed or stopped at spec; drills excluded).
- 4 retries (2 and 1 in the drills, 1 in S4), 1 rollback (drill 1), MTTR 7.8 s.
- Replies counted by the log: S1 7, S2 13 (2 "no"), S3 4, S4 6 menu decisions.
