# Schwab spec mapper

Author: Sree | Date: 2026-10-08 | Status: Checked against Schwab's assignment (`_private/schwab_assignment.pdf`, 7 sections) on 2026-10-08

For Schwab reviewers. It maps each section and requirement of the assignment to where snip-url meets it and the evidence to check. Names in the first column are Schwab's own requirement names. Nothing from the PDF is copied beyond those names and short paraphrases. Status values: **Met**, **Partly met**, **Not met** (required but not built), **Not in scope** (excluded by the brief, with the reason).

The sections follow the assignment: 1 Objective, 2 Scenario, 3 Scope, 4 Core Requirements (requirement 4, Workflow Orchestration, is split into its sub-items), 5 Deliverables, 6 Evaluation Criteria, 7 Expectation.

Evidence paths are relative to the repo root. Test commands are Windows PowerShell.

## 1. Objective

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Working prototype that transforms a requirement into a reviewable engineering outcome using an agentic execution model | `/sdlc specs/<feature>` takes a `request.md` and produces spec, plan, tasks, code, tests and summary, each reviewable in the feature folder | `.claude/skills/sdlc/SKILL.md`; `specs/001-core-api/` to `specs/004-data-model-analytics/` | Met |
| Demonstrate requirement understanding, task decomposition, multi-step execution, output generation/validation | Subagents `spec-writer`, `planner`, `coder`, `tester`; `verify_gate.py` validates with pytest and coverage | `.claude/agents/*.md`; `.claude/hooks/verify_gate.py` | Met |
| End-to-end SDLC automation with controlled autonomy | Steps run in order with 3 human approvals; hooks enforce tests, writes and logging | `.claude/skills/sdlc/SKILL.md`; `.claude/settings.json` | Partly met: stage order is followed by the AI, not enforced by code (V8); see section 4 |

## 2. Scenario

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Build a URL shortener service from scratch with core APIs, analytics and reliability features | FastAPI + SQLite: create, custom alias, 302 redirect, stats, per-link and summary analytics, rate limiting, hashed IPs | `src/snip_url/`; [design.md](design.md) section 3 | Met (reliability is basic: validation, one error format, rate limit, transactional tracking; no cache, queue or retry layer) |
| Complete and improve it over 2-3 days using AI assistance, demonstrating engineering judgment | Built with Claude Code in four scenarios; decisions, alternatives and trade-offs recorded | [decisions.md](decisions.md); [scenarios.md](scenarios.md); `prompts/` | Met |

## 3. Scope

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Greenfield scenarios (new systems/features) | S1 core API; S4 also adds new features (analytics endpoints, seed script) | `specs/001-core-api/`; `specs/004-data-model-analytics/` | Met |
| Brownfield scenarios (enhancements, refactors, bug fixes) | S2: custom alias and rate limit (enhancements), BUG-01 301 -> 302 (bug fix), DEF-02 database path on import (refactor). S4: table renames and new columns | `specs/002-alias-ratelimit-fix/`; `specs/004-data-model-analytics/` | Met |
| Test and documentation improvements | S2 added missing tests and README update; docs set written in `docs/` | `specs/002-alias-ratelimit-fix/summary.md`; `tests/`; `docs/` | Met (README: "How the /sdlc workflow works", "Documentation index") |
| Well-defined and ambiguous requirements | S1 well defined; S3 "Make it handle viral traffic" ambiguous: 5 open questions, 6 assumptions (A1-A6), 3 human decisions (D1-D3), stopped at the approved spec | `specs/003-viral-traffic/spec.md`; `specs/003-viral-traffic/summary.md` | Met |

## 4. Core Requirements

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| 1) Requirement Understanding | `spec-writer` turns `request.md` into `spec.md` with numbered ACs, assumptions and open questions; it asks the human when a request is vague | `specs/003-viral-traffic/spec.md`; `.claude/agents/spec-writer.md` | Met |
| 2) Task Decomposition | `planner` writes `tasks.md`: owner, files, depends on, `[P]` for parallel | `specs/002-alias-ratelimit-fix/tasks.md`; `specs/004-data-model-analytics/tasks.md` | Met |
| 3) Codebase Reasoning (Brownfield) | Plan has an impact analysis. S2 found BUG-01 from the code. S4 listed every file using the old table names | `specs/002-alias-ratelimit-fix/plan.md`; `specs/004-data-model-analytics/plan.md` | Met |
| 5) Engineering Output Generation | Code in `src/`, API contract and data model in each `plan.md`, unit and integration tests, docs. 81 tests, 98.5% coverage | `uv run pytest --cov=snip_url`; [design.md](design.md) sections 3 and 4 | Met (API schema: `/docs` does not list 404/409/429 and shows FastAPI's default 422 format, V10) |
| 6) Validation and Risk Control | Risks and trade-offs in brief sections 2b and 9; failure scenarios in specs; guardrails: tests, 80% coverage gate, validation rules, hooks; limitations list | `docs/project_brief.md`; [design.md](design.md) section 7; [decisions.md](decisions.md) | Met |
| 7) Controlled Autonomy | Agents work with fixed tools and folders (`coder` src and db_scripts, `tester` tests, others specs); humans approve spec, plan, merge and own the commit | `.claude/agents/*.md`; `.claude/settings.json`; `specs/*/summary.md` | Met |
| 8) Final Engineering Summary | `summary.md` per scenario: what was built, tests, approvals, retries, open items. Plan/rationale in `plan.md`; assumptions in `spec.md`; limitations in design.md | `specs/*/summary.md`; [design.md](design.md) section 7 | Met (README: "For reviewers (5 minutes)", "Limitations") |

### 4. Workflow Orchestration (Critical Differentiator): sub-items

Requirement 4 is one long sentence. Each element is listed separately.

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Agentic orchestration layer coordinating the full SDLC lifecycle: requirements | SPEC step, `spec-writer`, Approval 1 | `SKILL.md` step 1 | Met |
| ... architecture/design | No separate stage. `planner` writes design inside `plan.md` (impact analysis, file and function contract, data model). Approval 2 reviews it | `specs/*/plan.md` | Partly met: design is part of PLAN, not its own stage |
| ... implementation | BUILD step, `coder` | `SKILL.md` step 3; `.claude/agents/coder.md` | Met |
| ... testing | BUILD (`tester`) and VERIFY (`verify_gate.py`) | `.claude/agents/tester.md`; `.claude/hooks/verify_gate.py` | Met |
| ... documentation | DOCS step updates README; `summary.md` per feature | `SKILL.md` steps 5 and 6 | Met |
| ... release readiness | Approval 3 (merge) shows tests, coverage and changed files; the human commits. No separate release checklist, versioning or deployment step | `SKILL.md` Approval 3; CI in `.github/workflows/ci.yml` | Partly met: merge approval and CI only |
| Non-linear, stateful execution with governance, not simple linear chaining | Loops: reject at Approval 1, 2 or 3 re-runs the earlier step; VERIFY retries up to 2 rounds, then rollback; "stop here" ends early (S3). State lives in files (`specs/<feature>/`, `logs/audit.jsonl`, git), not in a database or code | `SKILL.md`; `specs/002-.../summary.md` | Partly met: the loops are followed by the AI from the skill, not run by a state machine (V8, [decisions.md](decisions.md) D-1) |
| Explicit dependency graph with entry/exit gates | Dependencies are explicit per task (`depends on`, `[P]`) in `tasks.md`. Gates: three approvals (entry to PLAN, BUILD, MERGE); VERIFY exit gate is code (pytest and 80% coverage) | `tasks.md` per feature; `.claude/hooks/verify_gate.py` | Partly met: the graph is a table in markdown, not a machine-readable graph; only the VERIFY gate is enforced by code |
| Sequential and parallel paths with synchronization | `coder` and `tester` start in one message and run in parallel; VERIFY joins them. Other steps are sequential | `SKILL.md` step 3; `[P]` tasks; `Agent` events in `logs/audit.jsonl`; [metrics.md](metrics.md) | Met |
| Preserve cross-stage context and decision lineage | request -> spec -> plan -> tasks -> summary in each feature folder; every prompt in `prompts/`; git history | `specs/`; `prompts/`; `git log --oneline` | Met |
| Enforce human approval checkpoints for high-impact actions | 3 approvals. The human commits and pushes; `git push`, `git add -A` and `git add .` are denied. Real rejections: S2 approvals 1 and 2, S4 approval 2 | `.claude/settings.json`; `specs/002-.../summary.md`; `specs/004-.../summary.md` | Met (approvals are enforced by the skill, not by code) |
| Bounded retries | `verify_gate.py` blocks at most 2 times | `.claude/hooks/verify_gate.py`; `prompts/03-hook-test.md` | Met |
| Fallback | After 2 failed fix rounds the workflow rolls back and escalates to the human (human-in-the-loop fallback) | `.claude/hooks/verify_gate.py`; `.claude/skills/sdlc/SKILL.md` step 4 | Partly met: human-in-the-loop fallback only; there is no automatic alternative strategy such as switching model or approach |
| Rollback | After the retry limit, `src/` and `tests/` are stashed (`git stash`). Spec files are not rolled back | `.claude/hooks/verify_gate.py`; `logs/audit.jsonl` | Met (proven by a hook drill; no scenario needed a rollback) |
| Safe-stop | Rollback message stops the flow and the human decides; "stop here" at Approval 1; policy guard exit code 2 stops an action | `SKILL.md` step 4; `.claude/hooks/policy_guard.py` | Met |
| Policy guardrails: security | Deny rules for `.env` and `git push`; `policy_guard.py` blocks writes outside the project, locked files, secret-like text and unsafe Bash. In S2 the agent could not read `.env.example` | `.claude/settings.json`; `.claude/hooks/policy_guard.py`; `prompts/08-deviation-fixes.md` | Met |
| Policy guardrails: compliance | IPs stored hashed only (app). For the workflow: audit log and approvals. No compliance rules engine and no retention policy | `src/snip_url/services/privacy.py`; `logs/audit.jsonl` | Partly met |
| Policy guardrails: change control | Locked files (hooks, settings, constitution, CI); human-only commit and push; named `git add` only | `.claude/hooks/policy_guard.py`; `CLAUDE.md` | Met |
| Audit-grade observability and traceability | `audit_log.py` appends a JSON line per tool call, prompt and stop; file contents are never logged | `logs/audit.jsonl`; `.claude/hooks/audit_log.py` | Partly met: long commands cut at 200 characters; menu choices logged as "a decision" only (V12); the log file is tracked in git (CLAUDE.md says it is git-ignored; it is not) |
| Track reliability metrics: success rate | `scripts/metrics.py` from audit log and git | `uv run python scripts/metrics.py`; [metrics.md](metrics.md) | Met |
| ... retry/rollback frequency | Same script: 4 retries, 1 rollback (drill) | [metrics.md](metrics.md) | Met |
| ... MTTR | Fail-to-pass pairs in the audit log: 7.8 s | [metrics.md](metrics.md); `prompts/08-deviation-fixes.md` part B | Partly met: one pair only |
| ... end-to-end latency | End-to-end minutes per run | [metrics.md](metrics.md) | Partly met: no per-stage latency |
| Dynamically re-plan when upstream outputs change | "No + comment" at Approval 2 or 3 sends the comment to `planner` for a new plan; at Approval 1 to `spec-writer` | `SKILL.md`; `specs/002-.../summary.md`; `specs/004-.../summary.md` | Partly met: re-planning happens on a human reject; nothing detects an upstream change automatically |
| Maintaining governance and controlled agent autonomy | Fixed agent tools and folders; hooks and approvals bound the rest | `.claude/agents/*.md`; `.claude/settings.json` | Met |

## 5. Deliverables

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Working prototype (runnable end-to-end) | App runs; `/docs` page; seed script gives sample data | `uv run uvicorn snip_url.main:app --reload`; `uv run python db_scripts/seed_data.py` | Met |
| Architecture overview (components, orchestration model, control flow, key decisions) | Workflow diagram (built), application diagram (built), target design (not built); decisions list | [architecture.md](architecture.md); [decisions.md](decisions.md) | Met |
| Three scenarios: greenfield, brownfield, ambiguous (each shows decomposition, orchestration, validation) | S1, S2, S3, plus S4. Each folder has request, spec, plan, tasks, summary. S3 stops at the spec, so it shows decomposition of the problem and approval, but no build or validation | [scenarios.md](scenarios.md); `specs/001-*` to `specs/004-*` | Met (S3 has no build by design) |
| Setup instructions | README has Windows PowerShell setup, endpoints, seed | `README.md` sections "For reviewers (5 minutes)", "Quick start (Windows PowerShell)", "Endpoints", "Metrics" | Partly met: README covers setup, but the fresh-clone check (checklist section F) is not done yet |
| Testing approach, limitations, and trade-offs | 81 pytest tests, coverage gate 80%, CI on every push, manual golden tests; limitations with IDs; trade-offs with alternatives | `uv run pytest --cov=snip_url`; `.github/workflows/ci.yml`; [review-checklist.md](review-checklist.md) section C; [design.md](design.md) section 7; [decisions.md](decisions.md) | Met (README section "Limitations") |

## 6. Evaluation Criteria

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Effectiveness of agentic orchestration | Skill + 4 subagents + 3 hooks + 3 approvals; four scenarios; metrics | Section 4 above; [metrics.md](metrics.md) | Partly met: no orchestrator code; step order not code-enforced (V8) |
| Architecture/system design quality | Layered app (routes, services, repos); target design with sizing | [architecture.md](architecture.md); [design.md](design.md) | Met |
| Depth of decomposition and execution quality | Tasks with owners, dependencies and `[P]`; parallel build | `specs/*/tasks.md` | Met |
| Realism/quality of outputs | Working API, 81 tests, 98.5% coverage, CI, seed data | `uv run pytest --cov=snip_url`; `src/` | Met |
| Validation and risk management rigor | Coverage gate, retry limit, rollback, policy guard; risks table; golden tests | `.claude/hooks/`; `docs/project_brief.md` section 9; [review-checklist.md](review-checklist.md) | Met |
| Clarity and defensibility of decisions | Decisions with context, alternative, why and trade-off | [decisions.md](decisions.md); brief section 2b | Met |
| Core engineering principles: modular | Strict layers: routes, services, repos | `specs/constitution.md`; [architecture.md](architecture.md) | Met |
| ... testable | 81 tests, injectable clock and settings | `tests/` | Met |
| ... reliable | Validation, one error format, transactional click tracking; single process, no retry layer | [design.md](design.md) | Partly met: prototype level |
| ... secure | URL validation, hashed IPs, no link editing, secrets blocked from agents; no auth | `src/snip_url/services/`; `.claude/hooks/policy_guard.py` | Partly met: no authentication |
| ... scalable | Sized on paper; target design only. SQLite, single process, in-memory rate limiter | [design.md](design.md) section 2; [architecture.md](architecture.md) diagram 3 | Not in scope for the build (brief section 10): target design, not built |
| ... safe change management | Approvals, locked files, named `git add`, human commit, CI | `CLAUDE.md`; `.claude/hooks/policy_guard.py`; `.github/workflows/ci.yml` | Met |
| Engineering judgment | Rejections with comments, scope limits (S3 stop, no backfill), honest deviation log | [decisions.md](decisions.md); [review-checklist.md](review-checklist.md) section D | Met |

## 7. Expectation

| Schwab asks | How snip-url meets it | Evidence | Status |
|---|---|---|---|
| Production-grade engineering work, strong design fundamentals | Layered code, tests, CI, constitution; prototype limits stated | `specs/constitution.md`; [design.md](design.md) | Partly met: prototype, not production (SQLite, no auth, no load test) |
| Lifecycle orchestration capability | `/sdlc` end to end, four scenarios | Section 4 above | Partly met (see orchestration gaps) |
| Output ownership and defensible reasoning | `summary.md`, `decisions.md`, exact approval replies in summaries and `prompts/` | `specs/*/summary.md`; [decisions.md](decisions.md) | Met |
| Principle: agents execute under defined autonomy boundaries; humans own oversight, approvals and final quality | Agent tool and folder limits; 3 approvals; human commit and push | `.claude/agents/*.md`; `.claude/settings.json`; `CLAUDE.md` | Met |

## 8. Gaps in one list

1. Stage order and loops are followed by the AI, not enforced by code; the dependency graph is a markdown table (V8).
2. No automatic fallback strategy (fallback is human escalation after rollback); rollback only covers `src/` and `tests/`.
3. No separate architecture/design or release-readiness stage.
4. Compliance guardrails are limited to hashed IPs and the audit log.
5. Metrics: MTTR from one pair; no per-stage latency; menu choices not recorded (V12).
6. Re-planning happens only on a human reject.
7. No load test, no authentication; the S3 target is undecided.
8. Rollback was proven by a drill, not by a real failed scenario.
9. `/docs` under-describes the API (V10, V11).
10. Fresh-clone check (checklist section F) pending.
