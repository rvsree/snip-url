import math
import time
from typing import Callable

from snip_url.common.errors import AppError

RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW_SECONDS = 60


class RateLimiter:
    """In-memory sliding-window limiter with an injectable clock."""

    # Store the limits, the clock and an empty hit table.
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = clock
        self.hits: dict[str, list[float]] = {}

    # Raise AppError(429, "rate_limited", ...) with Retry-After if key is over the limit; else record the hit.
    def enforce(self, key: str) -> None:
        wait = self.check(key)
        if wait > 0:
            raise AppError(
                429,
                "rate_limited",
                "Too many requests. Try again later.",
                headers={"Retry-After": str(wait)},
            )

    # Return 0 and record the hit if allowed, else whole seconds (>= 1) until a slot frees.
    def check(self, key: str) -> int:
        now = self.clock()
        kept: list[float] = []
        for stamp in self.hits.get(key, []):
            if now - stamp < self.window_seconds:
                kept.append(stamp)
        if len(kept) >= self.max_requests:
            self.hits[key] = kept
            wait = math.ceil(kept[0] + self.window_seconds - now)
            return max(wait, 1)
        kept.append(now)
        self.hits[key] = kept
        return 0
