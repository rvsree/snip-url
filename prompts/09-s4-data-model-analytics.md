# 09 - Scenario S4: data model, analytics, seed data (brownfield)

**Date:** 2026-10-08
**Purpose:** Better data model (5 tables, two-word names), analytics endpoints, re-runnable seed data for reviewers.
**Input:** `specs/004-data-model-analytics/request.md`
**Where:** Claude Code in the VS Code terminal (`claude`), new session.

## Part A: allow the coder to write the seed script

The coder agent may only write in src/snip_url/. The seed script lives in db_scripts/, so its scope is widened by one folder, with my approval, before the run.

```
Small config change, do not run /sdlc. In .claude/agents/coder.md, allow the coder to write in db_scripts/ as well as src/snip_url/. Change nothing else. Show me the changed lines.
```

## Part B: run the scenario

```
/sdlc specs/004-data-model-analytics
```

## What I check at each approval

| Approval | Check |
|---|---|
| 1 - Spec | All 12 points covered; IP only as a salted hash; renaming keeps existing data |
| 2 - Plan | Impact analysis lists every file that uses the old table names; seed script owned by coder; daily_link_stats updated on redirect; tests for rename-on-startup and re-run of the seed |
| 3 - Merge | All tests pass (45+); coverage at least 80%; summary.md included in the commit |

## Open questions and my answers

From `specs/004-data-model-analytics/summary.md`: analytics paths are `/api/analytics/...`; invalid N is rejected with 422; the summary takes the same N; totals are limited to the last N days; migrated old rows keep empty visitor data and `is_custom_alias` false; the seed has exactly 300 clicks and 40 visitors.

## My replies at the approvals

- Approval 1 (spec): "yes"
- Approval 2 (plan), first round: "no: 1) Fix risk 2: record the click event, the visitor update and the daily_link_stats update in ONE database transaction, so they can never get out of step. Add a test that proves a failure in the middle saves none of them. 2) Remove T7: README is updated in the DOCS step; the coder writes only in src/ and db_scripts/. Then show the plan again."
- Approval 2 (plan), second round: "yes"
- Approval 3 (merge): "yes"

## Result

81 tests passed, coverage 98.53%. One re-plan at Approval 2; the stop hook fired once while the coder was still writing (not a code fault); 0 fix rounds, 0 rollbacks. Merge commit `fe7c392`; audit log `9b318f1`. Seed counts: 30 links, 40 visitors, 300 clicks; counts for `api_clients` and `daily_link_stats` not recorded.
