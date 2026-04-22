"""Tests for the MCP server module.

Covers the helper functions and custom ASGI routes that ``server.py``
exposes. The MCP tool decorators themselves (``@mcp.tool``) delegate
to ``DebateService``, which has its own dedicated test suite — so we
focus on the auth, route, and lifecycle glue that lives in this module.
"""

from __future__ import annotations

import json as _json
from unittest.mock import MagicMock


class TestLoadTokenMap:
    """``_load_token_map`` converts env strings into token→tenant dicts."""

    def _reload(self, monkeypatch, *, tokens: str | None = None, auth: str | None = None):
        # Module-level globals cache the env at import time; exercise the
        # function after clearing the caches so each scenario is fresh.
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP_RAW", tokens or "")
        monkeypatch.setattr(srv, "_AUTH_TOKEN", auth)
        return srv._load_token_map()

    def test_json_map_parsed_into_dict(self, monkeypatch):
        mapping = self._reload(
            monkeypatch,
            tokens=_json.dumps({"tok-a": "tenant-a", "tok-b": "tenant-b"}),
        )
        assert mapping == {"tok-a": "tenant-a", "tok-b": "tenant-b"}

    def test_malformed_json_is_logged_and_returns_empty(self, monkeypatch, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="ploidy")
        mapping = self._reload(monkeypatch, tokens="{not json")
        assert mapping == {}
        assert any("not valid JSON" in r.message for r in caplog.records)

    def test_non_object_json_is_rejected(self, monkeypatch, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="ploidy")
        mapping = self._reload(monkeypatch, tokens=_json.dumps(["a", "b"]))
        assert mapping == {}
        assert any("object of token" in r.message for r in caplog.records)

    def test_single_auth_token_falls_back_to_ploidy_client(self, monkeypatch):
        mapping = self._reload(monkeypatch, auth="legacy-token")
        assert mapping == {"legacy-token": "ploidy-client"}

    def test_neither_configured_returns_empty(self, monkeypatch):
        mapping = self._reload(monkeypatch)
        assert mapping == {}

    def test_values_coerced_to_strings(self, monkeypatch):
        # JSON allows any scalar in values; the server normalises to str
        # so tenant labels are always safe to pass into Prometheus.
        mapping = self._reload(monkeypatch, tokens=_json.dumps({"t": 42}))
        assert mapping == {"t": "42"}


class TestTokenVerifier:
    """``_PloidyTokenVerifier.verify_token`` drives the bearer auth path."""

    async def test_valid_token_returns_access_token_with_tenant(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"tok-valid": "tenant-42"})
        verifier = srv._PloidyTokenVerifier()
        access = await verifier.verify_token("tok-valid")
        assert access is not None
        assert access.client_id == "tenant-42"
        assert "debate" in access.scopes

    async def test_invalid_token_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"tok-valid": "tenant-42"})
        verifier = srv._PloidyTokenVerifier()
        assert await verifier.verify_token("wrong") is None

    async def test_empty_token_map_always_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {})
        verifier = srv._PloidyTokenVerifier()
        assert await verifier.verify_token("anything") is None

    async def test_verifier_runs_full_scan_for_constant_time(self, monkeypatch):
        """Matching is constant-time — every entry is compared even after a hit."""
        from ploidy import server as srv

        call_count = {"n": 0}
        real_compare = srv.hmac.compare_digest

        def counting_compare(a, b):
            call_count["n"] += 1
            return real_compare(a, b)

        monkeypatch.setattr(srv.hmac, "compare_digest", counting_compare)
        monkeypatch.setattr(
            srv,
            "_TOKEN_MAP",
            {"a": "ta", "b": "tb", "c": "tc"},
        )
        verifier = srv._PloidyTokenVerifier()
        await verifier.verify_token("a")
        assert call_count["n"] == 3  # did not short-circuit on the first match


class TestCurrentOwner:
    """``_current_owner`` resolves the tenant from the MCP auth context."""

    def test_no_token_map_returns_none_without_consulting_context(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {})
        # ``get_access_token`` should not even be called — guarded by the
        # token-map check so tests can run without FastMCP's context set.
        sentinel = object()
        monkeypatch.setattr(srv, "get_access_token", lambda: sentinel)
        assert srv._current_owner() is None

    def test_access_token_client_id_is_returned(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"t": "tenant"})
        fake_token = MagicMock()
        fake_token.client_id = "tenant-7"
        monkeypatch.setattr(srv, "get_access_token", lambda: fake_token)
        assert srv._current_owner() == "tenant-7"

    def test_missing_access_token_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"t": "tenant"})
        monkeypatch.setattr(srv, "get_access_token", lambda: None)
        assert srv._current_owner() is None


class TestResolveStreamOwner:
    """``_resolve_stream_owner`` is the custom-route equivalent of ``_current_owner``."""

    def _request(self, authorization: str | None = None):
        req = MagicMock()
        req.headers = {"authorization": authorization} if authorization else {}
        return req

    def test_no_token_map_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {})
        assert srv._resolve_stream_owner(self._request("Bearer anything")) is None

    def test_missing_authorization_header_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"t": "tenant"})
        assert srv._resolve_stream_owner(self._request(None)) is None

    def test_non_bearer_scheme_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"t": "tenant"})
        assert srv._resolve_stream_owner(self._request("Basic Zm9vOmJhcg==")) is None

    def test_valid_bearer_token_returns_tenant(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"tok": "tenant-42"})
        assert srv._resolve_stream_owner(self._request("Bearer tok")) == "tenant-42"

    def test_unknown_bearer_token_returns_none(self, monkeypatch):
        from ploidy import server as srv

        monkeypatch.setattr(srv, "_TOKEN_MAP", {"tok": "tenant-42"})
        assert srv._resolve_stream_owner(self._request("Bearer unknown")) is None


class TestBuildLockProvider:
    """``_build_lock_provider`` picks the Redis backend when PLOIDY_REDIS_URL is set."""

    def test_no_redis_url_returns_async_lock_provider(self, monkeypatch):
        from ploidy import server as srv
        from ploidy.lockprovider import AsyncLockProvider

        # The module caches the URL at import time; patch the cached value.
        monkeypatch.setattr(srv, "_REDIS_URL", "")
        provider = srv._build_lock_provider()
        assert isinstance(provider, AsyncLockProvider)

    def test_redis_url_returns_redis_lock_provider(self, monkeypatch):
        # The factory only constructs the client — it does not open a
        # connection until first use, so pointing at a fake URL is fine.
        from ploidy import server as srv
        from ploidy.lockprovider import RedisLockProvider

        monkeypatch.setattr(srv, "_REDIS_URL", "redis://fake:6379/0")
        provider = srv._build_lock_provider()
        assert isinstance(provider, RedisLockProvider)


class TestHealthzRoute:
    async def test_ok_when_init_succeeds(self, monkeypatch):
        from ploidy import server as srv

        # Stub _init so the handler doesn't touch the real DB.
        async def fake_init():
            return MagicMock()

        monkeypatch.setattr(srv, "_init", fake_init)
        resp = await srv._healthz(MagicMock())
        assert resp.status_code == 200
        body = _json.loads(resp.body)
        assert body["status"] == "ok"

    async def test_503_when_init_raises(self, monkeypatch):
        from ploidy import server as srv

        async def broken_init():
            raise RuntimeError("db down")

        monkeypatch.setattr(srv, "_init", broken_init)
        resp = await srv._healthz(MagicMock())
        assert resp.status_code == 503
        body = _json.loads(resp.body)
        assert body["status"] == "error"
        assert "db down" in body["detail"]


class TestMetricsRoute:
    async def test_returns_prometheus_body_with_correct_media_type(self):
        from ploidy import server as srv

        resp = await srv._metrics_endpoint(MagicMock())
        # Prometheus exposition body is text/plain-ish; media_type must match
        # whatever ``metrics.content_type()`` returns so scrapers parse it.
        from ploidy.metrics import content_type

        assert resp.media_type == content_type()
        # Body is bytes; decoding it should not raise.
        resp.body.decode("utf-8")


class TestWebappRoute:
    async def test_returns_html_index(self):
        from ploidy import server as srv

        resp = await srv._webapp(MagicMock())
        assert resp.status_code == 200
        text = resp.body.decode("utf-8")
        # Webapp docstring promises static HTML — verify the shape rather
        # than the content so this test is resilient to UI tweaks.
        assert "<!DOCTYPE html>" in text or "<html" in text.lower()
