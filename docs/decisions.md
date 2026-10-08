# snip-url: Decisions

Author: Sree | Date: 2026-10-08 | Status: Draft for review

One short entry per decision. D-1 to D-8 are the brief's key trade-offs ([project_brief.md](project_brief.md) section 2b). D-9 onward were made while running the scenarios. Where a human reply is quoted, the source is the scenario's `summary.md` or `prompts/` file.

| ID | Decision | Source |
|---|---|---|
| D-1 | Claude Code skill + subagents + hooks as the orchestrator | Brief 2b |
| D-2 | Gates are hooks (code), not AI self-checks | Brief 2b |
| D-3 | coder and tester run in parallel | Brief 2b |
| D-4 | Rollback is a git stash of `src/` and `tests/` | Brief 2b |
| D-5 | SQLite as the database | Brief 2b |
| D-6 | Random 7-character base62 short codes | Brief 2b |
| D-7 | Redirect with 302, not 301 | Brief 2b |
| D-8 | Live agent runs only, no replay | Brief 2b |
| D-9 | Alias rules: case-sensitive, reserved words matched ignoring case | S2 |
| D-10 | 422 for bad or reserved alias; 409 for a taken alias | S2 |
| D-11 | Rate limit and identity use the direct IP only | S2 |
| D-12 | S3 stops at the approved spec; nothing is built | S3 |
| D-13 | S3 assumptions are recommended defaults owned by the business | S3 |
| D-14 | Click tracking happens in one transaction | S4 |
| D-15 | IP addresses are stored only as salted hashes | S4 |
| D-16 | Migrated rows are not backfilled | S4 |
| D-17 | `metrics.py` takes commits and their times from git | Metrics |

---

## D-1 Orchestrator

- **Context:** Schwab asks for orchestration with stages, gates and parallel paths. 2-3 days, one person.
- **Decision:** One skill (`/sdlc`) in Claude Code runs the steps; four subagents do the work; three hooks enforce the checks.
- **Alternative:** A custom Python pipeline or LangGraph.
- **Why:** Much less code, uses the tool Schwab asked about, easy to explain live.
- **Trade-off:** The step order is followed by the AI, not forced by code (deviation V8). Hooks make the important checks (tests, unsafe writes, logging) impossible to skip; the order is not.

## D-2 Gates are hooks

- **Context:** An AI that checks its own work can decide to skip the check.
- **Decision:** `policy_guard` (before writes and Bash), `audit_log` (after every tool call) and `verify_gate` (at "done") are Python scripts run by Claude Code.
- **Alternative:** Ask the AI to run and report tests.
- **Why:** A hook cannot be talked out of running.
- **Trade-off:** Hooks are specific to Claude Code and to Windows paths tested here.

## D-3 Parallel build

- **Context:** Schwab asks for parallel paths with a sync point.
- **Decision:** `coder` (src/) and `tester` (tests/) run at the same time in one message; VERIFY is the join.
- **Alternative:** Code first, then tests.
- **Why:** Shows a real fork and join, and tests written from the plan are independent of the code.
- **Trade-off:** `plan.md` must hold an exact file and function contract or the two sides drift apart.

## D-4 Rollback

- **Context:** After failed retries the workflow must stop safely.
- **Decision:** After 2 failed retries `verify_gate` runs `git stash push --include-untracked -- src tests`.
- **Alternative:** A git branch per run.
- **Why:** One command, easy to recover (`git stash pop`).
- **Trade-off:** Only code is rolled back, not spec files.

## D-5 SQLite

- **Context:** The reviewer must run the app in under 10 minutes.
- **Decision:** SQLite in `data/snip_url.db`.
- **Alternative:** Postgres.
- **Why:** No setup.
- **Trade-off:** One writer, single process, not for production scale. Postgres is the target design ([design.md](design.md) section 2).

## D-6 Short code

- **Context:** Codes must be short and hard to guess.
- **Decision:** 7 random base62 characters from `secrets.choice`; checked for uniqueness on insert, up to 10 tries.
- **Alternative:** A counter or a hash of the URL.
- **Why:** No guessable sequence, no state. 62^7 is about 3.5 trillion, so collisions are rare ([design.md](design.md) section 2).
- **Trade-off:** A small collision chance, handled by the check.

## D-7 Redirect status

- **Context:** Clicks must be counted.
- **Decision:** HTTP 302.
- **Alternative:** 301.
- **Why:** Browsers cache a 301, so repeat visits never reach the server. This was BUG-01, seeded on purpose and fixed in S2.
- **Trade-off:** Slightly more server load.

## D-8 Live runs only

- **Context:** Reproducibility versus honesty.
- **Decision:** Every scenario ran live; outputs (specs, summaries, audit log) are committed as evidence.
- **Alternative:** Recorded replay.
- **Why:** Honest and simple.
- **Trade-off:** Results vary from run to run, each run costs money, and the demo should not re-run them.

## D-9 Alias case rules (S2)

- **Context:** Custom aliases need rules for letter case and reserved names.
- **Decision:** Aliases are case-sensitive (`My-Link` and `my-link` are different). Reserved words (`api`, `health`, `docs`, `openapi`) are matched ignoring case, so `DOCS` is rejected.
- **Alternative:** Case-insensitive aliases.
- **Why:** Matches the random codes, which are case-sensitive base62. Reserved words must be blocked in every spelling because they are real paths.
- **Trade-off:** Two aliases that differ only by case can look alike to a person.

## D-10 422 versus 409 (S2)

- **Context:** An alias can fail in three ways.
- **Decision:** Bad characters or length: 422 `invalid_alias`. Reserved word: 422 `reserved_alias`. Already used: 409 `alias_taken`. An alias equal to an existing random code is also 409.
- **Alternative:** One 400 for all; or overwrite an equal random code.
- **Why:** 422 matches the existing URL validation. 409 means "valid request, conflicts with existing state". Overwriting would let someone hijack another person's link.
- **Trade-off:** Callers handle two codes.

## D-11 Direct IP only (S2)

- **Context:** The rate limit needs a client identity.
- **Decision:** Use the direct connection IP. Ignore `X-Forwarded-For`. Count every create request, including failed ones.
- **Alternative:** Trust `X-Forwarded-For`.
- **Why:** The header can be faked by the client, which would bypass the limit.
- **Trade-off:** Behind a proxy or NAT all callers look like one. The target design uses a trusted proxy IP behind the load balancer. The same identity feeds visitors and API clients in S4.

## D-12 S3 stops at the spec

- **Context:** "Make it handle viral traffic" has no target, no measure and no scope.
- **Decision:** The agent asked its questions; the human replied "yes, stop here" at Approval 1. Nothing was planned or built.
- **Alternative:** Pick a target and build a cache or queue.
- **Why:** Building against a guess wastes effort and breaks the brief's limits. Stopping is the correct safe behavior for an ambiguous requirement.
- **Trade-off:** No performance work in this prototype.

## D-13 S3 assumptions owned by the business

- **Context:** The business has not answered five questions.
- **Decision:** For each question the spec records a recommended default as an assumption (A1-A5) and keeps the question open for the business owner. The human added three firm decisions (stay inside the brief; keep the create limit, no redirect limit; build nothing).
- **Alternative:** Treat the defaults as approved requirements.
- **Why:** An assumption the business has not accepted must not become a requirement. Planning and load verification wait for the answers.
- **Trade-off:** The estimates in [design.md](design.md) section 2 are also unconfirmed.

## D-14 One-transaction tracking (S4)

- **Context:** A redirect updates four things: the click event, the visitor, `last_clicked_at` and the daily stat. At Approval 2 the human wrote: "Fix risk 2: record the click event, the visitor update and the daily_link_stats update in ONE database transaction, so they can never get out of step. Add a test that proves a failure in the middle saves none of them."
- **Decision:** `tracking_service.record_click` does all writes without committing and commits once; any exception rolls back everything.
- **Alternative:** Commit after each repo call.
- **Why:** The analytics must always agree with the click events.
- **Trade-off:** The redirect does more work while holding the SQLite write lock. This is the main reason the target design moves click recording to Kafka.

## D-15 Hashed IPs (S4)

- **Context:** Visitor and client tracking needs an identity, but a raw IP is personal data.
- **Decision:** Store `sha256(salt:ip)` only; the salt comes from `IP_HASH_SALT` with a fixed default for local development. No column in any table holds a raw IP.
- **Alternative:** Store the IP, or store nothing.
- **Why:** Counting unique visitors needs a stable identity; a salted hash gives it without keeping the address.
- **Trade-off:** The default salt is public, so a hash from a default-salt deployment could be reversed by brute force over the IPv4 space. Production must set `IP_HASH_SALT`. A retention policy is target design.

## D-16 No backfill (S4)

- **Context:** The S4 migration renames `links` and `clicks` and adds columns to databases that already hold data.
- **Decision:** Old rows keep empty visitor and client data (`created_by_client`, `visitor`, `user_agent`, `referrer` null; `last_clicked_at` null; `is_custom_alias` 0). Nothing is invented and nothing is lost.
- **Alternative:** Guess values for old rows or rebuild `daily_link_stats` from old clicks.
- **Why:** Old clicks have no IP, so the data cannot be recovered; guessing would produce false analytics.
- **Trade-off:** Analytics for pre-S4 links start empty, and `daily_link_stats` is not backfilled.

## D-17 Metrics: git as the source of truth for commits

- **Context:** The first `metrics.py` run showed a 25% success rate and a 586-minute S3 run. The audit hook cuts commands at 200 characters, so "git commit" was often lost, and idle sessions stretched run times.
- **Decision:** A run is "committed" if a commit subject starts with its scenario folder and a colon; its end time is that commit's time. Runs that are not committed end at a gap of more than 30 minutes. A run that stopped at spec is detected from the prompt "stop here".
- **Alternative:** Trust the audit log alone.
- **Why:** Git history is complete and cannot be truncated; the audit log is complete for actions but lossy for long commands.
- **Trade-off:** Metrics depend on commit subjects following the `specs/<feature>:` convention. Approvals chosen from the menu are not typed prompts, so they are logged as decisions only (V12).
