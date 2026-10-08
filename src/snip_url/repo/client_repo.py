import sqlite3


# Make sure a client row exists for the ip_hash and return its id.
def ensure_client(conn: sqlite3.Connection, ip_hash: str, now: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO api_clients "
        "(ip_hash, first_seen, last_seen, links_created, times_rate_limited) "
        "VALUES (?, ?, ?, 0, 0)",
        (ip_hash, now, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM api_clients WHERE ip_hash = ?", (ip_hash,)
    ).fetchone()
    return int(row["id"])


# Add one to links_created and update last_seen.
def add_link_created(conn: sqlite3.Connection, client_id: int, now: str) -> None:
    conn.execute(
        "UPDATE api_clients SET links_created = links_created + 1, last_seen = ? "
        "WHERE id = ?",
        (now, client_id),
    )
    conn.commit()


# Add one to times_rate_limited, creating the client row if missing.
def add_rate_limited(conn: sqlite3.Connection, ip_hash: str, now: str) -> None:
    conn.execute(
        "INSERT INTO api_clients "
        "(ip_hash, first_seen, last_seen, links_created, times_rate_limited) "
        "VALUES (?, ?, ?, 0, 1) "
        "ON CONFLICT(ip_hash) DO UPDATE SET "
        "times_rate_limited = times_rate_limited + 1, last_seen = excluded.last_seen",
        (ip_hash, now, now),
    )
    conn.commit()
