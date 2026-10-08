import secrets
import sqlite3
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from snip_url.common.errors import AppError
from snip_url.models.link import CreateLinkResponse, LinkStatsResponse
from snip_url.repo import link_repo

MAX_URL_LENGTH = 2048
CODE_LENGTH = 7
ALPHABET = string.ascii_letters + string.digits
MAX_CODE_ATTEMPTS = 10


# Raise AppError(422, invalid_url) if the url is not acceptable; else return it.
def validate_url(url: str | None) -> str:
    if url is None or url.strip() == "":
        raise AppError(422, "invalid_url", "URL is required")
    if len(url) > MAX_URL_LENGTH:
        raise AppError(422, "invalid_url", "URL is longer than 2048 characters")
    try:
        parsed = urlparse(url)
        host = parsed.netloc
    except ValueError:
        raise AppError(422, "invalid_url", "URL is not valid")
    if parsed.scheme not in ("http", "https"):
        raise AppError(422, "invalid_url", "URL must start with http or https")
    if host == "" or parsed.hostname is None:
        raise AppError(422, "invalid_url", "URL must have a host")
    return url


# Return a random 7-char base62 code.
def generate_code() -> str:
    code = ""
    for _ in range(CODE_LENGTH):
        code = code + secrets.choice(ALPHABET)
    return code


# Return current UTC time as an ISO 8601 string.
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Pick a code not in the db, or raise a 500 error after 10 tries.
def make_unique_code(conn: sqlite3.Connection) -> str:
    for _ in range(MAX_CODE_ATTEMPTS):
        code = generate_code()
        if not link_repo.code_exists(conn, code):
            return code
    raise AppError(500, "code_generation_failed", "Could not generate a unique code")


# Validate, generate a unique code, store, and return the response.
def create_link(
    conn: sqlite3.Connection, base_url: str, url: str | None
) -> CreateLinkResponse:
    valid_url = validate_url(url)
    code = make_unique_code(conn)
    created_at = utc_now_iso()
    link_repo.insert_link(conn, code, valid_url, created_at)
    return CreateLinkResponse(
        code=code,
        short_url=base_url + "/" + code,
        original_url=valid_url,
        created_at=created_at,
    )


# Look up the code, record a click, and return the original url.
def resolve_and_record_click(conn: sqlite3.Connection, code: str) -> str:
    link = link_repo.get_link(conn, code)
    if link is None:
        raise AppError(404, "link_not_found", "Short code not found")
    link_repo.insert_click(conn, code, utc_now_iso())
    return link["original_url"]


# Return stats for the code or raise a 404 error.
def get_stats(conn: sqlite3.Connection, code: str) -> LinkStatsResponse:
    link = link_repo.get_link(conn, code)
    if link is None:
        raise AppError(404, "link_not_found", "Short code not found")
    total = link_repo.count_clicks(conn, code)
    return LinkStatsResponse(
        code=link["code"],
        original_url=link["original_url"],
        created_at=link["created_at"],
        click_count=total,
    )
