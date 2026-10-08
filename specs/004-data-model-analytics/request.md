# Request: Data model, analytics and seed data (S4)

Type: Brownfield (schema refactor, enhancement, seed data, test and doc improvement) on the S2 code

## Data model

1. Rename the tables to clear two-word names: links -> short_links, clicks -> click_events.
   A database created by the current version must keep working: on startup, old tables are renamed and no data is lost.
2. Add columns:
   - short_links: is_custom_alias (yes/no), created_by_client (link to api_clients), last_clicked_at.
   - click_events: visitor (link to link_visitors), user_agent, referrer.
3. New table link_visitors: one row per visitor (people who open short links): hashed IP, latest user agent, first seen, last seen, visit count.
4. New table api_clients: one row per API caller (who creates links): hashed IP, first seen, last seen, links created, times rate-limited.
5. New table daily_link_stats: one row per short link per day: click count and unique visitors, updated on every redirect.
6. Privacy: an IP address is never stored as plain text, only as a salted hash. The salt comes from the IP_HASH_SALT setting, with a fixed default for local development.

## Analytics endpoints

7. Analytics for one short code: clicks and unique visitors per day for the last N days (default 7, maximum 90), plus totals. Unknown code returns 404.
8. Analytics summary: top 10 short links by clicks over the last N days, plus totals for links, clicks, visitors and API clients.

## Seed data

9. db_scripts/seed_data.py loads sample data into the database at DATABASE_PATH:
   - 30 short links (at least 5 with custom aliases), about 300 clicks spread over the last 14 days, about 40 visitors, 5 API clients, and daily_link_stats that match the clicks.
   - Same data on every machine (fixed random seed).
   - Re-runnable: running it again adds nothing and deletes nothing.
   - Prints a count per table when done.
10. db_scripts/schema.sql: the 5 tables as SQL, for reviewers (reference only; the app creates the tables).

## Tests and docs

11. Every change above has tests. All existing tests still pass. Coverage at least 80%.
12. README: the 5 tables, the analytics endpoints, and how to run the seed script.

Not needed now: dashboards or UI, Kafka or background jobs, authentication, data retention jobs.
