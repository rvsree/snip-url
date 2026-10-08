import os


class Settings:
    """A plain settings holder."""

    db_path: str
    base_url: str

    # Store the database path and base url.
    def __init__(self, db_path: str, base_url: str) -> None:
        self.db_path = db_path
        self.base_url = base_url


# Build Settings from env vars, with defaults, without a trailing slash on base_url.
def load_settings() -> Settings:
    db_path = os.environ.get("DATABASE_PATH", "data/snip_url.db")
    base_url = os.environ.get("SNIP_BASE_URL", "http://localhost:8000")
    base_url = base_url.rstrip("/")
    return Settings(db_path=db_path, base_url=base_url)
