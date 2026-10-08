---
name: sdlc
description: Run a feature through spec, plan, build, verify, docs and merge with 3 human approvals. Usage /sdlc specs/<feature>
disable-model-invocation: true
---

# /sdlc

Usage: `/sdlc specs/<feature>` (for example `/sdlc specs/001-core-api`).
The feature folder is `$ARGUMENTS`. It must contain `request.md`. If it does not, tell the human and stop.

You are the orchestrator. You delegate to subagents. You NEVER write specs, plans, code or tests yourself.
You may write only `README.md` (DOCS step) and `<feature>/summary.md` (SUMMARY step).
Do the steps in order. Never skip an approval. Record the human's exact replies for the summary.

## 1. SPEC
Call the `spec-writer` subagent with the feature folder. It writes `<feature>/spec.md`.
If spec.md has open questions (not "None"), ask the human each question, send the answers back to `spec-writer`, and let it update spec.md. Repeat until no open questions remain.

## APPROVAL 1
Show a 5-line summary of the spec (scope, number of ACs, key assumptions, out of scope, open questions).
Ask: "Approve spec? yes / no + comment".
- "no": send the comment to `spec-writer`, revise, show the summary, and ask again.
- "stop here": stop. Write the summary (SUMMARY step) and end.
- "yes": continue.

## 2. PLAN
Call the `planner` subagent. It writes `<feature>/plan.md` and `<feature>/tasks.md`.

## APPROVAL 2
Show the impact list (changed files, new files, risks) and the tasks (id, owner, [P]).
Ask: "Approve plan? yes / no + comment".
- "no": call `planner` again with the comment (re-plan), show again, ask again.
- "yes": continue.

## 3. BUILD
In ONE message, make two subagent calls so they run in parallel: `coder` and `tester`.
Give each the feature folder. Wait for both to finish.

## 4. VERIFY
Run: `uv run pytest --cov=snip_url --cov-fail-under=80`
- Pass: continue.
- Fail: send the output to `coder`. If a test is wrong against the spec, send it to `tester` instead. Re-run.
- Allow at most 2 fix rounds. If it still fails, end your turn. The verify_gate hook limits retries to 2 and rolls back `src/` and `tests/` after that.
- If a rollback happened (a message says "Rolled back"), tell the human what failed and stop.

## 5. DOCS
Update `README.md`: the endpoints and how to try them. Keep it short.

## APPROVAL 3
Show the test result, the coverage, and the list of changed files (`git status --short`).
Ask: "Approve merge? yes / no + comment".
- "yes": first write `<feature>/summary.md` (SUMMARY step), then run `git add` once for each file BY NAME (including `<feature>/summary.md`), then `git commit -m "<feature>: <summary>"`. After the commit, only report the commit ID. Never push. Never use `git add -A` or `git add .`.
- "no": go back to step 2 (PLAN) with the comment.

## 6. SUMMARY
Do this BEFORE the merge commit at APPROVAL 3 (and at "stop here"). Write `<feature>/summary.md` with: what was built, tests and coverage, approvals with the human's exact replies, retries, rollbacks, open items.
