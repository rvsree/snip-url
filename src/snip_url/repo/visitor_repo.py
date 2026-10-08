import sqlite3


# Insert or update the visitor row by ip_hash and return its id (no commit).
def upsert_visitor(
    conn: sqlite3.Connection, ip_hash: str, user_agent: str, now: str
) -> int:
    conn.execute(
        "INSERT INTO link_visitors (ip_hash, user_agent, first_seen, last_seen, visit_count) "
        "VALUES (?, ?, ?, ?, 1) "
        "ON CONFLICT(ip_hash) DO UPDATE SET "
        "visit_count = visit_count + 1, last_seen = excluded.last_seen, "
        "user_agent = excluded.user_agent",
        (ip_hash, user_agent, now, now),
    )
    row = conn.execute(
        "SELECT id FROM link_visitors WHERE ip_hash = ?", (ip_hash,)
    ).fetchone()
    return int(row["id"])
