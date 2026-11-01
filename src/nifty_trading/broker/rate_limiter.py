"""Rate limiting utility for broker API calls."""

import random
import time
from dataclasses import dataclass


@dataclass
class RateLimiter:
    """Thread-safe rate limiter with interval pacing and jitter."""

    max_calls_per_second: float = 3.0
    jitter_range: tuple[float, float] = (0.05, 0.15)
    _last_call_time: float = 0.0

    def wait(self) -> None:
        """Wait if necessary to comply with rate limits, adding jitter."""
        min_interval = 1.0 / self.max_calls_per_second
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < min_interval:
            sleep_time = (min_interval - elapsed) + random.uniform(*self.jitter_range)
            time.sleep(sleep_time)
        self._last_call_time = time.monotonic()

