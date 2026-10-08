# Spec: Viral traffic (003)

## Summary

The request is one sentence: "Make it handle viral traffic." The business has not yet decided what that means, so scope, target load, success measure, overload behavior and click accuracy are open questions for the business owner. Recommended defaults are recorded as assumptions. Decided so far: stay inside the brief limits (no queue, no cache, no new infrastructure), keep the create rate limit as is, put no rate limit on redirects, and build nothing in this scenario. The spec holds only non-regression criteria.

## In scope

- Record the decisions, assumptions and open questions for viral traffic handling.
- Keep the existing behavior (create, redirect 302, click stats, custom alias, create rate limit) unchanged and protected by non-regression criteria.
- Any later traffic work must stay within the brief limits: no background queue, no cache, no new infrastructure.

## Acceptance criteria

1. AC1. Given the existing test suite passes, When this feature is complete, Then all existing tests still pass without being weakened, skipped or deleted.
2. AC2. Given a short link exists, When a client requests it, Then the response is still a 302 to the original URL and one click is recorded.
3. AC3. Given the create rate limit exists, When a client exceeds 10 creates in 60 seconds, Then the response is still 429 with a Retry-After header and the standard JSON error body.
4. AC4. Given the feature is complete, When tests run, Then coverage is at least 80%.

## Out of scope

- Building any traffic-handling change in this scenario. Nothing is built here.
- Performance, throughput or latency criteria (not defined until the business answers).
- Background click queue, cache (including Redis), Postgres, Docker, cloud deployment and any other new infrastructure.
- Changing the create rate limit.
- Adding a rate limit on redirects.
- Verification of load behavior. This is a FUTURE step, not part of this scope.

## Assumptions

Decided by the human (resolved, not assumptions):

- D1. Stay inside the brief limits: no queue, no cache, no new infrastructure in this prototype.
- D2. Keep the create rate limit as is (10 per 60 seconds). No rate limit on redirects.
- D3. Nothing is built in this scenario. Verification of viral-traffic handling is recorded as a FUTURE step, not part of this scope.

Recommended defaults below are not business decisions. Each is paired with an open question for the business owner.

- A1 (recommended default for Q1): the surge is mainly on redirects (reading a link). Create and stats reads are not the focus.
- A2 (recommended default for Q2): the target is a placeholder, a short spike of about 100 redirect requests per second on one link on a single server. The business must confirm or replace it.
- A3 (recommended default for Q3): "handle" means redirects keep working with no server errors (5xx) and no lost clicks during the spike. No latency number is set until the business gives one.
- A4 (recommended default for Q4): above the target, redirects keep working as well as they can and are never blocked (consistent with D2). Slowdown is acceptable.
- A5 (recommended default for Q5): click counts stay exact, as today.
- A6 (from the brief): the app stays FastAPI + SQLite with the layers api -> services -> repo.

## Open questions

1. (owner: business) Which operation must handle the surge: redirect, create, click-stats reads, or all? Recommended: A1.
2. (owner: business) What is the target load (requests per second, concurrent users, or a spike on one link)? Recommended: A2.
3. (owner: business) What does "handle" mean as a measurable result (no errors, a latency limit, no lost clicks, service stays up)? Recommended: A3.
4. (owner: business) When load exceeds the target, what should happen: slow down, return 429/503, or skip click counting while still redirecting? Recommended: A4.
5. (owner: business) Must click counts stay exact under load, or is approximate counting acceptable? Recommended: A5.
