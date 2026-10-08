"""Deterministic, re-runnable seed data for snip-url.

Run: uv run python db_scripts/seed_data.py
"""

import random
import sqlite3
from datetime import date, datetime, time, timedelta, timezone

from snip_url.common.config import load_settings
from snip_url.repo.db import get_connection, init_db
from snip_url.services.privacy import hash_ip

SEED_RANDOM = 20260101
TABLES: tuple[str, ...] = (
    "short_links",
    "click_events",
    "link_visitors",
    "api_clients",
    "daily_link_stats",
)
LINK_COUNT = 25
ALIAS_COUNT = 5
CLICK_COUNT = 300
VISITOR_COUNT = 40
CLIENT_COUNT = 5
DAYS_BACK = 14
USER_AGENTS = ("Mozilla/5.0 (Windows)", "Mozilla/5.0 (Macintosh)", "curl/8.0")
REFERRERS = (None, "https://news.example.com/", "https://social.example.com/post/1")


# Return the 30 fixed link specs: 25 random-style codes and 5 custom aliases.
def build_link_specs() -> list[dict]:
    specs: list[dict] = []
    for number in range(1, LINK_COUNT + 1):
        code = "seed" + str(number).zfill(2)
        specs.append({"code": code, "is_custom_alias": False, "client_index": len(specs) % CLIENT_COUNT})
    for number in range(1, ALIAS_COUNT + 1):
        code = "promo-" + str(number)
        specs.append({"code": code, "is_custom_alias": True, "client_index": len(specs) % CLIENT_COUNT})
    for spec in specs:
        spec["original_url"] = "https://example.com/page/" + spec["code"]
    return specs


# Return an ISO UTC timestamp for a date and a second of the day.
def make_timestamp(day: date, seconds: int) -> str:
    moment = datetime.combine(day, time(0, 0), tzinfo=timezone.utc)
    return (moment + timedelta(seconds=seconds)).isoformat()


# Return exactly 300 planned clicks using only the given random generator.
def build_click_plan(rng: random.Random, today: date) -> list[dict]:
    plan: list[dict] = []
    for index in range(CLICK_COUNT):
        visitor = index
        if index >= VISITOR_COUNT:
            visitor = rng.randrange(VISITOR_COUNT)
        link_index = rng.randrange(LINK_COUNT + ALIAS_COUNT)
        offset = rng.randrange(DAYS_BACK)
        seconds = rng.randrange(86400)
        plan.append(
            {
                "index": index,
                "visitor": visitor,
                "link_index": link_index,
                "day_offset": offset,
                "clicked_at": make_timestamp(today - timedelta(days=offset), seconds),
                "user_agent": USER_AGENTS[visitor % len(USER_AGENTS)],
                "referrer": REFERRERS[rng.randrange(len(REFERRERS))],
            }
        )
    return plan


# Return True if the seed link seed01 is already stored.
def seed_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT 1 FROM short_links WHERE code = 'seed01'").fetchone()
    if row is None:
        return False
    return True


# Return the clicks ordered by time (ties by plan index).
def sort_clicks(plan: list[dict]) -> list[dict]:
    keyed: list[tuple] = []
    for click in plan:
        keyed.append((click["clicked_at"], click["index"], click))
    keyed.sort(key=lambda_free_key)
    result: list[dict] = []
    for item in keyed:
        result.append(item[2])
    return result


# Sort key for keyed clicks: time then plan index.
def lambda_free_key(item: tuple) -> tuple:
    return (item[0], item[1])


# Insert the 5 api clients with the number of links assigned to each.
def insert_clients(conn: sqlite3.Connection, salt: str, specs: list[dict], created_at: str) -> None:
    for client_index in range(CLIENT_COUNT):
        assigned = 0
        for spec in specs:
            if spec["client_index"] == client_index:
                assigned = assigned + 1
        ip_hash = hash_ip("192.168.1." + str(client_index + 1), salt)
        conn.execute(
            "INSERT INTO api_clients (id, ip_hash, first_seen, last_seen, links_created, times_rate_limited) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (client_index + 1, ip_hash, created_at, created_at, assigned),
        )


# Insert the 40 visitors with counts and times computed from the sorted clicks.
def insert_visitors(conn: sqlite3.Connection, salt: str, clicks: list[dict]) -> None:
    info: dict[int, dict] = {}
    for click in clicks:
        entry = info.get(click["visitor"])
        if entry is None:
            entry = {"count": 0, "first": click["clicked_at"], "last": "", "agent": ""}
            info[click["visitor"]] = entry
        entry["count"] = entry["count"] + 1
        entry["last"] = click["clicked_at"]
        entry["agent"] = click["user_agent"]
    for visitor in range(VISITOR_COUNT):
        entry = info[visitor]
        ip_hash = hash_ip("10.0.0." + str(visitor + 1), salt)
        conn.execute(
            "INSERT INTO link_visitors (id, ip_hash, user_agent, first_seen, last_seen, visit_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (visitor + 1, ip_hash, entry["agent"], entry["first"], entry["last"], entry["count"]),
        )


# Insert the 30 links with their last click time.
def insert_links(conn: sqlite3.Connection, specs: list[dict], clicks: list[dict], created_at: str) -> None:
    last_click: dict[int, str] = {}
    for click in clicks:
        last_click[click["link_index"]] = click["clicked_at"]
    for link_index in range(len(specs)):
        spec = specs[link_index]
        flag = 0
        if spec["is_custom_alias"]:
            flag = 1
        conn.execute(
            "INSERT INTO short_links (code, original_url, created_at, is_custom_alias, created_by_client, last_clicked_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (spec["code"], spec["original_url"], created_at, flag, spec["client_index"] + 1, last_click.get(link_index)),
        )


# Insert click events (chronological) and the daily stats computed from them.
def insert_clicks_and_stats(conn: sqlite3.Connection, specs: list[dict], clicks: list[dict]) -> None:
    daily: dict[tuple, dict] = {}
    for click in clicks:
        code = specs[click["link_index"]]["code"]
        conn.execute(
            "INSERT INTO click_events (code, clicked_at, visitor, user_agent, referrer) VALUES (?, ?, ?, ?, ?)",
            (code, click["clicked_at"], click["visitor"] + 1, click["user_agent"], click["referrer"]),
        )
        key = (code, click["clicked_at"][:10])
        entry = daily.get(key)
        if entry is None:
            entry = {"clicks": 0, "visitors": set()}
            daily[key] = entry
        entry["clicks"] = entry["clicks"] + 1
        entry["visitors"].add(click["visitor"])
    for key, entry in daily.items():
        conn.execute(
            "INSERT INTO daily_link_stats (code, day, click_count, unique_visitors) VALUES (?, ?, ?, ?)",
            (key[0], key[1], entry["clicks"], len(entry["visitors"])),
        )


# Insert all seed rows in one transaction.
def insert_seed(conn: sqlite3.Connection, salt: str, today: date) -> None:
    rng = random.Random(SEED_RANDOM)
    specs = build_link_specs()
    clicks = sort_clicks(build_click_plan(rng, today))
    created_at = make_timestamp(today - timedelta(days=DAYS_BACK - 1), 0)
    try:
        insert_clients(conn, salt, specs, created_at)
        insert_visitors(conn, salt, clicks)
        insert_links(conn, specs, clicks, created_at)
        insert_clicks_and_stats(conn, specs, clicks)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# Return the row count of each table.
def count_tables(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in TABLES:
        row = conn.execute("SELECT COUNT(*) AS total FROM " + table).fetchone()
        counts[table] = int(row["total"])
    return counts


# Create missing tables, insert the seed once, and return the table counts.
def run_seed(db_path: str, salt: str, today: date | None = None) -> dict[str, int]:
    if today is None:
        today = datetime.now(timezone.utc).date()
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        if not seed_exists(conn):
            insert_seed(conn, salt, today)
        return count_tables(conn)
    finally:
        conn.close()


# Seed the configured database and print one count line per table.
def main() -> None:
    settings = load_settings()
    counts = run_seed(settings.db_path, settings.ip_hash_salt)
    for table in TABLES:
        print(table + ": " + str(counts[table]))


if __name__ == "__main__":
    main()
