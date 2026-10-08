# 02 - Subagents, /sdlc skill, hooks (build step 2)

**Date:** 2026-10-07
**Purpose:** Build the agentic workflow: 4 subagents, the /sdlc skill, 3 hooks, hook registration.

## Prompt

```
Read docs/project_brief.md (sections 2, 2a, 4, 9) and specs/constitution.md.

Task: Build step 2 only (section 11, step 2): 4 subagents, the /sdlc skill, 3 hooks, and hook registration. Do not build app code, tests, request files or docs.

1. .claude/agents/ (model: sonnet for all; tools: Read, Glob, Grep, Write, Edit)
   - spec-writer.md: reads <feature>/request.md and existing code; writes only <feature>/spec.md with sections: Summary, In scope, Acceptance criteria (AC1, AC2... each testable, Given/When/Then), Out of scope, Assumptions, Open questions (numbered; "None" if clear). Never invent answers to open questions.
   - planner.md: reads spec.md and existing code; writes <feature>/plan.md with sections: Impact analysis (existing files changed, new files, risk), Contract (every file, every function with full signature and return type, every endpoint with method, path, status codes, JSON body), Data model, Test plan (each AC -> test name), Risks. Writes <feature>/tasks.md: T1, T2... each with owner (coder or tester), files, depends on; mark tasks that can run in parallel with [P].
   - coder.md: implements coder tasks in src/snip_url/ only, follows the plan.md contract exactly, follows the constitution, no extra features or libraries. Never writes tests.
   - tester.md: writes pytest tests in tests/ only, at least one per AC, named test_AC<n>_<what>, imports only via the plan.md contract, FastAPI TestClient, temporary SQLite via tmp_path; for a bug fix adds a regression test. Never changes src/.

2. .claude/skills/sdlc/SKILL.md (frontmatter: name sdlc, description, disable-model-invocation: true)
   Usage: /sdlc specs/<feature>. The main session is the orchestrator: it delegates, never writes specs, plans, code or tests itself. Steps exactly as brief section 4:
   SPEC (spec-writer; if open questions, ask me and update) -> APPROVAL 1 (show 5-line summary, ask "Approve spec? yes / no + comment"; no = revise and ask again; if I say "stop here", stop)
   -> PLAN (planner) -> APPROVAL 2 (show impact list and tasks; no = re-plan with my comment)
   -> BUILD (coder and tester in parallel, in ONE message with two subagent calls; wait for both)
   -> VERIFY (run: uv run pytest --cov=snip_url --cov-fail-under=80; on failure send output to coder, or tester if a test is wrong, and re-run; the verify_gate hook limits retries to 2 and rolls back after that; if rolled back, tell me and stop)
   -> DOCS (update README: endpoints and how to try them, short)
   -> APPROVAL 3 (show test result, coverage, changed files; yes = git add each file by name, git commit -m "<feature>: <summary>", never push; no = back to PLAN with my comment)
   -> SUMMARY (write <feature>/summary.md: what was built, tests and coverage, approvals with my exact replies, retries, rollbacks, open items).

3. .claude/hooks/ (Python 3.12, standard library only, beginner-readable per the constitution, each under 120 lines)
   - policy_guard.py (PreToolUse, matcher Write|Edit|MultiEdit|NotebookEdit): read hook JSON from stdin; block with exit code 2 and a reason on stderr if: the path is outside the project; the path is .env or starts with .env; the path is under .claude/settings.json, .claude/hooks/, .github/, or is specs/constitution.md; the new text contains sk-ant-, AKIA, or BEGIN PRIVATE KEY. Otherwise exit 0.
   - audit_log.py (PostToolUse with no matcher, UserPromptSubmit, Stop): append one JSON line to logs/audit.jsonl: ts (UTC ISO), session_id, event, tool_name, target (file_path, or command first 200 chars, or subagent type, or prompt first 200 chars). Never log file contents. Never block: catch all errors, always exit 0.
   - verify_gate.py (Stop, timeout 300): if git status --porcelain shows no changes in src/ or tests/, exit 0. Otherwise run uv run pytest --cov=snip_url --cov-fail-under=80 -q. Pass: reset counter in logs/verify_state.json, append verify_pass to audit.jsonl, exit 0. Fail: add 1 to counter; if counter <= 2, print JSON {"decision": "block", "reason": "Tests failed (attempt N of 2): <last 30 lines>"} and append verify_fail; if counter > 2, run git stash push --include-untracked -m "snip-url rollback <ts>" -- src tests, append rollback, reset counter, print JSON {"systemMessage": "Rolled back after 2 failed retries. Recover with git stash list / git stash pop."} and exit 0.

4. .claude/settings.json: keep the existing permissions; add hook registration for the 3 hooks using "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/<name>.py\"". Write this file LAST, after the hooks exist.

5. .gitignore: stop ignoring logs/audit.jsonl (keep other logs ignored) and ignore logs/verify_state.json.

Rules:
- First show me your plan: every file, one line each, plus anything in my spec that is wrong for the current Claude Code version (hook input fields, settings format). Then STOP and wait for my "yes".
- Never read or print .env. Do not git add, commit or push.
- Build only what is listed above.
```

## Reply to the plan

The plan found version differences (subagent tool is `Agent`; hook input fields differ per tool; new permission syntax) and asked for 7 decisions.

```
Approved with these changes:
1. Accept your defaults 1 to 7 as written.
2. Use the new permission form, and list each rule both bare and with " *": Bash(git push), Bash(git push *), Bash(git add -A), Bash(git add -A *), and keep Bash(git add .) exact.
3. Close the Bash gap: register policy_guard also for PreToolUse matcher Bash. Block a command if it contains ".env" (but allow ".env.example"), or if it contains "git push". Exit 2 with a reason, same as the file rules.
Update the plan with these and show it again, then wait for my yes.
```

Defaults accepted: no-tests (exit 5) counts as pass; `.env.example` writes blocked; skill allows 2 fix rounds, then the hook decides; orchestrator writes README and summary.md; `.gitignore` tracks audit.jsonl.

## Result

- 4 agents, SKILL.md, 3 hooks, settings.json and .gitignore written. policy_guard passed 16 sample cases.
- Known limitation: the Bash guard also blocks commands that only mention `os.environ` (contains ".env"). Safe side; listed in README Limitations.
- `/sdlc` shows in the terminal `claude` slash list (project skill) after trusting the folder; the VS Code chat panel does not list it.
- Commit [INSERT commit ID] "Step 2: subagents, /sdlc skill, hooks (gate retry and rollback tested)".
