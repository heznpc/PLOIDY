"""Lock provider abstraction for single-node and Redis-backed deployments.

The service has always used ``asyncio.Lock`` keyed by ``debate_id`` to
serialise concurrent writes within one process. That is correct for a
single replica but breaks the moment two pods handle requests for the
same debate.

``LockProvider`` factors that primitive out so deployments can pick an
implementation:

- :class:`AsyncLockProvider` — default; wraps ``asyncio.Lock`` exactly
  like before, one lock per debate, stored in a local dict.
- :class:`RedisLockProvider` — distributed lock via SET NX / DEL with a
  unique token, safe to hold across pods. Uses ``redis.asyncio``; the
  ``redis`` package is optional.

For multi-replica we also need a way to serialise the in-memory caches
(protocols/sessions/etc.) — that is out of scope for this module. The
first step is distributed locks; replicas that need shared caches must
either lazily rehydrate from the database or adopt sticky routing.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Protocol


class LockProvider(Protocol):
    """Interface: provide an async context manager for a keyed lock."""

    def lock(self, key: str):  # pragma: no cover - protocol definition
        """Return an async context manager guarding ``key``."""
        ...

    async def close(self) -> None:  # pragma: no cover - protocol definition
        """Release any backend resources (connection pools, etc.)."""


class AsyncLockProvider:
    """Per-process ``asyncio.Lock`` keyed by debate_id.

    ``dict.setdefault`` is atomic in CPython, so concurrent callers that
    both touch a fresh key still end up with the same ``asyncio.Lock``
    object.
    """

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def lock(self, key: str):
        return self._locks.setdefault(key, asyncio.Lock())

    async def close(self) -> None:
        self._locks.clear()

    # Exposed for tests and compatibility with existing service code that
    # expected a plain dict.
    def get(self, key: str) -> asyncio.Lock:
        return self.lock(key)

    def pop(self, key: str) -> None:
        self._locks.pop(key, None)


class RedisLockProvider:
    """Distributed lock backed by Redis ``SET key value NX PX``.

    Each ``lock(key)`` call blocks (with bounded retry) until it holds
    the key, then releases it with a safe compare-and-delete so a caller
    never deletes someone else's lock.

    ``ttl_ms`` caps how long one holder can keep the lock; if a holder
    crashes the key expires and another caller can proceed. Callers are
    expected to finish their critical section well under ``ttl_ms``.
    """

    def __init__(
        self,
        client,  # redis.asyncio.Redis
        *,
        prefix: str = "ploidy:lock:",
        ttl_ms: int = 30_000,
        retry_delay: float = 0.05,
        acquire_timeout: float = 30.0,
    ) -> None:
        self._client = client
        self._prefix = prefix
        self._ttl_ms = ttl_ms
        self._retry_delay = retry_delay
        self._acquire_timeout = acquire_timeout

    @asynccontextmanager
    async def lock(self, key: str):
        redis_key = f"{self._prefix}{key}"
        token = uuid.uuid4().hex
        deadline = time.monotonic() + self._acquire_timeout
        while True:
            acquired = await self._client.set(redis_key, token, nx=True, px=self._ttl_ms)
            if acquired:
                break
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"RedisLockProvider: could not acquire {key} within {self._acquire_timeout}s"
                )
            await asyncio.sleep(self._retry_delay)
        try:
            yield
        finally:
            await self._release(redis_key, token)

    async def _release(self, redis_key: str, token: str) -> None:
        """Compare-and-delete using WATCH/MULTI/EXEC.

        A plain ``DEL`` would risk nuking another holder's lock if this
        caller's TTL already expired and someone else re-acquired. The
        transaction checks the key still carries our token and only
        deletes if so; otherwise we abandon release and let the natural
        TTL clean up.
        """
        try:
            async with self._client.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(redis_key)
                    current = await self._client.get(redis_key)
                    if current != token:
                        await pipe.unwatch()
                        return
                    pipe.multi()
                    pipe.delete(redis_key)
                    await pipe.execute()
                except Exception:
                    try:
                        await pipe.unwatch()
                    except Exception:
                        pass
        except Exception:
            # Lock will expire on its own if release fails.
            pass

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except AttributeError:
            # Older redis-py versions used close() instead.
            await self._client.close()
