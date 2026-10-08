# Request: Custom alias, rate limiting, bug fix and refactor (S2)

Type: Brownfield (enhancement, bug fix, refactor, test and doc improvement) on the S1 code

## Enhancements

1. Custom alias: when creating a short link, a user may give their own alias instead of a random code.
   - 3 to 30 characters: letters, digits and hyphens only.
   - Must be unique. If it is already taken, return 409 with a clear error message.
   - Reserved words cannot be used as an alias: api, health, docs, openapi.
   - If no alias is given, the service works as today (random 7-character code).
2. Rate limiting on link creation: at most 10 create requests per minute per client IP.
   - Over the limit: return 429 with a clear error message and a Retry-After header.
   - Redirects and stats are not rate limited.
   - In-memory counting is fine for now (single server).

## Bug fix

3. BUG-01: users report that the click count is lower than the real number of visits, especially for people who open the same short link more than once. Find the cause, fix it, and add a regression test that would have caught it.

## Refactor

4. DEF-02: the database file is created in the project root as soon as the app code is loaded. It must be created in data/snip_url.db (path from the DATABASE_PATH setting, see .env.example), and only when the app starts, not on import. Tests must keep using a temporary database.

## Tests and docs

5. Every change above has tests. All existing tests must still pass.
6. README: document the alias option, the rate limit, and the DATABASE_PATH setting.

Not needed now: user accounts, link expiry, editing or deleting links, a shared rate-limit store (Redis).
