"""Correlation-id plumbing for structured service logs.

A ``request_id`` is generated at the entry of each service tool call and
propagated via ``contextvars`` so every log line inside that call carries
it. Logs also gain ``debate_id`` when one is available. The filter is
idempotent — attaching it twice is harmless.
"""

from __future__ import annotations

import contextvars
import logging
import uuid
from contextlib import contextmanager

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("ploidy_request_id", default="-")
_debate_id: contextvars.ContextVar[str] = contextvars.ContextVar("ploidy_debate_id", default="-")


class CorrelationFilter(logging.Filter):
    """Attach request_id / debate_id to every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        record.debate_id = _debate_id.get()
        return True


_CORR_FORMAT = (
    "%(asctime)s [%(name)s] %(levelname)s req=%(request_id)s debate=%(debate_id)s: %(message)s"
)


def install(level: int = logging.INFO) -> None:
    """Install the correlation filter on the root logger once."""
    root = logging.getLogger()
    # Reset handlers to apply the new formatter; main() normally sets this up.
    if not any(isinstance(f, CorrelationFilter) for f in root.filters):
        root.addFilter(CorrelationFilter())
    for handler in root.handlers:
        if not any(isinstance(f, CorrelationFilter) for f in handler.filters):
            handler.addFilter(CorrelationFilter())
    root.setLevel(level)


@contextmanager
def scope(*, debate_id: str | None = None, request_id: str | None = None):
    """Enter a correlation scope for the duration of a service call."""
    rid = request_id or uuid.uuid4().hex[:10]
    req_tok = _request_id.set(rid)
    dbg_tok = _debate_id.set(debate_id or "-")
    try:
        yield rid
    finally:
        _request_id.reset(req_tok)
        _debate_id.reset(dbg_tok)


def set_debate_id(debate_id: str) -> None:
    """Set the current debate_id within an existing scope."""
    _debate_id.set(debate_id)


def get_request_id() -> str:
    return _request_id.get()


def deprecated(*, version: str, prefer: str):
    """Prepend a one-line deprecation notice to the wrapped callable's ``__doc__``.

    FastMCP surfaces ``__doc__`` as the tool description that LLM clients read,
    so editing it in one place (the decorator) keeps the 12 legacy debate tools
    in sync without duplicating the same sentence into every docstring.
    """
    prefix = f"DEPRECATED (v{version}) — prefer {prefer}."

    def decorator(fn):
        existing = fn.__doc__ or ""
        fn.__doc__ = prefix + "\n\n    " + existing.lstrip() if existing else prefix
        return fn

    return decorator


def traced(fn):
    """Decorator that runs an async callable inside a correlation scope.

    If the wrapped call returns a dict with a ``debate_id`` key, that ID
    gets attached to the trailing log lines automatically — handy for
    tools like ``debate_start`` that mint a fresh id partway through.
    """
    import functools

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        # Inbound debate_id (if the caller passed one) gets the scope
        # started with it; otherwise we set it after the return.
        inbound = kwargs.get("debate_id") or (
            args[0] if args and isinstance(args[0], str) else None
        )
        with scope(debate_id=inbound):
            result = await fn(*args, **kwargs)
            if isinstance(result, dict) and result.get("debate_id"):
                set_debate_id(result["debate_id"])
            return result

    wrapper.__ploidy_traced__ = True  # type: ignore[attr-defined]
    wrapper.__ploidy_request_id__ = lambda: get_request_id()  # type: ignore[attr-defined]
    return wrapper
