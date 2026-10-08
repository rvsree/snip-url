# snip-url: Project Brief

Author: Sree | Date: 2026-10-07 | Status: Draft for review

## 1. Problem (FDE framing)

Schwab wants to see if an engineer can make AI agents do real software work **under control**: a requirement goes in, and a reviewed, tested result comes out. Agents do the multi-step work. A human approves the high-impact steps and owns the final quality.

The URL shortener is the example product. **What is graded is the controlled agentic workflow around it.**

**Stakeholders.** Hiring manager (judges design and judgment), interview panel (asks "why" on each decision), recruiter (on-time submission).

**Constraints.** 2-3 days, one person, own API budget, Windows laptop, must be explainable live in the interview.

## 2. Approach

**Spec-Driven Development (SDD) run by Claude Code.** No custom orchestrator program.

- **Subagents** do the work: `spec-writer`, `planner`, `coder`, `tester`.
- **One skill, `/sdlc`**, runs the steps in order and stops for human approval.
- **Three hooks** (small Python scripts that Claude Code runs automatically) enforce the rules in code: block unsafe writes, log every action, refuse "done" while tests fail.
- **Specs** live in `specs/<feature>/`: request, spec, plan, tasks.

## 2a. Architecture

**System (how work flows)**

```
Human (Sree, in VS Code)
  |  /sdlc specs/<feature>          approvals: spec, plan, merge
  v
Claude Code main session  = orchestrator (follows .claude/skills/sdlc/SKILL.md)
  |-- spec-writer --> spec.md
  |-- planner     --> plan.md + tasks.md
  |-- coder  (src/)   } run in parallel, then join
  |-- tester (tests/) }
  |
  Hooks around every tool call (code, not AI):
     before Write/Edit : policy_guard.py  -> block unsafe write
     after any tool    : audit_log.py     -> logs/audit.jsonl
     at "done"         : verify_gate.py   -> pytest + coverage; retry x2; rollback
  |
  v
Git (human commits and pushes)    scripts/metrics.py reads audit log + git
```

**App (what the agents build)**

```
HTTP -> api/routes.py (no logic) -> services/link_service.py (rules, no SQL)
     -> repo/link_repo.py (SQL only) -> SQLite (links, click_events)
```

| Aspect | Decision |
|---|---|
| AI vs code boundary | AI (non-deterministic): writing specs, plans, code, tests. Code (deterministic): hooks, tests, coverage, rollback, metrics. |
| State | Files: `specs/<feature>/` holds each stage's output; `logs/audit.jsonl` holds every action; git holds history. No database for the workflow. |
| Data access (app) | Only the repo layer talks to SQLite. |
| Auth | None for the app (out of scope). Agent permissions are limited by settings.json and hooks. |

## 2b. Key trade-offs

| Decision | Chosen | Alternative | Why | What we give up |
|---|---|---|---|---|
| Orchestrator | Claude Code skill + subagents + hooks | Custom Python pipeline or LangGraph | Less code, uses the tool Schwab asked about, easy to explain | Step order is followed by the AI, not forced by code |
| Gates | Hooks (code) | Ask the AI to check itself | Gates cannot be skipped by the AI | Hooks are Claude Code specific |
| Parallel build | coder and tester at the same time | One after the other | Shows parallel paths with a sync point | Needs a strict contract in plan.md |
| Rollback | git stash of src/ and tests/ | Git branches per run | Simple, one command | Only rolls back code, not spec files |
| Database | SQLite | Postgres | No setup for reviewer | Not for production scale (documented) |
| Short code | Random 7-char base62 | Counter or hash | No guessable links, simple | Small collision chance (checked on insert) |
| Redirect | 302 | 301 | Every click reaches the server and is counted | Slightly more server load |
| Runs | Live only | Recorded replay | Honest, simple | Results vary run to run; cost per run |

## 3. Success criteria (measurable)

1. Three scenarios (S1 greenfield, S2 brownfield, S3 ambiguous) run through `/sdlc`, each with spec, plan, tasks and summary in `specs/`.
2. The app passes its tests with at least 80% coverage.
3. At least one run shows a test failure, a retry and a recovery in `logs/audit.jsonl`.
4. Every agent action is in `logs/audit.jsonl`; `scripts/metrics.py` prints the metrics in section 7.
5. A reviewer can clone the repo and run the app and tests in under 10 minutes using the README.

## 4. How a feature runs (`/sdlc specs/<feature>`)

```
SPEC    spec-writer writes spec.md; asks questions if the request is vague
        -> APPROVAL 1: human approves the spec (or rejects with a comment)
PLAN    planner writes plan.md (impact analysis + exact file/function contract) and tasks.md
        -> APPROVAL 2: human approves the plan (reject = re-plan)
BUILD   coder (src/) and tester (tests/) run at the same time, then join
VERIFY  verify_gate hook runs pytest + coverage; fail = retry (max 2); still failing = rollback
DOCS    README updated for the feature
MERGE   -> APPROVAL 3: human approves; commit (human pushes)
SUMMARY summary.md: what was built, results, approvals, retries
```

## 5. Scenarios

| ID | Type | Request | What it proves |
|---|---|---|---|
| S1 | Greenfield, well-defined | Build the URL shortener: create a short link, redirect (302), click stats; SQLite; URL validation | Decomposition, build from zero, tests, gates |
| S2 | Brownfield (enhancement, bug fix, test and doc improvement) | Add custom alias and rate limiting; fix BUG-01 (redirect returns 301 instead of 302, so clicks are lost); add missing tests; update README | Impact analysis on existing code, safe change, regression test |
| S3 | Ambiguous | "Make it handle viral traffic." | Agent asks questions, records assumptions, stops at the approved spec |

BUG-01 is seeded on purpose after S1 by `scripts/seed_bug01.py`, in a clearly labelled commit.

## 6. Project structure

```
snip-url/
  README.md  CLAUDE.md  pyproject.toml  .env.example  .gitignore
  .github/workflows/ci.yml                 tests on every push
  .claude/  settings.json                  permissions + hooks
            agents/   spec-writer.md planner.md coder.md tester.md
            skills/sdlc/SKILL.md           the /sdlc flow
            hooks/    policy_guard.py audit_log.py verify_gate.py
  specs/    constitution.md                coding standards and rules
            001-core-api/  002-alias-ratelimit-fix/  003-viral-traffic/
                (request.md spec.md plan.md tasks.md summary.md; 001 also data-model.md, contracts/api.md)
  src/snip_url/  __init__.py main.py api/ services/ repo/ models/ common/   (written by agents)
  tests/                                                        (written by agents)
  data/     snip_url.db (local SQLite, git-ignored)
  scripts/  metrics.py  seed_bug01.py
  logs/audit.jsonl
  docs/     PROJECT_BRIEF.md architecture.md design.md decisions.md requirements-map.md scenarios.md
```

## 7. Schwab requirements: where each is met

| Schwab asks | Where |
|---|---|
| Requirement understanding, ambiguity | `spec-writer`, open questions in spec.md (S3) |
| Task decomposition with dependencies | `planner` -> tasks.md |
| Codebase reasoning (brownfield) | plan.md impact analysis (S2) |
| Orchestration: stages, entry/exit gates | `/sdlc` skill (order) + hooks (code-enforced checks) |
| Sequential and parallel paths with sync | BUILD: coder and tester in parallel, then VERIFY |
| Context and decision lineage | spec -> plan -> tasks -> summary, plus git history |
| Human approval for high-impact actions | 3 approvals in `/sdlc`; commit by human |
| Bounded retry, rollback, safe-stop | `verify_gate.py` (2 retries, then rollback via git stash) |
| Policy guardrails | `settings.json` deny rules + `policy_guard.py` |
| Audit and traceability | `audit_log.py` -> logs/audit.jsonl |
| Metrics: success rate, retry and rollback count, MTTR, latency | `scripts/metrics.py` (from audit log and git) |
| Re-plan when upstream changes | reject at approval 2 or 3 -> planner runs again |
| Output: code, API, tests, docs | `src/`, contracts/api.md, `tests/`, README |
| Final engineering summary | summary.md per feature + README |
| Deliverables: prototype, architecture, 3 scenarios, setup, testing, limits | app + `docs/` + README |

## 8. Assumptions

- Python 3.12, FastAPI, SQLite, pytest. Windows laptop with Claude Code in VS Code.
- Live agent runs only (no replay). Cost per scenario is taken from the Claude Code usage view and recorded in summary.md.
- One human approver (Sree).

## 9. Risks and mitigations (FDE: decided before building)

| Risk | Mitigation |
|---|---|
| Over-engineering again; time runs out | Build only this brief. Ideas go to README "Limitations", not code. |
| Step order is followed by the AI from the skill, not forced by code | Hooks enforce the important checks in code (tests, writes, logging). Stated openly as a trade-off. |
| Coder and tester build mismatched code (parallel, no shared view) | planner writes an exact file/function contract in plan.md; both must follow it. |
| Hooks behave differently on Windows | Test each hook once by hand before S1. |
| Secrets leak to an agent or to git | settings.json denies .env; policy_guard blocks secret-like text; .env is git-ignored. |
| Agent output fails tests repeatedly | 2 retries, then rollback; human decides. |
| Live runs give different results each time | Commit each scenario's outputs (specs, summary, audit log) as evidence; do not re-run for the demo. |
| Reviewer sees "no orchestrator code" and marks it down | requirements-map.md shows where each orchestration item is met; decisions.md explains the choice. |
| Claude Code behaves differently than the docs (new version) | Pin and record the Claude Code version in the README. |
| Cost overrun | Use sonnet for subagents; check the usage view after each scenario. |

**Stop rule:** if a step takes more than 2x its time in section 11, stop, write the gap in README "Limitations" and move on.

## 10. Out of scope (listed in README as future work)

Login and JWT, link expiry, list or delete links, background click queue, Redis cache, Postgres, Docker, cloud deployment, load testing.

## 11. Build order

| Step | Work | Time |
|---|---|---|
| 1 | Repo, folders, pyproject, CI, CLAUDE.md, constitution, settings | 30 min |
| 2 | 4 subagents, /sdlc skill, 3 hooks; test each hook by hand | 60 min |
| 3 | S1 through /sdlc | 45 min |
| 4 | Seed BUG-01; S2 through /sdlc | 40 min |
| 5 | S3 through /sdlc (stop at spec) | 15 min |
| 6 | metrics.py; docs (architecture, design, decisions, requirements map, scenarios); README | 75 min |
| 7 | Handover check: fresh clone, follow README, run tests, run metrics; then submit | 20 min |

## 12. Handover (what the reviewer gets)

README gives a 5-minute path: setup, run tests, try the API, read one scenario (`specs/001-core-api/`), see the audit log and metrics. `docs/decisions.md` and section 2b answer the "why" questions for the interview.
