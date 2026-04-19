"""Retention job tests.

Verify that purge_terminal_before removes only completed/cancelled rows
past the cutoff, preserves active/paused, and that the service wrapper
drives the purge correctly.
"""

import pytest

from ploidy.service import DebateService
from ploidy.store import DebateStore


async def _backdate(store: DebateStore, debate_id: str, iso: str) -> None:
    """Stamp a debate row's updated_at to a specific ISO timestamp."""
    db = store._db
    await db.execute("UPDATE debates SET updated_at = ? WHERE id = ?", (iso, debate_id))
    await db.commit()


@pytest.fixture
async def store(tmp_path):
    s = DebateStore(db_path=tmp_path / "ret.db")
    await s.initialize()
    yield s
    await s.close()


async def test_purge_removes_old_terminal_rows(store):
    await store.save_debate("old-complete", "p")
    await store.update_debate_status("old-complete", "complete")
    await _backdate(store, "old-complete", "2020-01-01 00:00:00")

    await store.save_debate("old-cancelled", "p")
    await store.update_debate_status("old-cancelled", "cancelled")
    await _backdate(store, "old-cancelled", "2020-01-01 00:00:00")

    removed = await store.purge_terminal_before("2024-01-01 00:00:00")
    assert removed == 2
    assert await store.get_debate("old-complete") is None
    assert await store.get_debate("old-cancelled") is None


async def test_purge_keeps_active_and_paused_regardless_of_age(store):
    await store.save_debate("old-active", "p")
    await _backdate(store, "old-active", "2020-01-01 00:00:00")

    await store.save_debate("old-paused", "p")
    await store.update_debate_status("old-paused", "paused")
    await _backdate(store, "old-paused", "2020-01-01 00:00:00")

    removed = await store.purge_terminal_before("2024-01-01 00:00:00")
    assert removed == 0
    assert await store.get_debate("old-active") is not None
    assert await store.get_debate("old-paused") is not None


async def test_purge_skips_recent_rows(store):
    await store.save_debate("recent", "p")
    await store.update_debate_status("recent", "complete")
    # updated_at defaults to 'now' on that UPDATE, so leave it untouched
    removed = await store.purge_terminal_before("1999-01-01 00:00:00")
    assert removed == 0
    assert await store.get_debate("recent") is not None


async def test_purge_cascades_messages_and_sessions(store):
    await store.save_debate("d1", "p")
    await store.save_session("d1-s1", "d1", "deep", "p")
    await store.save_message("d1", "d1-s1", "position", "content")
    await store.update_debate_status("d1", "complete")
    await _backdate(store, "d1", "2020-01-01 00:00:00")

    removed = await store.purge_terminal_before("2024-01-01 00:00:00")
    assert removed == 1

    messages = await store.get_messages("d1")
    sessions = await store.get_sessions("d1")
    assert messages == []
    assert sessions == []


async def test_service_run_retention_once_noop_when_disabled(tmp_path):
    svc = DebateService(store=DebateStore(db_path=tmp_path / "r.db"), retention_days=0)
    await svc.initialize()
    try:
        # Disabled service skips the background task entirely.
        assert svc._retention_task is None
        removed = await svc.run_retention_once()
        assert removed == 0
    finally:
        await svc.shutdown()


async def test_service_run_retention_once_purges_old(tmp_path):
    svc = DebateService(
        store=DebateStore(db_path=tmp_path / "r2.db"),
        retention_days=30,
        retention_interval_seconds=3600,
        retention_vacuum=False,
    )
    await svc.initialize()
    try:
        # Background task started because retention_days > 0.
        assert svc._retention_task is not None

        start = await svc.start_debate("old", owner_id="t")
        await svc.cancel(start["debate_id"], owner_id="t")
        await _backdate(svc.store, start["debate_id"], "2020-01-01 00:00:00")

        removed = await svc.run_retention_once()
        assert removed == 1
    finally:
        await svc.shutdown()


async def test_vacuum_runs_without_error(store):
    await store.vacuum()
