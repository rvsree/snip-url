import sqlite3
from datetime import datetime, timezone

from snip_url.common.errors import AppError
from snip_url.repo import client_repo, db, link_repo, stats_repo, visitor_repo
from snip_url.services.privacy import hash_ip
from snip_url.services.rate_limiter import RateLimiter


# Return the user agent for the visitor row; None becomes an empty string.
def visitor_user_agent(user_agent: str | None) -> str:
    if user_agent is None:
        return ""
    return user_agent


# Save click event, visitor, last_clicked_at and daily stat in one transaction.
def record_click(
    conn: sqlite3.Connection,
    code: str,
    now: str,
    ip_hash: str,
    user_agent: str | None,
    referrer: str | None,
) -> None:
    try:
        agent = visitor_user_agent(user_agent)
        visitor_id = visitor_repo.upsert_visitor(conn, ip_hash, agent, now)
        day = now[:10]
        seen = link_repo.visitor_clicked_on_day(conn, code, visitor_id, day)
        link_repo.insert_click(conn, code, now, visitor_id, user_agent, referrer)
        link_repo.set_last_clicked(conn, code, now)
        stats_repo.bump_daily_stat(conn, code, day, not seen)
        db.commit(conn)
    except Exception:
        db.rollback(conn)
        raise


# Count one created link for the client.
def record_link_created(conn: sqlite3.Connection, client_id: int, now: str) -> None:
    client_repo.add_link_created(conn, client_id, now)


# Return the api client id for the ip, or None when there is no ip.
def client_id_for(
    conn: sqlite3.Connection, client_ip: str | None, salt: str, now: str
) -> int | None:
    if client_ip is None:
        return None
    return client_repo.ensure_client(conn, hash_ip(client_ip, salt), now)


# Apply the create limit; count a rate-limited hit and re-raise the same error.
def enforce_create_limit(
    conn: sqlite3.Connection, limiter: RateLimiter, client_ip: str, salt: str
) -> None:
    try:
        limiter.enforce(client_ip)
    except AppError as error:
        if error.code == "rate_limited":
            now = datetime.now(timezone.utc).isoformat()
            client_repo.add_rate_limited(conn, hash_ip(client_ip, salt), now)
        raise
