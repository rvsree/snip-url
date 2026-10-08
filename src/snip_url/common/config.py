import os

DEFAULT_IP_HASH_SALT: str = "dev-only-salt-change-me"


class Settings:
    """A plain settings holder."""

    db_path: str
    base_url: str
    ip_hash_salt: str

    # Store the database path, base url and ip hash salt.
    def __init__(
        self,
        db_path: str,
        base_url: str,
        ip_hash_salt: str = DEFAULT_IP_HASH_SALT,
    ) -> None:
        self.db_path = db_path
        self.base_url = base_url
        self.ip_hash_salt = ip_hash_salt


# Build Settings from env vars, with defaults, without a trailing slash on base_url.
def load_settings() -> Settings:
    db_path = os.environ.get("DATABASE_PATH", "data/snip_url.db")
    base_url = os.environ.get("SNIP_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    salt = os.environ.get("IP_HASH_SALT", "")
    if salt == "":
        salt = DEFAULT_IP_HASH_SALT
    return Settings(db_path=db_path, base_url=base_url, ip_hash_salt=salt)
