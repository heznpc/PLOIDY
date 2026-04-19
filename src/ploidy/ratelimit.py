"""Token-bucket rate limiter.

Used at service boundaries that spend real resources — ``run_auto`` and
``run_solo``. Keyed buckets (one per tenant, IP, or token) support future
multi-tenant deployments; the default key is ``"global"``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from ploidy.exceptions import PloidyError


class RateLimitError(PloidyError):
    """Raised when a caller exhausts its token bucket."""


# Backwards-compatible alias for the early naming.
RateLimitExceeded = RateLimitError


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class TokenBucketLimiter:
    """In-process keyed token bucket.

    Each key gets its own bucket of ``capacity`` tokens that refills at
    ``rate_per_sec``. ``acquire(key)`` consumes one token or raises
    ``RateLimitExceeded`` when the bucket is empty.

    For multi-process deployments replace with a Redis-backed bucket.
    """

    def __init__(self, capacity: float, rate_per_sec: float) -> None:
        self.capacity = capacity
        self.rate_per_sec = rate_per_sec
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self.capacity > 0 and self.rate_per_sec > 0

    async def acquire(self, key: str = "global", cost: float = 1.0) -> None:
        if not self.enabled:
            return
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, last_refill=now)
                self._buckets[key] = bucket
            elapsed = now - bucket.last_refill
            bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.rate_per_sec)
            bucket.last_refill = now
            if bucket.tokens < cost:
                raise RateLimitError(
                    f"Rate limit exceeded for key={key}; "
                    f"tokens={bucket.tokens:.2f}, required={cost}"
                )
            bucket.tokens -= cost
