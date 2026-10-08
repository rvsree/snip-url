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
ALIAS_MIN_LENGTH = 3
ALIAS_MAX_LENGTH = 30
ALIAS_CHARS = string.ascii_letters + string.digits + "-"
RESERVED_ALIASES = ("api", "health", "docs", "openapi")
ALIAS_RULE_MESSAGE = (
    "Alias must be 3 to 30 characters: letters, digits and hyphens only"
)


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


# Raise AppError(422) for a bad or reserved alias; else return it.
def validate_alias(alias: str) -> str:
    if len(alias) < ALIAS_MIN_LENGTH or len(alias) > ALIAS_MAX_LENGTH:
        raise AppError(422, "invalid_alias", ALIAS_RULE_MESSAGE)
    for char in alias:
        if char not in ALIAS_CHARS:
            raise AppError(422, "invalid_alias", ALIAS_RULE_MESSAGE)
    if alias.lower() in RESERVED_ALIASES:
        raise AppError(422, "reserved_alias", "Alias is reserved")
    return alias


# Store the link under the alias; AppError(409, alias_taken) if the code exists.
def create_alias_link(
    conn: sqlite3.Connection, base_url: str, valid_url: str, alias: str
) -> CreateLinkResponse:
    created_at = utc_now_iso()
    inserted = link_repo.try_insert_link(conn, alias, valid_url, created_at)
    if not inserted:
        raise AppError(409, "alias_taken", "Alias is already taken")
    return CreateLinkResponse(
        code=alias,
        short_url=base_url + "/" + alias,
        original_url=valid_url,
        created_at=created_at,
    )


# Validate, then store under the alias or a unique random code; return the response.
def create_link(
    conn: sqlite3.Connection,
    base_url: str,
    url: str | None,
    alias: str | None = None,
) -> CreateLinkResponse:
    valid_url = validate_url(url)
    if alias is not None:
        valid_alias = validate_alias(alias)
        return create_alias_link(conn, base_url, valid_url, valid_alias)
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
