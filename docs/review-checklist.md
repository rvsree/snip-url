# snip-url: Review Checklist

Owner: Sree | Started: 2026-10-08 | Version: 2 (adds S4, deviation fixes, architecture, doc set)
Use: tick each box yourself before moving to the next stage.
Status key: Done / Partial / Pending / Gap

## 0. Plan for today (in order)

| # | Step | Output | Time | Done |
|---|---|---|---|---|
| 1 | Save and commit this checklist | docs/review-checklist.md | 2 min | [x] |
| 2 | Fix deviations V2, V3, V4 (section D) | SKILL.md order fix; recovery test in audit log; guard fix | 25 min | [x] |
| 3 | Scenario S4 via /sdlc: rename tables, new columns, 2 client tables, daily analytics table, analytics endpoints, seed script | specs/004-.../; 5 tables; db_scripts/seed_data.py | 75 min | [x] |
| 4 | Run the seed script; run golden tests G1-G24 (section C) | At least 30 links in data/snip_url.db | 20 min | [x] |
| 5 | 6a: scripts/metrics.py | Metrics per scenario incl. MTTR | 25 min | [x] |
| 6 | Architecture: confirm section G in text, then draw 2 diagrams (current, target) | docs/architecture.md + diagrams | 40 min | [x] |
| 7 | 6b: docs (section H) and README | Full doc set | 60 min | [x] |
| 8 | 6c: fill [INSERT] in prompts/ | No blanks left | 5 min | [ ] |
| 9 | 7: fresh-clone check (section F), then submit | Working repo | 20 min | [x] |
| | Total | | about 4.5 hours | |

Rule for every step: README.md is updated in the same step (how to start the app, endpoints, features, how to test).

## A. Schwab requirements: evidence and how to check

| # | Schwab asks | Evidence in repo | Status | How to check |
|---|---|---|---|---|
| 1 | Requirement understanding, ambiguity | spec.md per scenario; S3 has 5 open questions, 6 assumptions, 3 decisions | Done | specs/003-viral-traffic/spec.md |
| 2 | Task decomposition with dependencies | tasks.md (owner, depends on, [P]) | Done | specs/002-.../tasks.md |
| 3 | Codebase reasoning (brownfield) | S2 impact analysis; BUG-01 cause found from code; S4 schema change | Done | specs/002-.../plan.md |
| 4a | Stages with entry/exit gates | /sdlc skill (order) + verify_gate hook (code) | Partial (stage order followed by the AI, not enforced by code: V8) | .claude/skills/sdlc/SKILL.md, .claude/hooks/verify_gate.py |
| 4b | Sequential and parallel paths with sync | coder + tester in parallel, then VERIFY | Done | [P] tasks; audit log |
| 4c | Context and decision lineage | request -> spec -> plan -> tasks -> summary; prompts/; git | Done | specs/, prompts/ |
| 4d | Human approval for high-impact actions | 3 approvals; S2 has 2 "no + comment" loops | Done | prompts/06; summary.md |
| 4e | Bounded retry, rollback, safe-stop | Hook test: 2 blocks then rollback; no scenario needed a rollback | Done | prompts/03; audit log |
| 4e+ | Recovery (fail -> fix -> pass) | Recovery test (one pair) | Done | audit log: verify_fail then verify_pass |
| 4e++ | Fallback | Human escalation after rollback; no automatic alternative strategy | Partial | docs/SCHWAB_SPEC_MAPPER.md |
| 4f | Policy guardrails | settings.json deny rules + policy_guard.py | Done | S2: agent could not read .env.example |
| 4g | Audit-grade observability | logs/audit.jsonl | Partial (long commands cut at 200 characters; menu choices logged as a decision only: V12) | logs/audit.jsonl |
| 4h | Metrics: success rate, retries, rollbacks, MTTR, latency | scripts/metrics.py | Partial (MTTR from one pair; no per-stage latency) | uv run python scripts/metrics.py |
| 4i | Re-plan when upstream changes | S2 approval 2 and S4 approval 2 "no + comment" -> new plan; nothing detects an upstream change automatically | Partial | prompts/06 |
| 4j | Controlled autonomy | Folder rules per agent, hooks, approvals | Done | .claude/agents/*.md |
| 5 | Code, API, tests | src/, plan.md contract, tests/ (81 tests, 98.5%) | Done | uv run pytest --cov=snip_url |
| 6 | Docs and final engineering summary | summary.md per scenario; docs/ | Done | docs/ |
| D1 | Deliverable: working prototype | App runs; /docs page | Done | Section C |
| D2 | Deliverable: architecture overview | docs/architecture.md, docs/architecture.html, docs/diagrams/ | Done | docs/architecture.md |
| D3 | Deliverable: 3 scenarios | S1, S2, S3 (+ S4) | Done | specs/001-004 |
| D4 | Deliverable: setup instructions | README | Done | Section F |
| D5 | Deliverable: testing, limitations, trade-offs | README + docs/design.md + docs/decisions.md | Done | docs/design.md section 7 |

## B. Stage checkpoints

| Step | Checkpoint | Done |
|---|---|---|
| 2 | SKILL.md writes summary.md BEFORE the merge commit, so it is included in the commit | [x] |
| 2 | Audit log has verify_fail followed by verify_pass (recovery) | [x] |
| 2 | Guard allows os.environ but still blocks .env | [x] |
| 3 | S4 spec lists all 5 tables, the analytics endpoints and the seed script | [x] |
| 3 | No raw IP stored anywhere (hashed only) | [x] |
| 3 | Existing 45 tests still pass after the table renames | [x] |
| 3 | Coverage at least 80% | [x] |
| 4 | Seed script is re-runnable: running it twice does not duplicate or delete data | [x] |
| 4 | At least 30 links, clicks across at least 14 days | [x] |
| 5 | metrics.py shows S1-S4: runs, success rate, retries, rollbacks, MTTR, time per run | [x] |
| 6 | Section G confirmed by Sree before drawing (diagrams approved 2026-10-08) | [x] |
| 6 | Target diagram clearly labelled "target design, not built" | [x] |
| 7 | Every doc in section H exists, dated truthfully | [x] |
| 7 | README: start app, endpoints, features, tests, seed, metrics, Claude Code version, Limitations | [x] |
| 8 | No [INSERT] left: Select-String -Path prompts\*.md -Pattern "INSERT" | [ ] |
| 9 | Fresh clone works by README only; CI green; git grep -n "sk-ant-" finds nothing | [x] |

## C. Golden dataset: manual tests

Start the app: `uv run uvicorn snip_url.main:app` then open http://127.0.0.1:8000/docs and use "Try it out".
Run G13 last or wait 60 seconds after it (it uses up the create limit).
G1-G24: all 24 passed on 2026-10-08.

| ID | Input | Expected | Pass |
|---|---|---|---|
| G1 | Create: url https://www.schwab.com | Success; 7-character code and short URL | [x] |
| G2 | Create: url ftp://example.com | 422, JSON error | [x] |
| G3 | Create: url longer than 2048 characters | 422, JSON error | [x] |
| G4 | Open the G1 short URL | 302 to https://www.schwab.com | [x] |
| G5 | Open it again, then get stats | click count 2 | [x] |
| G6 | Open unknown code zzzzzzz | 404, JSON error | [x] |
| G7 | Stats for G1 | original URL, created time, click count | [x] |
| G8 | Create with alias my-link | Success; code is my-link | [x] |
| G9 | Create with alias my-link again | 409 alias_taken | [x] |
| G10 | Create with alias ab | 422 invalid_alias | [x] |
| G11 | Create with alias DOCS | 422 reserved_alias | [x] |
| G12 | Create with alias My-Link | Success (case-sensitive) | [x] |
| G13 | Create 11 links within 60 seconds | 11th returns 429 with Retry-After | [x] |
| G14 | Health endpoint | 200 | [x] |
| G15 | Restart the app, open the G1 short URL | Still redirects | [x] |
| G16 | After running the app | data\snip_url.db exists; none in project root | [x] |
| G17 | After S4: run the seed script | At least 30 links; clicks over at least 14 days | [x] |
| G18 | Run the seed script a second time | Same row counts (no duplicates) | [x] |
| G19 | Analytics for one seeded link | Clicks per day and unique visitors per day | [x] |
| G20 | Analytics summary | Top links by clicks | [x] |
| G21 | Click a link, check link visitors | Visitor row with hashed IP, not raw IP | [x] |
| G22 | Create a link, check API clients | Caller row with hashed IP and links-created count | [x] |
| G23 | Analytics for one link with days=91 | 422, JSON error | [x] |
| G24 | Analytics for an unknown code | 404, JSON error | [x] |

## D. Deviation log (design vs build)

| ID | Deviation | Impact | Action | Status |
|---|---|---|---|---|
| V1 | Data model and API contract are sections of plan.md, not separate files | None | Brief updated | Done |
| V2 | /sdlc writes summary.md after the merge commit | Summary committed by hand | Fix SKILL.md order (step 2) | Done (commit 6b85dd2) |
| V3 | No fail -> fix -> pass in audit log; MTTR not computable | Success criterion 3 partly met | Recovery test (step 2) | Done (commit 6b85dd2) |
| V4 | Bash guard blocks any command containing ".env", including os.environ | Safe side, but false positives | Fix guard (step 2); you edit by hand (file is protected) | Done (commit 6b85dd2) |
| V5 | /sdlc not listed in the VS Code chat panel; runs from the terminal | None | README note | Done (README note) |
| V6 | Tables links and clicks: short names, few columns; no client or analytics tables | Weak data model for analytics | S4 (step 3) | Done (S4) |
| V7 | Claude Code updated mid-project (2.1.270 -> 2.1.293) | None seen | README note | Done (README note) |
| V8 | /sdlc step order followed by the AI, not enforced by code | Known trade-off | decisions.md | Open (known trade-off, decisions.md D-1) |
| V9 | requirements-map.md in brief replaced by SCHWAB_SPEC_MAPPER.md | Name only | Update brief section 6 in step 7 | Done (brief section 6 updated) |
| V10 | /docs (OpenAPI) does not list 404/409/429 and shows FastAPI's default 422 format, not the real {"error": {...}} format | /docs under-describes the API | Documented in design.md section 7; README is the reference | Open |
| V11 | The query-parameter validation message says "Request body is invalid" for a bad ?days value | Wrong wording; code and status are correct | Documented in design.md section 7 | Open |
| V12 | Approvals chosen from Claude Code's menu are logged as a decision, not the choice made | metrics.py cannot count S4's "no + comment" as a re-plan | Exact replies are in summary.md and prompts/ | Open |
| V13 | Race on random-code insert: the code is checked first and inserted second, with a plain insert, so two simultaneous requests that pick the same new code could make the second insert fail with an unhandled database error | Very unlikely with one SQLite process; real at scale | Target design must retry on a duplicate-key error (design.md sections 2.2 and 7) | Open |

## E. Non-functional requirements (NFR)

| NFR | In this prototype | Target design (documented, not built) |
|---|---|---|
| Latency | Redirect: one indexed lookup + inserts; no load test | Redis cache for hot links; click events written asynchronously |
| Scalability | Single process, SQLite | Stateless services behind a load balancer; Postgres (links), analytics store |
| SQL vs NoSQL | SQL (SQLite): simple, transactional | Key-value store for redirect lookups; SQL/columnar for analytics |
| Async / parallel | Synchronous click recording | Kafka (or SQS) topic link-clicks; analytics service consumes |
| Error handling | Input validation; one JSON error format; 404/409/422/429 | Same + retries on downstream failures |
| Failed transactions | Not stored | Dead-letter topic + failed_events table for retry and analysis |
| Rate limiting | In-memory, per IP, create only | Redis shared counter; trusted proxy IP behind the load balancer |
| Monitoring | Agent workflow: audit log + metrics.py; app: uvicorn access log | Request metrics, error rate, latency percentiles, alerts |
| Privacy | (S4) IP stored hashed only | Same + retention policy |
| Security | URL validation; no link editing; secrets never reach agents | Auth for create and analytics; abuse/phishing checks |
| Testability | 81 tests, 98.5% coverage, CI | Load tests once S3 open questions are answered |

## F. Fresh-clone check (step 9)

| Step | Command | Expected | Done |
|---|---|---|---|
| 1 | git clone https://github.com/rvsree/snip-url.git snip-url-check | Folder created | [x] |
| 2 | cd snip-url-check; uv sync | Packages installed | [x] |
| 3 | uv run pytest --cov=snip_url | All pass, coverage at least 80% | [x] |
| 4 | uv run python db_scripts/seed_data.py | Seed rows created | [x] |
| 5 | uv run python scripts/metrics.py | Metrics table printed | [x] |
| 6 | uv run uvicorn snip_url.main:app | /docs page loads; analytics shows seeded data | [x] |

## G. Architecture: content to confirm before drawing

| Item | Current prototype (built) | Target design (not built) |
|---|---|---|
| Personas | Link creator (API caller); visitor (clicks a short link); reviewer (reads analytics); developer (Sree, runs /sdlc) | + Admin / operations |
| Access path | HTTP API (FastAPI, Swagger /docs) | API gateway + load balancer; CDN in front of redirects |
| Components by layer | API (routes) -> services (link, rate limiter, analytics) -> repo (SQL) -> SQLite | Link service (create, alias); Redirect service (read path); Analytics service (consumer + API); shared Kafka |
| Data | 5 tables after S4: short_links, click_events, link_visitors, api_clients, daily_link_stats | Postgres (links); Redis (cache, rate limit); Kafka topics link-clicks + dead-letter; analytics store |
| Deterministic vs AI | App is fully deterministic. AI agents only in the development workflow (spec, plan, code, tests) | Same |
| Data access | Only repo layer talks to the database | Each service owns its data; analytics via events, not shared tables |
| Auth | None (prototype) | API key/OAuth for create and analytics; redirects public |
| State | SQLite file; in-memory rate limiter | Postgres, Redis, Kafka offsets |
| Diagram style | Colored layers: clients, edge, services, messaging, data, observability | Same style, "target" label |

Reference article for the target design: "System Design | Design a URL Shortener (Tiny URL)", LeetCode Discuss, by Aryan Sharma: https://leetcode.com/discuss/post/6149386/system-design-design-a-url-shortener-tin-80zk/

| Reference article | snip-url | Why |
|---|---|---|
| Load balancer + API gateway + stateless web servers | Adopt in target design | Standard horizontal scaling |
| Redis cache-aside for hot links | Adopt in target design | Low-latency redirects |
| NFRs: low latency, high availability, fault tolerance, scalability | Adopt as NFR list | Same goals |
| 301 permanent redirect | Differ: 302 | 301 is cached by browsers, so repeat clicks are lost (this is BUG-01) |
| MongoDB (NoSQL) | Differ: SQL (prototype); key-value for redirects in target | Prototype needs transactions and simple setup |
| PUT update of destination URL | Differ: not offered | A changeable destination is a phishing risk |
| No rate limiting, no analytics design | Add: rate limiting, Kafka click events, analytics service, hashed IPs | Schwab asks for analytics and reliability |

## H. Document set (FDE view, one set, no duplicates, true dates)

| Document | Purpose | Written | Status |
|---|---|---|---|
| docs/project_brief.md | Problem, success criteria, architecture, trade-offs, risks, plan (pre-build) | 2026-10-07, before build | Done |
| docs/review-checklist.md | This file: progress, golden tests, deviations, NFR | 2026-10-08 | Done |
| docs/architecture.md | Current and target architecture, 3 diagrams (workflow, application, target) | 2026-10-08 | Done |
| docs/design.md | API, data model (5 tables), NFR, target design | Step 7 | Done |
| docs/decisions.md | Key decisions and trade-offs, incl. S2/S3/S4 decisions | Step 7 | Done |
| docs/SCHWAB_SPEC_MAPPER.md | For Schwab: every FR, NFR, deliverable and evaluation criterion -> evidence in repo | Step 7 | Done |
| docs/scenarios.md | S1-S4: what each proves, links to specs and prompts | Step 7 | Done |
| README.md | Start, endpoints, features, tests, seed, metrics, limitations | Every step | Done (Stage 3; fresh-clone check done 2026-10-08) |
| docs/architecture.html, docs/data-model.html, docs/diagrams/ | Rendered diagrams: workflow, application, target design, data model | Stage 1-3 | Done |
| docs/metrics.md | Generated by scripts/metrics.py | 2026-10-08 | Done |
