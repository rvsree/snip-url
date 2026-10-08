# 05 - Seed BUG-01 on purpose (before S2)

**Date:** 2026-10-07
**Purpose:** Plant a known bug so scenario S2 can show a real bug fix on existing code. Done by the human, outside /sdlc, in a clearly labelled commit.
**Where:** Claude Code in the VS Code terminal (`claude`), new session.

**The bug:** the redirect returns 301 (permanent) instead of 302 (temporary). Browsers cache a 301, so repeat visits skip the server and are not counted. The S1 test is loosened to accept any redirect, which is how the bug "slipped through" (a test gap S2 must close).

## Prompt

```
Task: write scripts/seed_bug01.py only. Do not change src/ or tests/ yourself, and do not run the script. I will run it.

The script plants BUG-01 on purpose for a demo:
1. In src/snip_url/, change the redirect status code from 302 to 301 (one place only).
2. In tests/, find the test that checks the redirect status is 302, and loosen only that assertion so it accepts 301 or 302.
3. Print each file and line it changed. If it cannot find exactly one match for a change, print an error and change nothing.

Rules: Python standard library only, beginner-readable per specs/constitution.md, under 60 lines. First show me which file and line each change will touch, then write the script. Do not git add or commit.
```

## Steps after the script is written (human, in the terminal, not in claude)

```
uv run python scripts/seed_bug01.py
```
```
uv run pytest -q
```
Expected: all tests still pass (the loosened test hides the bug).
```
git add scripts/seed_bug01.py <the 2 changed files the script printed>
```
```
git commit -m "BUG-01 seeded on purpose for scenario S2 (redirect 301 instead of 302)"
```

## Follow-up during the session

Claude Code found that 3 tests (not 1) asserted 302. Reply:

```
Yes, loosen those two assertions too, the same way (accept 301 or 302). Keep the exactly-one-match check for each change. Show me the final list of every file and line the script will change.
```

## Result

- Script made 4 changes: `src/snip_url/api/routes.py` (302 -> 301), `tests/test_redirect.py` (AC5, AC7 assertions), `tests/test_persistence.py` (AC11 assertion).
- `uv run pytest -q`: 17 passed (bug hidden by the loosened tests, as intended).
- Commit [INSERT commit ID] "BUG-01 seeded on purpose for scenario S2 (redirect 301 instead of 302; 3 test assertions loosened)".
