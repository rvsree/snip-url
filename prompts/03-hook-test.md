# 03 - Hook test: gate retry and rollback

**Date:** 2026-10-07
**Purpose:** Prove the verify_gate hook blocks "done" while tests fail, allows 2 retries, then rolls back (brief section 9: test each hook by hand).
**Where:** Claude Code in the VS Code terminal (`claude`), new session.

## Prompt

```
Hook test only. Create tests/test_gate_check.py with one test: def test_gate_check(): assert False
Then end your turn. When the stop hook blocks you, do NOT fix anything and do NOT edit files; just end your turn again. Repeat until the hook stops blocking. Then show me: git stash list, and the last 6 lines of logs/audit.jsonl.
```

## Result

- Stop 1: blocked, "Tests failed (attempt 1 of 2)".
- Stop 2: blocked, "Tests failed (attempt 2 of 2)".
- Stop 3: "Rolled back after 2 failed retries"; `tests/test_gate_check.py` removed.
- `git stash list`: `stash@{0}: On main: snip-url rollback 2026-10-08T01:21:59...`
- `logs/audit.jsonl`: `verify_fail` (attempt 1), `verify_fail` (attempt 2), `rollback` (src tests).
- Stash dropped afterwards with `git stash drop` (it held only the fake test).
- Audit log from this test: [INSERT kept or deleted].
