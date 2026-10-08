# 04 - Scenario S1: core URL shortener (greenfield, well-defined)

**Date:** [INSERT run date]
**Purpose:** Build the URL shortener from zero through the full /sdlc workflow with 3 human approvals.
**Input:** `specs/001-core-api/request.md`
**Where:** Claude Code in the VS Code terminal (`claude`), new session.

## Prompt

```
/sdlc specs/001-core-api
```

## What I check at each approval

| Approval | Check |
|---|---|
| 1 - Spec | Every point in request.md has at least one acceptance criterion; redirect is 302; nothing from "Not needed now" crept in |
| 2 - Plan | Contract lists every file and function; layers follow the constitution; each AC has a test name |
| 3 - Merge | All tests pass; coverage at least 80%; changed files are only in src/, tests/, specs/001-core-api/, README.md |

## My replies

- Approval 1: [INSERT]
- Approval 2: [INSERT]
- Approval 3: [INSERT]

## Result

[INSERT: tests passed, coverage %, retries, commit ID]
