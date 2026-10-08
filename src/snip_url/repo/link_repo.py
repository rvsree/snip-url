import sqlite3

INSERT_LINK_SQL = (
    "INSERT INTO short_links "
    "(code, original_url, created_at, is_custom_alias, created_by_client) "
    "VALUES (?, ?, ?, ?, ?)"
)


# Return True if a link with this code exists.
def code_exists(conn: sqlite3.Connection, code: str) -> bool:
    row = conn.execute("SELECT 1 FROM short_links WHERE code = ?", (code,)).fetchone()
    if row is None:
        return False
    return True


# Insert a link row and commit.
def insert_link(
    conn: sqlite3.Connection,
    code: str,
    original_url: str,
    created_at: str,
    is_custom_alias: bool = False,
    created_by_client: int | None = None,
) -> None:
    flag = 0
    if is_custom_alias:
        flag = 1
    conn.execute(
        INSERT_LINK_SQL,
        (code, original_url, created_at, flag, created_by_client),
    )
    conn.commit()


# Insert a link row; return False if the code already exists.
def try_insert_link(
    conn: sqlite3.Connection,
    code: str,
    original_url: str,
    created_at: str,
    is_custom_alias: bool = False,
    created_by_client: int | None = None,
) -> bool:
    flag = 0
    if is_custom_alias:
        flag = 1
    try:
        conn.execute(
            INSERT_LINK_SQL,
            (code, original_url, created_at, flag, created_by_client),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    return True


# Return the link row as a dict or None.
def get_link(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute(
        "SELECT code, original_url, created_at, is_custom_alias, "
        "created_by_client, last_clicked_at FROM short_links WHERE code = ?",
        (code,),
    ).fetchone()
    if row is None:
        return None
    return {
        "code": row["code"],
        "original_url": row["original_url"],
        "created_at": row["created_at"],
        "is_custom_alias": bool(row["is_custom_alias"]),
        "created_by_client": row["created_by_client"],
        "last_clicked_at": row["last_clicked_at"],
    }


# Insert a click row (no commit).
def insert_click(
    conn: sqlite3.Connection,
    code: str,
    clicked_at: str,
    visitor: int | None = None,
    user_agent: str | None = None,
    referrer: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO click_events (code, clicked_at, visitor, user_agent, referrer) "
        "VALUES (?, ?, ?, ?, ?)",
        (code, clicked_at, visitor, user_agent, referrer),
    )


# Return number of clicks for the code.
def count_clicks(conn: sqlite3.Connection, code: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM click_events WHERE code = ?", (code,)
    ).fetchone()
    return int(row["total"])


# Set last_clicked_at for the code (no commit).
def set_last_clicked(conn: sqlite3.Connection, code: str, clicked_at: str) -> None:
    conn.execute(
        "UPDATE short_links SET last_clicked_at = ? WHERE code = ?",
        (clicked_at, code),
    )


# Return True if this visitor already clicked this code on the day.
def visitor_clicked_on_day(
    conn: sqlite3.Connection, code: str, visitor: int, day: str
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM click_events WHERE code = ? AND visitor = ? "
        "AND substr(clicked_at, 1, 10) = ? LIMIT 1",
        (code, visitor, day),
    ).fetchone()
    if row is None:
        return False
    return True
