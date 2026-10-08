# Spec: Custom alias, rate limiting, BUG-01 fix, DEF-02 refactor

## Summary

This change extends the S1 URL shortener in four ways. Users can choose their own alias when creating a link. Link creation is limited to 10 requests per minute per client IP. BUG-01 is fixed: the redirect returns 301, so browsers cache it and repeat visits are not counted. DEF-02 is fixed: the database is created at the `DATABASE_PATH` location only when the app starts, not on import. Tests and README are updated for all of it.

## In scope

- Optional custom alias on link creation (3 to 30 characters, letters, digits and hyphens only).
- 409 error when the alias is already taken.
- Invalid aliases rejected with 422 (`invalid_alias`); reserved aliases (api, health, docs, openapi, any case) rejected with 422 (`reserved_alias`).
- Setting `SNIP_DB_PATH` renamed to `DATABASE_PATH` (old name dropped).
- Random 7-character code when no alias is given (unchanged).
- In-memory rate limit on link creation: 10 requests per minute per client IP; 429 with a clear error and a `Retry-After` header.
- BUG-01: change the redirect from 301 to 302 so every visit reaches the server and is counted; add a regression test.
- DEF-02: database path comes from the `DATABASE_PATH` setting (default `data/snip_url.db`); the file and its folder are created at app startup only, not at import. Tests keep using a temporary database.
- Tests for every change; all existing tests still pass; the three test assertions loosened by the BUG-01 seed are restored to expect 302.
- README: document the alias option, the rate limit and `DATABASE_PATH`.

## Acceptance criteria

1. AC1: Given a valid URL and an alias such as "my-link", When the client creates a link, Then the response is 201 and the code is "my-link" and the short_url ends with "/my-link".
2. AC2: Given a link created with alias "my-link", When the client requests `/my-link`, Then it redirects to the original URL.
3. AC3: Given no alias is sent, When the client creates a link, Then the code is a random 7-character code as before.
4. AC4: Given an alias that is already used by an existing link, When the client creates a link with it, Then the response is 409 with the JSON error format and a message saying the alias is taken, and the existing link is unchanged.
5. AC5: Given an alias of 3 characters and one of 30 characters, When each is used to create a link, Then both are accepted.
6. AC6: Given an alias shorter than 3 or longer than 30 characters, When the client creates a link, Then the response is 422 with the JSON error format and error code `invalid_alias`, and no link is created.
7. AC7: Given an alias containing a character other than letters, digits or hyphens (for example a space, underscore or slash), When the client creates a link, Then the response is 422 with error code `invalid_alias` and no link is created.
8. AC8: Given an alias of api, health, docs or openapi in any letter case (for example "API" or "Docs"), When the client creates a link, Then the response is 422 with error code `reserved_alias` (distinct from `invalid_alias`) and a message saying the alias is reserved, and no link is created.
9. AC9: Given a link exists with alias "MyLink", When the client creates a link with alias "mylink", Then it is accepted (aliases are case-sensitive).
10. AC10: Given a link exists with a random 7-character code, When the client creates a link with an alias equal to that code, Then the response is 409 with the alias-taken error.
11. AC11: Given the rate limit is reached, When create requests fail validation (422) or return 409, Then they still count toward the limit, and a spoofed `X-Forwarded-For` header does not change which client the request is counted against.
12. AC12: Given a client IP that has made 10 create requests in the last minute, When it makes an 11th create request, Then the response is 429 with the JSON error format and a `Retry-After` header holding a positive whole number of seconds.
13. AC13: Given a client IP that has made 10 create requests in the last minute, When it makes a create request after the minute window has passed, Then the request is accepted (tested with a controllable clock, not a real wait).
14. AC14: Given client IP A is at the limit, When client IP B creates a link, Then B's request is accepted.
15. AC15: Given a client IP is over the create limit, When it requests a redirect or the stats endpoint, Then those requests are not limited.
16. AC16: Given an existing short link, When the client requests `/{code}`, Then the response status is 302 with the original URL in the `Location` header.
17. AC17 (BUG-01 regression): Given an existing short link, When the same link is opened 3 times in a row, Then each response is 302 and the stats endpoint reports a click_count of 3. The test asserts the 302 status so it fails if 301 returns.
18. AC18: Given the app code is imported with no startup, When the import finishes, Then no database file exists at the project root or at `DATABASE_PATH`.
19. AC19: Given `DATABASE_PATH` points to a path whose folder does not exist, When the app starts, Then the folder and database file are created there and the tables exist.
20. AC20: Given `DATABASE_PATH` is not set, When the app starts, Then the database is created at `data/snip_url.db`.
21. AC21: Given the test suite runs, When tests create the app, Then they use a temporary database under `tmp_path` and no file is created in the project root or `data/`.
22. AC22: Given the README, When a reader looks for them, Then it documents the alias option (rules and 409/reserved behaviour), the rate limit (10 per minute per IP, 429, Retry-After) and the `DATABASE_PATH` setting.

## Out of scope

- User accounts or login.
- Link expiry.
- Editing or deleting links.
- A shared rate-limit store such as Redis (in-memory, single server only).
- Rate limiting of redirects or stats.
- Any change to URL validation rules.

## Assumptions

Decisions made by the human (answers to earlier open questions):

- DECIDED: invalid alias and reserved alias both return 422, with distinct error codes (`invalid_alias`, `reserved_alias`).
- DECIDED: aliases are case-sensitive; reserved words are matched case-insensitively.
- DECIDED: the request body field is `alias`.
- DECIDED: the rate limit counts all create requests, keyed on the direct connection IP; `X-Forwarded-For` is ignored.
- DECIDED: `SNIP_DB_PATH` is renamed to `DATABASE_PATH` only (default `data/snip_url.db`); the old name is dropped.
- DECIDED: an alias equal to an existing random code is taken (409).

Assumptions:

- ASSUMED (from request): "per minute" is a rolling or fixed 60-second window; either is acceptable as long as AC12 and AC13 hold.
- ASSUMED (from current code): the existing error codes and JSON error format are kept; the "alias taken" error code is chosen by the planner.
- ASSUMED: the root-level `snip_url.db` already created by the old behaviour is not deleted by this change.

## Open questions

None
