# 10 - Metrics script (build step 5)

**Date:** 2026-10-08
**Purpose:** Measure the workflow's reliability from logs/audit.jsonl and git: runs, success rate, retries, rollbacks, MTTR, end-to-end time, human decisions, agent calls.
**Where:** Claude Code in the VS Code terminal (`claude`), new session. Not through /sdlc (it is a review tool, not an app feature).

## Prompt

```
Task: write scripts/metrics.py only. Do not run /sdlc. Do not change src/ or tests/.

It reads logs/audit.jsonl and prints a metrics table for Schwab's reliability requirements:
1. Split events into runs: a run starts at a UserPromptSubmit whose target starts with "/sdlc " and ends at the next such prompt or the last event of that session_id. Sessions without /sdlc that contain verify_fail, verify_pass or rollback are runs named "hook test".
2. Per run print: scenario folder, start time, end-to-end minutes, outcome (committed if a Bash target contains "git commit"; stopped at spec if a prompt contains "stop here"; otherwise incomplete), human replies count, "no" replies (re-plans), verify_fail count (retries), rollback count, agent calls per subagent type.
3. Totals: runs, success rate %, total retries, total rollbacks, MTTR in seconds (average time from each verify_fail to the next verify_pass in the same session; "n/a" if none).
4. Also write the same report as Markdown to docs/metrics.md.
Rules: Python standard library only, beginner-readable per specs/constitution.md, no comprehensions or lambdas, under 200 lines. First show me your plan (functions, one line each) and wait for my yes. Do not git add or commit.
```

## Reply to the plan

```
yes, with 3 changes: 1) "no" replies also match a reply starting with "no:" (my replies were typed "no: ..."). 2) A run is successful if it is committed OR stopped at spec. 3) Show "hook test" runs in the table, but leave them out of the success rate; still include them in retries, rollbacks and MTTR.
```

## First output was wrong (checked, not trusted)

Success rate 25%, S3 586 minutes, recovery test missing, S4 re-plan not counted. Causes: the audit hook cuts commands at 200 characters (the "git commit" part was lost); runs ended at the session's last event (session left open overnight); events before a session's first /sdlc were dropped; approvals chosen in the menu are not typed prompts.

```
Fix 4 issues: 1) Outcome "committed": use git history (git log --format=%s). A run is committed if a commit subject starts with its scenario folder followed by ":" (e.g. "specs/001-core-api:"). 2) A run ends at the last event before a gap of more than 30 minutes, or at the next /sdlc prompt. 3) Events in a session before its first /sdlc prompt that include verify_fail, verify_pass or rollback form a "hook test" run. 4) Count PostToolUse events with tool_name AskUserQuestion as "menu decisions" in a separate column. Also print each MTTR pair (fail time, pass time, seconds) under the totals. You may go up to 250 lines. Then run it and show me the output.
```

Second output: S1 cut to 2.2 minutes (no main-session events during the long parallel build looked like idle time).

```
One more fix: for a committed run, the end time is its commit time from git (use git log --format="%s|%cI" and the same subject rule). The 30-minute gap rule applies only to runs that are not committed. Then run it and show me the output.
```

## Result

| Run | Minutes | Outcome | Re-plans ("no") | Retries | Rollbacks |
|---|---|---|---|---|---|
| hook test (prompt 03) | 0.6 | drill | 0 | 2 | 1 |
| S1 specs/001-core-api | 45.7 | committed | 0 | 0 | 0 |
| S2 specs/002-alias-ratelimit-fix | 30.3 | committed | 2 | 0 | 0 |
| S3 specs/003-viral-traffic | 5.0 | stopped at spec | 0 | 0 | 0 |
| hook test (prompt 08, recovery) | 14.3 | drill | 0 | 1 | 0 |
| S4 specs/004-data-model-analytics | 35.3 | committed | (menu) | 1 | 0 |

Success rate 100% (hook tests excluded); retries 4; rollbacks 1; MTTR 7.8 seconds (one fail -> pass pair, recovery test).

Known limit (V12): approvals chosen from Claude Code's menu are logged as "a decision was made", not the choice itself; S4's "no + comment" is therefore not counted as a re-plan by the script. The exact replies are in specs/004-.../summary.md and prompts/09.

Commit: `c82ed21`
