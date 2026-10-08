# 07 - Scenario S3: viral traffic (ambiguous requirement)

**Date:** [INSERT run date]
**Purpose:** Show how the workflow handles a vague requirement: the agent asks questions and records assumptions, and the run stops at the approved spec. No code is built.
**Input:** `specs/003-viral-traffic/request.md` (one line: "Make it handle viral traffic.")
**Where:** Claude Code in the VS Code terminal (`claude`), new session.

## Prompt

```
/sdlc specs/003-viral-traffic
```

## How I answer the open questions

The business has not decided yet. For each question, I choose the agent's recommended option if it is reasonable, and otherwise reply:

```
Not decided by the business yet. Record your recommended default as an assumption and keep this as an open question for the business owner.
```

## Reply at approval 1

```
yes, stop here
```

(The skill stops after the approved spec. Building waits for the business answers.)

## Result

[INSERT: number of questions, assumptions recorded, open questions left]
