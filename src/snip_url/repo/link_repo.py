import sqlite3


# Return True if a link with this code exists.
def code_exists(conn: sqlite3.Connection, code: str) -> bool:
    row = conn.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone()
    if row is None:
        return False
    return True


# Insert a link row and commit.
def insert_link(
    conn: sqlite3.Connection, code: str, original_url: str, created_at: str
) -> None:
    conn.execute(
        "INSERT INTO links (code, original_url, created_at) VALUES (?, ?, ?)",
        (code, original_url, created_at),
    )
    conn.commit()


# Return the link row as a dict or None.
def get_link(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute(
        "SELECT code, original_url, created_at FROM links WHERE code = ?",
        (code,),
    ).fetchone()
    if row is None:
        return None
    return {
        "code": row["code"],
        "original_url": row["original_url"],
        "created_at": row["created_at"],
    }


# Insert a click row and commit.
def insert_click(conn: sqlite3.Connection, code: str, clicked_at: str) -> None:
    conn.execute(
        "INSERT INTO clicks (code, clicked_at) VALUES (?, ?)",
        (code, clicked_at),
    )
    conn.commit()


# Return number of clicks for the code.
def count_clicks(conn: sqlite3.Connection, code: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM clicks WHERE code = ?", (code,)
    ).fetchone()
    return int(row["total"])
