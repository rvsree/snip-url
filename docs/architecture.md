# snip-url: Architecture

Author: Sree | Date: 2026-10-08 | Status: Draft for review

## 1. Overview

- snip-url is two things: a small URL shortener (FastAPI + SQLite) and the agentic SDLC workflow that built it.
- The app creates short links (random or custom alias), redirects with 302, records every click, and serves per-link and summary analytics. Rate limiting applies to link creation. IP addresses are stored hashed only.
- The workflow is Claude Code only: one skill (`/sdlc`), four subagents (`spec-writer`, `planner`, `coder`, `tester`), three hooks (`policy_guard`, `audit_log`, `verify_gate`). There is no custom orchestrator program.
- Three human approvals (spec, plan, merge) gate the work; the human commits and pushes.
- The app is fully deterministic. AI is used only in the development workflow. Diagrams 1 and 2 show what is built; diagram 3 is a target design that is **not built**.

## 2. Diagram 1: Agentic SDLC workflow (built)

```mermaid
flowchart TD
    classDef human fill:#fde68a,stroke:#b45309,color:#000
    classDef orch fill:#bfdbfe,stroke:#1d4ed8,color:#000
    classDef agent fill:#ddd6fe,stroke:#6d28d9,color:#000
    classDef hook fill:#fecaca,stroke:#b91c1c,color:#000
    classDef store fill:#bbf7d0,stroke:#15803d,color:#000

    subgraph H["Human"]
        human["Sree: runs claude, then /sdlc specs/feature"]
        a1["Approval 1: spec"]
        a2["Approval 2: plan and tasks"]
        a3["Approval 3: merge (human commits and pushes)"]
    end

    subgraph O["Orchestrator (Claude Code main session)"]
        sdlc["/sdlc skill (.claude/skills/sdlc/SKILL.md)"]
    end

    subgraph A["Subagents (AI)"]
        sw["spec-writer: spec.md"]
        pl["planner: plan.md and tasks.md"]
        co["coder: src/ and db_scripts/"]
        te["tester: tests/"]
    end

    subgraph G["Hooks (code, deterministic)"]
        pg["policy_guard.py: before Write, Edit, Bash"]
        al["audit_log.py: after tool, prompt, stop"]
        vg["verify_gate.py: at Stop, pytest + coverage, 2 retries, then rollback"]
    end

    subgraph D["Evidence"]
        specs["specs/feature/: request, spec, plan, tasks, summary"]
        log["logs/audit.jsonl"]
        met["scripts/metrics.py -> docs/metrics.md"]
        git["git history"]
    end

    human --> sdlc
    sdlc --> sw --> a1
    a1 -->|yes| pl --> a2
    a1 -->|no + comment| sw
    a2 -->|yes| co
    a2 -->|yes| te
    a2 -->|no + comment| pl
    co --> vg
    te --> vg
    vg -->|pass| a3
    vg -->|fail, retry| co
    vg -->|still failing| rb["rollback src/ and tests/ (git stash)"]
    a3 -->|yes| git
    a3 -->|no + comment| pl

    sw --> specs
    pl --> specs
    sdlc -.->|summary.md| specs

    pg -.->|guards| co
    pg -.->|guards| te
    pg -.->|guards| sdlc
    al -.-> log
    vg -.-> log
    log --> met
    git --> met

    class human,a1,a2,a3 human
    class sdlc orch
    class sw,pl,co,te agent
    class pg,al,vg,rb hook
    class specs,log,met,git store
```

| Component | Role |
|---|---|
| `/sdlc` skill | Runs the steps in order: SPEC, PLAN, BUILD, VERIFY, DOCS, MERGE, SUMMARY. Stops at each approval. Writes only `README.md` and `summary.md`. |
| `spec-writer` | Writes `spec.md` from `request.md`; asks questions when the request is vague. |
| `planner` | Writes `plan.md` (impact analysis and file/function contract) and `tasks.md` (owner, dependencies, [P]). |
| `coder` | Implements coder tasks in `src/snip_url/` and `db_scripts/`. |
| `tester` | Writes pytest tests in `tests/`. Runs in parallel with `coder`, bound by the plan.md contract. |
| `policy_guard.py` | PreToolUse on Write, Edit, MultiEdit, NotebookEdit, Bash. Exit code 2 blocks: locked files (`.claude/hooks/`, `.github/`, `settings.json`, `constitution.md`), secret-like text, `.env` access. |
| `audit_log.py` | PostToolUse, UserPromptSubmit and Stop. Appends one JSON line per event to `logs/audit.jsonl`; never blocks. |
| `verify_gate.py` | Stop hook. Runs pytest and coverage when `src/` or `tests/` changed. Blocks twice (max 2 retries), then rolls back. |
| `settings.json` | Deny rules: read of `.env` and `.env.*`, `git push`, `git add -A`, `git add .`. |
| `scripts/metrics.py` | Reads the audit log and git: runs, success rate, retries, rollbacks, MTTR, latency. |

**Deterministic vs AI boundary.** AI (non-deterministic): writing specs, plans, code and tests. Code (deterministic): hooks, deny rules, pytest, coverage, rollback, metrics. Step order is followed by the AI from the skill and is not forced by code (a known trade-off, V8 in the review checklist); the checks that matter are enforced by hooks.

## 3. Diagram 2: Current application (built)

```mermaid
flowchart TD
    classDef client fill:#fde68a,stroke:#b45309,color:#000
    classDef api fill:#bfdbfe,stroke:#1d4ed8,color:#000
    classDef svc fill:#ddd6fe,stroke:#6d28d9,color:#000
    classDef repo fill:#fbcfe8,stroke:#be185d,color:#000
    classDef data fill:#bbf7d0,stroke:#15803d,color:#000

    subgraph C["Clients"]
        caller["API caller (creates links)"]
        visitor["Visitor (opens a short link)"]
        reviewer["Reviewer (reads analytics, Swagger /docs)"]
    end

    subgraph R["FastAPI routes (api/routes.py, no logic)"]
        r_health["GET /health"]
        r_create["POST /api/links"]
        r_stats["GET /api/links/code/stats"]
        r_redirect["GET /code (302)"]
        r_alink["GET /api/analytics/links/code"]
        r_asum["GET /api/analytics/summary"]
    end

    subgraph S["Services (rules, no SQL)"]
        link["link_service"]
        limiter["rate_limiter (in memory, per IP)"]
        track["tracking_service"]
        analytics["analytics_service"]
        privacy["privacy (hash_ip)"]
    end

    subgraph P["Repos (SQL only)"]
        link_repo["link_repo"]
        client_repo["client_repo"]
        visitor_repo["visitor_repo"]
        stats_repo["stats_repo"]
        db["db.py (connection, init_db)"]
    end

    subgraph T["SQLite (data/snip_url.db)"]
        t1[("short_links")]
        t2[("click_events")]
        t3[("link_visitors")]
        t4[("api_clients")]
        t5[("daily_link_stats")]
    end

    caller --> r_create
    caller --> r_stats
    visitor --> r_redirect
    reviewer --> r_alink
    reviewer --> r_asum
    reviewer --> r_health

    r_create --> track
    r_create --> link
    r_stats --> link
    r_redirect --> link
    r_alink --> analytics
    r_asum --> analytics

    track --> limiter
    track --> privacy
    link --> privacy
    link --> track

    link --> link_repo
    track --> client_repo
    track --> visitor_repo
    track --> link_repo
    track --> stats_repo
    analytics --> stats_repo
    analytics --> link_repo

    link_repo --> t1
    link_repo --> t2
    client_repo --> t4
    visitor_repo --> t3
    stats_repo --> t5
    stats_repo --> t1
    stats_repo --> t2
    stats_repo --> t3
    stats_repo --> t4

    class caller,visitor,reviewer client
    class r_health,r_create,r_stats,r_redirect,r_alink,r_asum api
    class link,limiter,track,analytics,privacy svc
    class link_repo,client_repo,visitor_repo,stats_repo,db repo
    class t1,t2,t3,t4,t5 data
```

| Component | Role |
|---|---|
| `main.py` | `create_app()`: settings, rate limiter, error handlers, router; lifespan runs `init_db` at startup only. |
| `api/routes.py` | Six routes (health, create, stats, redirect, two analytics). No business logic. Uses the direct client IP, ignores `X-Forwarded-For`. |
| `common/errors.py` | `AppError` and one JSON error format `{"error": {...}}`; handlers for app errors and validation errors. |
| `services/link_service.py` | URL and alias validation, random 7-char code, create, `resolve_and_record_click`, `get_stats`. |
| `services/rate_limiter.py` | `RateLimiter`: in-memory sliding window per IP (create only). |
| `services/tracking_service.py` | Click recording, link-created counts, client lookup, `enforce_create_limit` (records rate-limit hits). |
| `services/analytics_service.py` | Per-link daily series and summary over a `days` window (1-90). |
| `services/privacy.py` | `hash_ip(ip, salt)`: raw IPs are never stored. |
| `repo/*_repo.py`, `repo/db.py` | All SQL. `db.py` holds the real schema, connection, commit/rollback, and `init_db` (renames old tables, adds missing columns). |
| SQLite tables | `short_links`, `click_events`, `link_visitors`, `api_clients`, `daily_link_stats` (see `db_scripts/schema.sql`, reference only). |
| `db_scripts/seed_data.py` | Re-runnable seed: 30+ links with clicks over 14+ days. |

**Deterministic vs AI boundary.** Everything in this diagram is deterministic code. A click and its counters are written in one transaction. No AI call happens at runtime.

## 4. Diagram 3: Target design (NOT built)

> **Target design, not built.** This is how snip-url could scale. Nothing in this diagram exists in the repository. It follows the reference article in section 6 and the NFR list in `docs/review-checklist.md` section E.

```mermaid
flowchart TD
    classDef client fill:#fde68a,stroke:#b45309,color:#000
    classDef edge fill:#e5e7eb,stroke:#374151,color:#000
    classDef svc fill:#ddd6fe,stroke:#6d28d9,color:#000
    classDef msg fill:#fed7aa,stroke:#c2410c,color:#000
    classDef data fill:#bbf7d0,stroke:#15803d,color:#000
    classDef obs fill:#fbcfe8,stroke:#be185d,color:#000

    subgraph C["Clients"]
        caller["API caller"]
        visitor["Visitor"]
        reviewer["Reviewer / admin"]
    end

    subgraph E["Edge (target, not built)"]
        cdn["CDN (redirects)"]
        lb["Load balancer"]
        gw["API gateway (auth, rate limit)"]
    end

    subgraph S["Services (target, not built)"]
        links["Link service (create, alias)"]
        redirect["Redirect service (read path)"]
        analytics["Analytics service (consumer + API)"]
    end

    subgraph M["Messaging (target, not built)"]
        clicks[["Kafka topic: link-clicks"]]
        dlq[["Kafka topic: link-clicks-dead-letter"]]
    end

    subgraph D["Data (target, not built)"]
        pg[("Postgres: links")]
        redis[("Redis: cache + rate limits")]
        astore[("Analytics store")]
        failed[("failed_events table")]
    end

    subgraph O["Observability (target, not built)"]
        metrics["Metrics"]
        logs["Logs"]
        alerts["Alerts"]
    end

    caller --> gw
    reviewer --> gw
    visitor --> cdn
    cdn --> lb
    gw --> lb
    lb --> links
    lb --> redirect
    lb --> analytics

    links --> pg
    redirect --> redis
    redirect --> pg
    redirect --> clicks
    gw --> redis
    clicks --> analytics
    analytics --> astore
    clicks -->|fails after retries| dlq
    dlq --> failed

    links --> metrics
    redirect --> metrics
    analytics --> metrics
    links --> logs
    redirect --> logs
    analytics --> logs
    metrics --> alerts
    dlq --> alerts

    class caller,visitor,reviewer client
    class cdn,lb,gw edge
    class links,redirect,analytics svc
    class clicks,dlq msg
    class pg,redis,astore,failed data
    class metrics,logs,alerts obs
```

| Component | Role (target, not built) |
|---|---|
| CDN | Serves redirects close to the visitor. |
| Load balancer + API gateway | Horizontal scaling; auth (API key/OAuth) for create and analytics; redirects stay public; trusted proxy IP for rate limits. |
| Link service | Create links and aliases. Owns link data in Postgres. |
| Redirect service | Read path: Redis cache-aside lookup, Postgres on miss, publishes a click event. Does not wait for analytics. |
| Analytics service | Consumes `link-clicks`, writes the analytics store, serves analytics API. Reads events, not shared tables. |
| Kafka `link-clicks` and dead-letter topic | Click events are written asynchronously; failed events go to the dead-letter topic. |
| Postgres / Redis / analytics store / `failed_events` | Links; cache and shared rate-limit counters; click analytics; failed events kept for retry and analysis. |
| Metrics, logs, alerts | Request metrics, error rate, latency percentiles, alerts on dead-letter growth. |

**Deterministic vs AI boundary.** Same as today: the whole runtime is deterministic. AI stays in the development workflow only.

## 5. Built vs target at a glance

| Aspect | Built | Target (not built) |
|---|---|---|
| Access path | HTTP API, Swagger `/docs` | CDN, load balancer, API gateway |
| Services | One process: routes -> services -> repos | Link, redirect and analytics services |
| Click recording | Synchronous, one transaction | Asynchronous via Kafka |
| Data | SQLite, 5 tables | Postgres, Redis, analytics store |
| Rate limiting | In memory, per direct IP, create only | Redis shared counter, trusted proxy IP |
| Failed events | Not stored | Dead-letter topic + `failed_events` |
| Auth | None | API key/OAuth for create and analytics |
| Monitoring | Agent workflow: audit log + `metrics.py`; app: uvicorn access log | Metrics, logs, alerts |

## 6. Comparison with the reference design

Reference article: "System Design | Design a URL Shortener (Tiny URL)", LeetCode Discuss, by Aryan Sharma: https://leetcode.com/discuss/post/6149386/system-design-design-a-url-shortener-tin-80zk/

| Reference article | snip-url | Why |
|---|---|---|
| Load balancer + API gateway + stateless web servers | Adopt in target design | Standard horizontal scaling |
| Redis cache-aside for hot links | Adopt in target design | Low-latency redirects |
| NFRs: low latency, high availability, fault tolerance, scalability | Adopt as NFR list | Same goals |
| 301 permanent redirect | Differ: 302 | 301 is cached by browsers, so repeat clicks are lost (this is BUG-01) |
| MongoDB (NoSQL) | Differ: SQL (prototype); key-value for redirects in target | Prototype needs transactions and simple setup |
| PUT update of destination URL | Differ: not offered | A changeable destination is a phishing risk |
| No rate limiting, no analytics design | Add: rate limiting, Kafka click events, analytics service, hashed IPs | Schwab asks for analytics and reliability |
