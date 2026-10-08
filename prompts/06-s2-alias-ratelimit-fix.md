# 06 - Scenario S2: alias, rate limit, BUG-01, DEF-02 (brownfield)

**Date:** 2026-10-07
**Purpose:** Change existing code safely: enhancement (custom alias, rate limiting), bug fix (BUG-01), refactor (DEF-02), test and doc improvement.
**Input:** `specs/002-alias-ratelimit-fix/request.md`
**Where:** Claude Code in the VS Code terminal (`claude`), new session.

## Prompt

```
/sdlc specs/002-alias-ratelimit-fix
```

## Open questions from spec-writer (6) and my answers

| Question | Answer |
|---|---|
| Status code for invalid or reserved alias | 422 for both (matches existing URL validation errors) |
| Alias case rules | Alias case-sensitive; reserved words matched ignoring case |
| Field name | `alias` |
| Rate limit counting and client IP | Count all create requests; direct client IP only; ignore X-Forwarded-For (it can be faked) |
| Database setting name | Rename to `DATABASE_PATH` only (default `data/snip_url.db`) |
| Alias equal to an existing random code | Treat as taken, 409 (overwrite would let someone hijack a link) |

## My replies at the approvals

Approval 1 (spec), first reply:
```
no: renumber the acceptance criteria in order, AC1 to AC22 with no gaps, keeping the same content. Then show the summary again.
```
Approval 1, second reply: `yes`

Approval 2 (plan), first reply:
```
no: 1) Remove T6. README is updated in the DOCS step; the coder writes only in src/. 2) Add a named regression test for BUG-01 that asserts the redirect is exactly 302 and that two visits to the same link give a click count of 2. 3) State in the plan that conftest.py gives every test a fresh rate limiter, so tests never affect each other. Then show the plan again.
```
Approval 2, second reply: `yes`

Before approval 3 (check):
```
Before I answer: list the test function names in tests/test_redirect.py and tell me which one is the BUG-01 regression test (exactly 302, and two visits give a click count of 2).
```
Answer: `test_BUG01_redirect_is_302_and_counts_clicks`.
Approval 3 (merge): `yes`

## Result

- 45 passed, 0 failed; coverage 98.81% (gate 80%); no fix rounds, no rollbacks.
- spec-writer found the BUG-01 cause from the code (routes.py returned 301); 3 loosened assertions restored to exactly 302.
- DEF-02 checked by hand after the merge: running the app creates `data/snip_url.db`, and no `snip_url.db` in the project root.
- Merge commit [INSERT commit ID]; audit log commit `2295b57`.
