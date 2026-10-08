import sqlite3


# Add one click to the (code, day) row; add a unique visitor when new_visitor (no commit).
def bump_daily_stat(
    conn: sqlite3.Connection, code: str, day: str, new_visitor: bool
) -> None:
    unique = 0
    if new_visitor:
        unique = 1
    conn.execute(
        "INSERT INTO daily_link_stats (code, day, click_count, unique_visitors) "
        "VALUES (?, ?, 1, ?) "
        "ON CONFLICT(code, day) DO UPDATE SET "
        "click_count = click_count + 1, "
        "unique_visitors = unique_visitors + excluded.unique_visitors",
        (code, day, unique),
    )


# Return daily stat rows for the code from start_day on, oldest first.
def get_daily_stats(conn: sqlite3.Connection, code: str, start_day: str) -> list[dict]:
    rows = conn.execute(
        "SELECT day, click_count, unique_visitors FROM daily_link_stats "
        "WHERE code = ? AND day >= ? ORDER BY day",
        (code, start_day),
    ).fetchall()
    result: list[dict] = []
    for row in rows:
        result.append(
            {
                "day": row["day"],
                "click_count": int(row["click_count"]),
                "unique_visitors": int(row["unique_visitors"]),
            }
        )
    return result


# Return distinct visitors of the code in the window.
def count_window_visitors_for_code(
    conn: sqlite3.Connection, code: str, start_day: str
) -> int:
    row = conn.execute(
        "SELECT COUNT(DISTINCT visitor) AS total FROM click_events "
        "WHERE code = ? AND substr(clicked_at, 1, 10) >= ?",
        (code, start_day),
    ).fetchone()
    return int(row["total"])


# Return the most clicked links in the window.
def top_links(conn: sqlite3.Connection, start_day: str, limit: int) -> list[dict]:
    rows = conn.execute(
        "SELECT s.code AS code, s.original_url AS original_url, COUNT(*) AS clicks "
        "FROM click_events c JOIN short_links s ON s.code = c.code "
        "WHERE substr(c.clicked_at, 1, 10) >= ? "
        "GROUP BY s.code, s.original_url ORDER BY clicks DESC, s.code ASC LIMIT ?",
        (start_day, limit),
    ).fetchall()
    result: list[dict] = []
    for row in rows:
        result.append(
            {
                "code": row["code"],
                "original_url": row["original_url"],
                "clicks": int(row["clicks"]),
            }
        )
    return result


# Return the number of links created in the window.
def count_links_since(conn: sqlite3.Connection, start_day: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM short_links WHERE substr(created_at, 1, 10) >= ?",
        (start_day,),
    ).fetchone()
    return int(row["total"])


# Return the number of clicks in the window.
def count_clicks_since(conn: sqlite3.Connection, start_day: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM click_events WHERE substr(clicked_at, 1, 10) >= ?",
        (start_day,),
    ).fetchone()
    return int(row["total"])


# Return the number of distinct visitors with a click in the window.
def count_visitors_since(conn: sqlite3.Connection, start_day: str) -> int:
    row = conn.execute(
        "SELECT COUNT(DISTINCT visitor) AS total FROM click_events "
        "WHERE substr(clicked_at, 1, 10) >= ?",
        (start_day,),
    ).fetchone()
    return int(row["total"])


# Return the number of api clients last seen in the window.
def count_clients_since(conn: sqlite3.Connection, start_day: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM api_clients WHERE substr(last_seen, 1, 10) >= ?",
        (start_day,),
    ).fetchone()
    return int(row["total"])
