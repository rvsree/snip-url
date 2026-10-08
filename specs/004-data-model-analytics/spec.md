# Spec: Data model, analytics and seed data (004)

## Summary

This brownfield change renames the two existing tables (links to short_links, clicks to click_events), adds new columns, and adds three new tables (link_visitors, api_clients, daily_link_stats). It records visitor and API-client activity using salted IP hashes only, and adds two read-only analytics endpoints. It also adds a deterministic, re-runnable seed script and a reference schema.sql, with tests and README updates.

## In scope

- Startup migration: a database made by the current version has its tables renamed with no data loss.
- New columns on short_links: is_custom_alias, created_by_client, last_clicked_at.
- New columns on click_events: visitor, user_agent, referrer.
- New tables: link_visitors, api_clients, daily_link_stats (fields as listed in request.md).
- Salted IP hashing using the IP_HASH_SALT setting, with a fixed default for local development.
- Recording on redirect: click_events row, visitor upsert, last_clicked_at, daily_link_stats update.
- Recording on link creation and on rate limiting: api_clients upsert, links created count, times rate-limited count.
- Endpoint: analytics for one short code (per-day clicks and unique visitors for the last N days, plus totals).
- Endpoint: analytics summary (top 10 links by clicks over the last N days, plus totals for links, clicks, visitors, API clients).
- db_scripts/seed_data.py and db_scripts/schema.sql.
- Tests for every change; existing tests still pass; coverage at least 80%.
- README: the 5 tables, the analytics endpoints, how to run the seed script.

## Acceptance criteria

1. AC1. Given a database created by the current version that holds links and clicks rows, When the app starts, Then the tables are named short_links and click_events, every old row is still present with the same values, and no table named links or clicks remains.
2. AC2. Given a database already using the new names, When the app starts again, Then startup succeeds and no data changes.
3. AC3. Given a fresh empty database, When the app starts, Then all 5 tables exist (short_links, click_events, link_visitors, api_clients, daily_link_stats) with the columns listed in request.md.
4. AC4. Given a short link is created with a custom alias, When the row is read, Then is_custom_alias is true; Given it is created without an alias, Then is_custom_alias is false.
5. AC5. Given a link is created by a caller, When the row is read, Then created_by_client points to an api_clients row for that caller's hashed IP, and that row's links created count is increased by 1 and last seen is updated.
6. AC6. Given a caller is rejected by the rate limiter, When the response is 429, Then the caller's api_clients row has times rate-limited increased by 1.
7. AC7. Given a valid short code, When it is opened, Then the response is still a 302 to the original URL and a click_events row exists with visitor, user_agent (from the User-Agent header) and referrer (from the Referer header); missing headers are stored as empty/null.
8. AC8. Given a visitor opens links, When the visit is recorded, Then link_visitors has one row per hashed IP, with visit count incremented, last seen updated, and latest user agent replaced on each visit.
9. AC9. Given a link is opened, When the redirect finishes, Then short_links.last_clicked_at is set to the time of that click.
10. AC10. Given a link is opened, When the redirect finishes, Then the daily_link_stats row for that link and today has click count increased by 1, and unique visitors increased by 1 only if this visitor had no earlier click on that link that day.
11. AC11. Given any request that creates or opens links, When the database is inspected, Then no column in any table contains the plain-text IP address; stored values equal a salted hash of the IP using IP_HASH_SALT.
12. AC12. Given IP_HASH_SALT is unset, When the app runs, Then a fixed default salt is used; Given it is set to a different value, Then the same IP produces a different hash.
13. AC13. Given a known code with clicks on several days, When GET /api/analytics/links/{code} is called with no days parameter, Then it returns one entry per day for the last 7 days (days with no clicks show 0), each with clicks and unique visitors, plus total clicks and total unique visitors.
14. AC14. Given a known code, When GET /api/analytics/links/{code}?days=N is called with N between 1 and 90, Then exactly N days are returned.
15. AC15. Given an unknown code, When GET /api/analytics/links/{code} is called, Then the response is 404 with the standard JSON error shape.
16. AC16. Given a days value greater than 90, less than 1, or not a whole number, When either analytics endpoint is called, Then the response is 422 with the standard JSON error body.
17. AC17. Given several links with clicks, When GET /api/analytics/summary?days=N is called (default 7, maximum 90), Then it returns at most 10 links ordered by clicks over the last N days descending, plus total links, total clicks, total visitors and total API clients, all limited to the last N days (see Assumptions).
18. AC18. Given an empty database, When GET /api/analytics/summary is called, Then it returns an empty top list and all totals equal 0.
19. AC19. Given an empty database at DATABASE_PATH, When db_scripts/seed_data.py is run, Then it creates 30 short links (at least 5 with custom aliases), exactly 300 click events spread over the last 14 days, exactly 40 visitors, 5 API clients, and daily_link_stats rows whose click counts and unique visitors match the click events.
20. AC20. Given the seed script is run on two different empty databases, When the contents are compared, Then the seeded data is identical (fixed random seed).
21. AC21. Given the seed script has already run, When it is run again, Then no rows are added and none are deleted, and it still prints a count per table.
22. AC22. Given the seed script finishes, When its output is read, Then it prints a row count for each of the 5 tables.
23. AC23. Given db_scripts/schema.sql, When it is read, Then it defines the 5 tables as SQL, and (reference only) it is not used by the app at startup.
24. AC24. Given the full test suite, When it is run, Then all pre-existing tests pass and coverage is at least 80%.
25. AC25. Given the README, When it is read, Then it describes the 5 tables, both analytics endpoints, and how to run the seed script.

## Out of scope

- Dashboards or UI.
- Kafka or background jobs.
- Authentication.
- Data retention jobs.
- Any change to existing endpoint behavior beyond recording the new data (create, redirect and stats keep their current responses).
- The app reading schema.sql (it is reference only).

## Assumptions

- ASSUMPTION (identity): a visitor and an API client are each identified by the salted hash of the direct client IP (same source as the existing rate limiter, ignoring X-Forwarded-For).
- ASSUMPTION (migration of old rows): existing rows get empty/null values for new columns (no created_by_client, no visitor, no user_agent, no referrer, last_clicked_at null), and is_custom_alias is false.
- ASSUMPTION (days): "day" means a UTC calendar day; "last N days" includes today.
- ASSUMPTION (rate-limit counting): times rate-limited is counted only for rejections of link creation, the only rate-limited action today.
- ASSUMPTION (seed tables): the seed script creates missing tables itself if the database is new.
- ASSUMPTION (seed idempotency): re-runs detect existing seed rows by stable keys (for example fixed short codes), so nothing is added or removed.
- ASSUMPTION (hash): the hash algorithm is a standard salted SHA-256; the exact choice is a plan detail.
- DECISION (human): paths are GET /api/analytics/links/{code}?days=N and GET /api/analytics/summary?days=N; parameter name is days, default 7, max 90; invalid values return 422 with the standard error body.
- DECISION (human): summary totals are limited to the last N days, not all-time.
- DECISION (human): migrated old rows keep empty visitor/client data and is_custom_alias=false; no backfill.
- DECISION (human): the seed produces exactly 300 clicks and 40 visitors.
- ASSUMPTION (summary totals meaning): within the last N days, total links = links created in the window, total clicks = click events in the window, total visitors = distinct visitors with a click in the window, total API clients = clients whose last seen is in the window.
- ASSUMPTION (response shapes): analytics responses are JSON; field names are decided in the plan.

## Open questions

None
