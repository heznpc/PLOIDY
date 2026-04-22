"""LockProvider contract tests.

Both AsyncLockProvider and RedisLockProvider must provide mutual
exclusion: a second acquirer must wait until the first releases. The
Redis backend is exercised against fakeredis so the tests run offline.
"""

import asyncio

import pytest

from ploidy.lockprovider import AsyncLockProvider, RedisLockProvider


async def _exercise_mutex(provider) -> list[int]:
    """Two concurrent tasks grab the same key and must serialise."""
    observed: list[int] = []

    async def hold(i: int) -> None:
        async with provider.lock("shared"):
            observed.append(i)
            # Release-after-sleep so a concurrent task would race if the
            # lock wasn't mutually exclusive.
            await asyncio.sleep(0.05)
            observed.append(-i)

    await asyncio.gather(hold(1), hold(2))
    return observed


async def test_async_lock_provider_serialises():
    provider = AsyncLockProvider()
    try:
        observed = await _exercise_mutex(provider)
        # Must see enter-exit pairs back-to-back with no interleaving.
        assert observed in ([1, -1, 2, -2], [2, -2, 1, -1])
    finally:
        await provider.close()


async def test_async_lock_provider_reuses_lock_per_key():
    provider = AsyncLockProvider()
    try:
        a = provider.lock("same")
        b = provider.lock("same")
        assert a is b
        other = provider.lock("different")
        assert other is not a
    finally:
        await provider.close()


async def test_redis_lock_provider_serialises():
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    provider = RedisLockProvider(client, ttl_ms=5_000, retry_delay=0.01)
    try:
        observed = await _exercise_mutex(provider)
        assert observed in ([1, -1, 2, -2], [2, -2, 1, -1])
    finally:
        await provider.close()


async def test_redis_lock_provider_releases_on_exit():
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    provider = RedisLockProvider(client, ttl_ms=5_000, retry_delay=0.01)
    try:
        async with provider.lock("k"):
            present = await client.get("ploidy:lock:k")
            assert present is not None
        # After exit, the key should be gone (compare-and-delete succeeded).
        cleared = await client.get("ploidy:lock:k")
        assert cleared is None
    finally:
        await provider.close()


async def test_redis_lock_provider_safe_against_foreign_release():
    """Releasing my handle must not delete another holder's lock."""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    a = RedisLockProvider(client, ttl_ms=5_000, retry_delay=0.01)
    try:
        # Simulate another holder already owning the key with a different token.
        await client.set("ploidy:lock:k", "someone-else", px=5_000)
        # Our provider sees the key as taken and would retry; force a short
        # acquire_timeout so the test doesn't hang.
        a._acquire_timeout = 0.1
        with pytest.raises(TimeoutError):
            async with a.lock("k"):
                pass
        # Foreign lock must still be held.
        assert await client.get("ploidy:lock:k") == "someone-else"
    finally:
        await a.close()


async def test_async_lock_provider_pop_removes_key():
    provider = AsyncLockProvider()
    try:
        lock_a = provider.lock("k1")
        provider.pop("k1")
        # Re-locking the same key yields a fresh object once the old one is popped.
        lock_b = provider.lock("k1")
        assert lock_b is not lock_a
        # Popping a key that does not exist is a silent no-op.
        provider.pop("never-locked")
    finally:
        await provider.close()


async def test_redis_release_skips_delete_when_token_no_longer_matches():
    """If TTL expired and someone else re-acquired, release must not DEL their lock."""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    provider = RedisLockProvider(client, ttl_ms=5_000, retry_delay=0.01)
    try:
        redis_key = "ploidy:lock:stolen"
        # Acquire with our token, then simulate the TTL expiring and a
        # foreign caller grabbing the key before we release.
        async with provider.lock("stolen"):
            await client.set(redis_key, "foreign-token", px=5_000)
        # The foreign token must still be present — our release did not DEL it.
        assert await client.get(redis_key) == "foreign-token"
    finally:
        await provider.close()


async def test_redis_release_swallows_pipeline_errors():
    """A broken pipeline mid-release must not propagate to the caller."""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    provider = RedisLockProvider(client, ttl_ms=5_000, retry_delay=0.01)
    try:
        async with provider.lock("k"):
            # Corrupt the client so the next pipeline call will blow up.
            # The release path is invoked on __aexit__, and any exception
            # inside it is swallowed so the caller's try/finally still runs.
            client.pipeline = lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("connection lost")
            )
        # No exception escaped the context manager.
    finally:
        pass  # provider.close() may also hit the broken client; ignore.


class _FakeRedisCloseOnly:
    """Older redis-py exposed ``close()`` but not ``aclose()``."""

    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


async def test_redis_close_falls_back_to_close_on_older_clients():
    client = _FakeRedisCloseOnly()
    provider = RedisLockProvider(client)
    await provider.close()
    assert client.closed is True


async def test_service_uses_redis_lock_provider(tmp_path):
    """Smoke test: wire a Redis lock into a live service and drive a full flow."""
    import fakeredis.aioredis

    from ploidy.service import DebateService
    from ploidy.store import DebateStore

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    provider = RedisLockProvider(client, ttl_ms=5_000, retry_delay=0.01)
    svc = DebateService(
        store=DebateStore(db_path=tmp_path / "rl.db"),
        lock_provider=provider,
    )
    await svc.initialize()
    try:
        start = await svc.start_debate("redis-backed", owner_id="t1")
        join = await svc.join_debate(start["debate_id"], owner_id="t1")
        await svc.submit_position(start["session_id"], "A", owner_id="t1")
        await svc.submit_position(join["session_id"], "B", owner_id="t1")
        await svc.submit_challenge(start["session_id"], "x", "challenge", owner_id="t1")
        await svc.submit_challenge(join["session_id"], "y", "challenge", owner_id="t1")
        result = await svc.converge(start["debate_id"], owner_id="t1")
        assert result["phase"] == "complete"
    finally:
        await svc.shutdown()
