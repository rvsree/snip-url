# 11 - Architecture, docs and handover (build steps 6, 7, 8)

**Date:** 2026-10-08
**Purpose:** Claude Code writes all remaining documents from the real repo, in 3 stages, stopping after each for human review.
**Where:** Claude Code in the VS Code terminal (`claude`), one session.
**Input not in git:** `_private/schwab_assignment.pdf` (Schwab's assignment, kept out of the repo; `_private/` is git-ignored).

## Stage 1: architecture (step 6)

```
Stage 1 of 3. Do not run /sdlc. Do not change src/, tests/ or db_scripts/. Do not git add or commit.

Read docs/project_brief.md (sections 2, 2a, 2b), docs/review-checklist.md (sections E and G, including the reference article table), CLAUDE.md, .claude/ (agents, skill, hooks, settings.json), src/snip_url/ and db_scripts/schema.sql.

Write docs/architecture.md with:
1. Overview: what is built (app + agentic SDLC workflow) in 5 lines.
2. Diagram 1 "Agentic SDLC workflow (built)": human -> /sdlc skill -> spec-writer, planner, coder + tester in parallel -> VERIFY gate -> approvals; hooks (policy_guard, audit_log, verify_gate) around tool calls; audit log and metrics.py.
3. Diagram 2 "Current application (built)": colored layers: clients (API caller, visitor, reviewer) -> FastAPI routes -> services (link, rate limiter, tracking, analytics, privacy) -> repos -> SQLite with the 5 real tables.
4. Diagram 3 "Target design (NOT built)": colored layers: clients; edge (CDN, load balancer, API gateway); services (link service, redirect service, analytics service); messaging (Kafka topics link-clicks and a dead-letter topic); data (Postgres for links, Redis for cache and rate limits, analytics store, failed_events table); observability (metrics, logs, alerts). Title and caption must say "target design, not built".
5. Under each diagram: a short table of components, one line each, and the deterministic vs AI boundary (the app is fully deterministic; AI is used only in the development workflow).
6. A section "Comparison with the reference design" using the table in checklist section G.
Use Mermaid flowcharts (GitHub renders them) with subgraphs per layer and classDef colors per layer, the same color per layer in diagrams 2 and 3. Use only names that exist in the code for the built diagrams.

When done, list what you wrote and STOP for my review.
```

## Stage 2: design and Schwab mapping docs (step 7a)

```
Stage 2 of 3. Same rules: no /sdlc, no changes to src/, tests/, db_scripts/; no git add or commit.

Read _private/schwab_assignment.pdf (Schwab's assignment; never copy it into the repo, only refer to its requirement names), the specs/ folders (request, spec, plan, tasks, summary for 001-004), prompts/ 01-10, docs/metrics.md, docs/review-checklist.md, docs/project_brief.md and the code.

Write:
1. docs/design.md: API (every endpoint: method, path, request, responses incl. error codes and the JSON error format); data model (the 5 real tables with columns, keys and indexes, from the code); key flows (create, redirect with one-transaction tracking, analytics); non-functional requirements (checklist section E, built vs target); known limitations (checklist section D items still open, plus V10, V11, V12 below).
2. docs/decisions.md: one short entry per decision (context, decision, alternative, why, trade-off): brief section 2b items, plus decisions made in S2 (alias case rules, 422 vs 409, direct IP only), S3 (stop at spec, assumptions owned by business), S4 (one-transaction tracking, hashed IPs, no backfill), metrics rules (git as source of truth for commits).
3. docs/SCHWAB_SPEC_MAPPER.md: for Schwab reviewers. One table per section of Schwab's assignment (objective, scope, every core requirement and every sub-item of the orchestration requirement, deliverables, evaluation criteria). Columns: Schwab asks (their requirement name) | How snip-url meets it | Evidence (exact file paths or commands) | Status (Met / Partly met / Not in scope, with reason). Be honest: mark gaps as gaps.
4. docs/scenarios.md: S1-S4 and the two hook drills: request type, what it proves, human decisions, result (tests, coverage, retries), links to specs/ and prompts/.

New findings to include as limitations:
- V10: /docs (OpenAPI) does not list 404/409/429 responses, and shows FastAPI's default 422 format instead of the real {"error": {...}} format.
- V11: the query-parameter validation message says "Request body is invalid" for a bad ?days value.
- V12: approvals chosen from Claude Code's menu are logged as a decision, not the choice made; exact replies are in summary.md and prompts/.

When done, list what you wrote and STOP for my review.
```

## Stage 3: README, checklist, brief, prompt blanks (steps 7b, 8)

```
Stage 3 of 3. Same rules: no /sdlc, no changes to src/, tests/, db_scripts/; no git add or commit.

1. README.md (rewrite, keep it practical): what snip-url is (app + agentic SDLC workflow); quick start on Windows PowerShell (uv sync, run tests, run the seed, start the app, open /docs); every endpoint with one example; features list; how the /sdlc workflow works (run from the terminal with claude; /sdlc does not appear in the VS Code chat panel); how to run metrics; project structure; documentation index (all docs/ files); Claude Code version used (run claude --version); Limitations (from docs/design.md).
2. docs/review-checklist.md: tick golden tests G1-G24 (all passed on 2026-10-08), tick completed checkpoints in sections 0 and B, set statuses in section A to match docs/SCHWAB_SPEC_MAPPER.md, add V10, V11, V12 to section D, mark V1-V9 Done or Open as they really are.
3. docs/project_brief.md section 6 (structure): add db_scripts/ and prompts/, replace requirements-map.md with SCHWAB_SPEC_MAPPER.md, add design.md, decisions.md, scenarios.md, metrics.md, review-checklist.md. Change nothing else in the brief.
4. prompts/: replace every [INSERT] with real values from git log and specs/*/summary.md (commit IDs, dates, my approval replies). If a value cannot be found, write "not recorded" instead of guessing.
5. Show me: git status --short, and a list of every file changed with one line each.

Then STOP. I will review, commit and push myself.
```

## Result

- Stage 1: `docs/architecture.md` (3 Mermaid diagrams, reference comparison).
- Stage 2: `docs/design.md`, `docs/decisions.md`, `docs/SCHWAB_SPEC_MAPPER.md` (checked against the Schwab PDF), `docs/scenarios.md`.
- Stage 3: `README.md`, `docs/review-checklist.md`, `docs/project_brief.md` section 6, `prompts/01-10` blanks filled.
- Review notes: the mapper's Fallback row is "Partly met"; the S3 counts are 5 open questions, 6 assumptions, 3 decisions; checklist golden tests run G1-G24.
- Commit ID: not recorded (the human commits and pushes).
