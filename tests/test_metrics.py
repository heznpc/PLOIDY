"""Metrics recording tests.

Verify that service lifecycle events drive the Prometheus counters and
that the /metrics endpoint serves the snapshot.
"""

import pytest

from ploidy import metrics as metrics_mod
from ploidy.metrics import CONTENT_TYPE_LATEST, _NoopMetric, content_type
from ploidy.service import DebateService
from ploidy.store import DebateStore


def _counter_value(metric, **labels) -> float:
    """Read a counter's current value for a label set."""
    return metric.labels(**labels)._value.get()  # type: ignore[attr-defined]


@pytest.fixture
async def svc(tmp_path):
    metrics_mod.reset()
    store = DebateStore(db_path=tmp_path / "m.db")
    service = DebateService(store=store)
    await service.initialize()
    yield service
    await service.shutdown()


async def test_start_increments_counter(svc):
    m = metrics_mod.metrics()
    await svc.start_debate("p", owner_id="tenant-a")
    assert _counter_value(m.debate_started, tenant="tenant-a", mode="two_terminal") == 1.0


async def test_full_flow_counts_positions_challenges_and_completion(svc):
    m = metrics_mod.metrics()
    start = await svc.start_debate("flow", owner_id="t1")
    join = await svc.join_debate(start["debate_id"], owner_id="t1")

    await svc.submit_position(start["session_id"], "A", owner_id="t1")
    await svc.submit_position(join["session_id"], "B", owner_id="t1")
    await svc.submit_challenge(start["session_id"], "x", "challenge", owner_id="t1")
    await svc.submit_challenge(join["session_id"], "y", "challenge", owner_id="t1")
    await svc.converge(start["debate_id"], owner_id="t1")

    assert _counter_value(m.messages_recorded, tenant="t1", phase="position") == 2.0
    assert _counter_value(m.messages_recorded, tenant="t1", phase="challenge") == 2.0
    assert _counter_value(m.debate_completed, tenant="t1", mode="two_terminal") == 1.0


async def test_cancel_increments_cancelled_counter(svc):
    m = metrics_mod.metrics()
    res = await svc.start_debate("cancel", owner_id="t1")
    await svc.cancel(res["debate_id"], owner_id="t1")
    assert _counter_value(m.debate_cancelled, tenant="t1", outcome="cancelled") == 1.0


async def test_rate_limit_rejection_counted(tmp_path):
    from ploidy.ratelimit import RateLimitError, TokenBucketLimiter

    metrics_mod.reset()
    limiter = TokenBucketLimiter(capacity=1, rate_per_sec=0.0001)
    svc = DebateService(store=DebateStore(db_path=tmp_path / "rl.db"), rate_limiter=limiter)
    await svc.initialize()
    try:
        await svc.start_debate("first", owner_id="t1")
        with pytest.raises(RateLimitError):
            await svc.start_debate("second", owner_id="t1")
        assert _counter_value(metrics_mod.metrics().rate_limit_rejections, tenant="t1") == 1.0
    finally:
        await svc.shutdown()


def test_render_exposes_counter_values():
    """render() emits Prometheus text format; counter names appear as substrings."""
    metrics_mod.reset()
    m = metrics_mod.metrics()
    m.debate_started.labels(tenant="t1", mode="solo").inc()
    body = m.render().decode("utf-8")
    assert "ploidy_debate_started_total" in body
    assert 'tenant="t1"' in body
    assert 'mode="solo"' in body


class TestNoopMetric:
    """Fallback stubs used when prometheus_client is not installed."""

    def test_labels_returns_self_for_fluent_chaining(self):
        m = _NoopMetric()
        assert m.labels(tenant="x", mode="y") is m

    def test_inc_and_observe_are_silent_noops(self):
        m = _NoopMetric()
        # Neither method raises — this keeps every call site branch-free.
        m.inc()
        m.inc(3.5)
        m.observe(0.125)


class TestPrometheusMissingFallback:
    """Exercise the ``_HAS_PROMETHEUS=False`` branches of ``_Metrics.__init__``."""

    def test_fallback_registry_is_none_and_counters_are_noop(self, monkeypatch):
        monkeypatch.setattr(metrics_mod, "_HAS_PROMETHEUS", False)
        metrics_mod.reset()
        try:
            m = metrics_mod.metrics()
            assert m.enabled is False
            assert m.registry is None
            # Every counter must be a noop so call sites do not need guards.
            m.debate_started.labels(tenant="t", mode="solo").inc()
            m.api_calls.labels(tenant="t", outcome="ok").inc()
            m.convergence_duration.labels(tenant="t", mode="auto").observe(1.2)
            # render() returns an informational placeholder rather than
            # a real Prometheus exposition body.
            body = m.render()
            assert b"not installed" in body
        finally:
            # Restore the real registry for subsequent tests.
            monkeypatch.setattr(metrics_mod, "_HAS_PROMETHEUS", True)
            metrics_mod.reset()


def test_content_type_returns_prometheus_constant():
    # The metrics HTTP handler reads this directly; verify it is non-empty
    # and matches the Prometheus client's constant.
    assert content_type() == CONTENT_TYPE_LATEST
    assert content_type()  # not empty
