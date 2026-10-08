# Spec: Core URL shortener (S1)

## 1. Summary

A small HTTP service that turns a long http/https URL into a 7-character short code and a full short URL. Opening the short URL redirects (302) to the original URL and records a click with its time. Users can read stats for a code (original URL, creation time, total clicks). Data is stored in SQLite so it survives restarts, and a health endpoint reports that the service is up.

## 2. In scope

- Create a short link from a long URL; return the short code and the full short URL.
- Validate the URL: scheme must be http or https, length at most 2048 characters; reject anything else with a clear error.
- Redirect from the short URL to the original URL with HTTP 302.
- Return 404 with a clear error for an unknown short code.
- Record every successful redirect as a click with its time.
- Stats endpoint for a short code: original URL, created time, total click count.
- Persist links and clicks in SQLite.
- Health endpoint.
- Errors returned as JSON in the constitution format: `{"error": {"code": "...", "message": "..."}}`.

## 3. Acceptance criteria

1. AC1: Given a valid http or https URL of at most 2048 characters, when the user submits it to create a short link, then the response contains a short code of exactly 7 characters (letters and digits only) and the full short URL ending in that code.
2. AC2: Given a URL whose scheme is not http or https (for example `ftp://x.com` or `javascript:alert(1)`), when the user submits it, then the request is rejected with a 4xx status and a JSON error with a clear message, and nothing is stored.
3. AC3: Given a URL longer than 2048 characters, when the user submits it, then it is rejected with a 4xx status and a JSON error with a clear message, and nothing is stored.
4. AC4: Given a missing or empty URL value, when the user submits it, then it is rejected with a 4xx status and a JSON error with a clear message.
5. AC5: Given an existing short code, when the user opens its short URL, then the response is HTTP 302 with a Location header equal to the original URL.
6. AC6: Given an unknown short code, when the user opens its short URL, then the response is 404 with a JSON error containing a clear message.
7. AC7: Given an existing short code, when the short URL is opened N times, then N click records exist, each with a time.
8. AC8: Given an unknown short code, when the user opens its short URL, then no click is recorded.
9. AC9: Given an existing short code, when the user requests its stats, then the response contains the original URL, the creation time, and the total click count (0 for a new link, N after N redirects).
10. AC10: Given an unknown short code, when the user requests its stats, then the response is 404 with a JSON error containing a clear message.
11. AC11: Given a link and clicks created in a SQLite database, when the application is restarted against the same database file, then the link still redirects and its stats still show the same click count.
12. AC12: Given the service is running, when the user calls the health endpoint, then it returns 200 with a body indicating the service is up.
13. AC13: Given a short code is generated that already exists, when a link is created, then a different unused code is used, so two links never share a code.

## 4. Out of scope

- User accounts and authentication.
- Custom aliases.
- Link expiry.
- Editing or deleting links.
- Listing links.
- Rate limiting, caching, background click queue, Docker, deployment.

## 5. Assumptions

- Assumption (code format): the 7 characters are random, drawn from a-z, A-Z, 0-9 (base62), per the project brief.
- Assumption (duplicate URLs): submitting the same long URL twice creates two separate short codes. The request does not ask for de-duplication.
- Assumption (endpoints): the exact paths are chosen in the plan (for example POST to create, GET `/{code}` to redirect, GET stats and health under clear paths). The request does not name them.
- Assumption (base URL): the "full short URL" is built from a configurable base URL setting (default local, e.g. `http://localhost:8000`).
- Assumption (create status): a successful create returns 201.
- Assumption (timestamps): times are stored and returned in UTC, ISO 8601.
- Assumption (code matching): short codes are case-sensitive.
- Assumption (invalid input status): validation failures return 422 or 400; the plan picks one and uses it consistently.

## 6. Open questions

None
