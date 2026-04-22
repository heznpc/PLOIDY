"""Correlation-id filter, scope, and install() smoke tests.

These cover the logctx paths that the service imports but do not drive
in the existing service tests — ``CorrelationFilter.filter``, the
idempotent ``install()`` setup, and the ``get_request_id()`` accessor.
"""

import logging

from ploidy import logctx


def test_correlation_filter_injects_ids_from_current_scope():
    filt = logctx.CorrelationFilter()
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    with logctx.scope(debate_id="d123", request_id="r456"):
        assert filt.filter(rec) is True
        assert rec.request_id == "r456"
        assert rec.debate_id == "d123"


def test_correlation_filter_uses_defaults_outside_scope():
    filt = logctx.CorrelationFilter()
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    assert filt.filter(rec) is True
    # Default sentinel is ``-`` — distinguishes "no scope" from a real id.
    assert rec.request_id == "-"
    assert rec.debate_id == "-"


def test_get_request_id_tracks_current_scope():
    with logctx.scope(request_id="custom"):
        assert logctx.get_request_id() == "custom"
    assert logctx.get_request_id() == "-"


def test_install_adds_filter_and_is_idempotent():
    root = logging.getLogger()
    saved_filters = list(root.filters)
    saved_level = root.level
    saved_handler_filters = [(h, list(h.filters)) for h in root.handlers]
    try:
        logctx.install(level=logging.DEBUG)
        # Root gains exactly one CorrelationFilter.
        corr_count = sum(1 for f in root.filters if isinstance(f, logctx.CorrelationFilter))
        assert corr_count == 1
        assert root.level == logging.DEBUG

        # Every existing handler also gains the filter.
        for h in root.handlers:
            assert any(isinstance(f, logctx.CorrelationFilter) for f in h.filters)

        # Re-install must not duplicate the filter.
        logctx.install()
        corr_count_again = sum(1 for f in root.filters if isinstance(f, logctx.CorrelationFilter))
        assert corr_count_again == 1
    finally:
        root.filters[:] = saved_filters
        root.setLevel(saved_level)
        for h, filts in saved_handler_filters:
            h.filters[:] = filts
