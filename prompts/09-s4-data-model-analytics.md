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

[INSERT]

## My replies at the approvals

[INSERT]

## Result

[INSERT: tests, coverage, retries, commit ID; seed counts per table]
