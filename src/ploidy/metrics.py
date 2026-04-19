"""Prometheus metrics for Ploidy.

Requires ``prometheus-client``. When the package is missing the module
falls back to a dict-of-counters shim so unit tests and core behaviour
stay functional without the optional dependency installed.

Metrics are tagged with ``tenant`` where it makes sense; unscoped
legacy debates report as ``tenant="unscoped"``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ploidy.metrics")

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Histogram,
        generate_latest,
    )

    _HAS_PROMETHEUS = True
except ImportError:  # pragma: no cover - exercised only when extra missing
    _HAS_PROMETHEUS = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"


_TENANT = "tenant"
_MODE = "mode"
_OUTCOME = "outcome"


class _NoopMetric:
    """Fallback when prometheus_client is unavailable."""

    def labels(self, **_kwargs):
        return self

    def inc(self, _amount: float = 1.0) -> None:
        pass

    def observe(self, _value: float) -> None:
        pass


class _Metrics:
    """Single owner of all registry + metric objects.

    Instances are cheap; reset() rebuilds them against a fresh registry,
    which keeps test isolation simple (each test gets a clean counter
    set instead of fighting a process-wide singleton).
    """

    def __init__(self) -> None:
        self.enabled = _HAS_PROMETHEUS
        if self.enabled:
            self.registry = CollectorRegistry()
            self.debate_started = Counter(
                "ploidy_debate_started_total",
                "Debates started",
                (_TENANT, _MODE),
                registry=self.registry,
            )
            self.debate_completed = Counter(
                "ploidy_debate_completed_total",
                "Debates that reached convergence",
                (_TENANT, _MODE),
                registry=self.registry,
            )
            self.debate_cancelled = Counter(
                "ploidy_debate_cancelled_total",
                "Debates cancelled or rejected",
                (_TENANT, _OUTCOME),
                registry=self.registry,
            )
            self.messages_recorded = Counter(
                "ploidy_messages_recorded_total",
                "Messages submitted by phase",
                (_TENANT, "phase"),
                registry=self.registry,
            )
            self.convergence_duration = Histogram(
                "ploidy_convergence_duration_seconds",
                "Time spent in the convergence engine",
                (_TENANT, _MODE),
                registry=self.registry,
            )
            self.rate_limit_rejections = Counter(
                "ploidy_rate_limit_rejections_total",
                "Calls rejected by the token bucket",
                (_TENANT,),
                registry=self.registry,
            )
            self.api_calls = Counter(
                "ploidy_api_calls_total",
                "Outbound OpenAI-compatible API calls",
                (_TENANT, _OUTCOME),
                registry=self.registry,
            )
        else:
            self.registry = None
            self.debate_started = _NoopMetric()
            self.debate_completed = _NoopMetric()
            self.debate_cancelled = _NoopMetric()
            self.messages_recorded = _NoopMetric()
            self.convergence_duration = _NoopMetric()
            self.rate_limit_rejections = _NoopMetric()
            self.api_calls = _NoopMetric()

    def render(self) -> bytes:
        if not self.enabled:
            return b"# prometheus-client not installed\n"
        return generate_latest(self.registry)


_metrics = _Metrics()


def metrics() -> _Metrics:
    """Return the module-level metrics facade."""
    return _metrics


def reset() -> None:
    """Replace the shared registry; tests call this in their setup."""
    global _metrics
    _metrics = _Metrics()


def tenant_label(owner_id: str | None) -> str:
    """Stable label value for an (possibly unscoped) tenant."""
    return owner_id if owner_id else "unscoped"


def content_type() -> str:
    return CONTENT_TYPE_LATEST
