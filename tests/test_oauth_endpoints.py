"""End-to-end tests for the FastMCP-mounted OAuth endpoints (slice 4).

Exercises the discovery, DCR, authorize, and token endpoints that
FastMCP auto-mounts when an ``auth_server_provider`` is configured.
The ASGI app is driven through ``httpx.ASGITransport`` so tests talk
to the real route handlers without spawning a live server.
"""

from __future__ import annotations

import httpx
import pytest
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import FastMCP

from ploidy.oauth import PloidyOAuthProvider
from ploidy.store import DebateStore

_ISSUER = "https://example.com"


@pytest.fixture
async def ctx(tmp_path):
    """Build a FastMCP instance wired to a store-backed OAuth provider."""
    store = DebateStore(db_path=tmp_path / "oauth-endpoints.db")
    await store.initialize()
    provider = PloidyOAuthProvider(store)
    mcp = FastMCP(
        "TestPloidy",
        auth_server_provider=provider,
        auth=AuthSettings(
            issuer_url=_ISSUER,
            resource_server_url=_ISSUER,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=["debate"],
                default_scopes=["debate"],
            ),
            revocation_options=RevocationOptions(enabled=True),
            required_scopes=["debate"],
        ),
    )
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as client:
        yield client, provider, store
    await store.close()


class TestDiscovery:
    """RFC 8414 authorization server metadata."""

    async def test_discovery_returns_expected_endpoints(self, ctx):
        client, _, _ = ctx
        resp = await client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        body = resp.json()
        # Issuer must round-trip exactly so clients trust the discovery doc.
        assert body["issuer"].rstrip("/") == _ISSUER.rstrip("/")
        # Each endpoint is present and lives under the issuer.
        for key in (
            "authorization_endpoint",
            "token_endpoint",
            "registration_endpoint",
            "revocation_endpoint",
        ):
            assert key in body, f"missing {key}"
            assert body[key].startswith(_ISSUER)
        # PKCE S256 must be advertised — Claude.ai rejects servers that omit it.
        assert "S256" in body["code_challenge_methods_supported"]
        # Scopes the client can request.
        assert "debate" in (body.get("scopes_supported") or [])


class TestDynamicClientRegistration:
    """RFC 7591 DCR contract."""

    async def test_register_returns_client_id(self, ctx):
        client, _, _ = ctx
        resp = await client.post(
            "/register",
            json={
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
                "client_name": "Claude.ai",
                "grant_types": ["authorization_code", "refresh_token"],
                "token_endpoint_auth_method": "none",
            },
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body.get("client_id"), "DCR response missing client_id"
        # Echo of submitted fields so the caller can store them.
        assert "https://claude.ai/api/mcp/auth_callback" in [str(u) for u in body["redirect_uris"]]

    async def test_registered_client_is_visible_to_provider(self, ctx):
        client, provider, _ = ctx
        resp = await client.post(
            "/register",
            json={
                "redirect_uris": ["https://claude.com/api/mcp/auth_callback"],
                "client_name": "Claude Web",
                # Omit grant_types so the SDK picks its default
                # (``authorization_code`` + ``refresh_token``); the
                # metadata validator rejects subsets.
            },
        )
        assert resp.status_code in (200, 201)
        client_id = resp.json()["client_id"]
        # The provider can look up what DCR just persisted.
        info = await provider.get_client(client_id)
        assert info is not None
        assert info.client_name == "Claude Web"


class TestProtectedResourceMetadata:
    """RFC 9728 protected resource metadata."""

    async def test_pr_metadata_points_at_issuer(self, ctx):
        client, _, _ = ctx
        resp = await client.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
        body = resp.json()
        # The resource server advertises which AS can issue tokens for it.
        assert _ISSUER.rstrip("/") in " ".join(
            str(v) for v in body.get("authorization_servers", [])
        ) or _ISSUER.rstrip("/") == str(body.get("resource", "")).rstrip("/")


class TestTokenEndpointWiring:
    """The /token endpoint must reject malformed requests at the HTTP layer.

    Happy-path grant exchange is covered end-to-end in
    ``tests/test_oauth_provider.py``; these checks just confirm the
    route is mounted and rejects sensibly without our provider ever
    seeing the call.
    """

    async def test_missing_client_id_is_rejected(self, ctx):
        client, _, _ = ctx
        resp = await client.post(
            "/token",
            data={"grant_type": "password"},
        )
        # SDK authenticates the client before parsing the grant type,
        # so an unauthenticated call lands in ``unauthorized_client``.
        assert resp.status_code in (400, 401)
        body = resp.json()
        assert body["error"] in (
            "unauthorized_client",
            "invalid_client",
            "unsupported_grant_type",
        )

    async def test_unknown_client_id_is_rejected(self, ctx):
        client, _, _ = ctx
        resp = await client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "never-registered",
                "code": "anything",
                "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
                "code_verifier": "ignored",
            },
        )
        assert resp.status_code in (400, 401)
        assert resp.json()["error"] in ("unauthorized_client", "invalid_client")


class TestRevocationWiring:
    async def test_revoke_endpoint_is_mounted(self, ctx):
        # Per the discovery advertisement, revocation must be routable.
        # Content-of-response varies by SDK version and request shape, so
        # we only assert the endpoint exists and does not 404.
        client, _, _ = ctx
        resp = await client.post(
            "/revoke",
            data={"token": "never-issued"},
        )
        assert resp.status_code != 404
