"""Provider-level tests for ``PloidyOAuthProvider`` (slice 2).

The provider is store-backed, so every test talks to a real
``DebateStore`` against a tmp SQLite file — there is no mock layer
between the provider and the OAuth tables. Tests that would normally
go through FastMCP's handlers (PKCE verification, response shape)
invoke the provider methods directly.
"""

from __future__ import annotations

import pytest
from mcp.server.auth.provider import (
    AuthorizationParams,
    RegistrationError,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull

from ploidy.oauth import PloidyOAuthProvider
from ploidy.store import DebateStore


@pytest.fixture
async def provider(tmp_path):
    store = DebateStore(db_path=tmp_path / "oauth-p.db")
    await store.initialize()
    try:
        yield PloidyOAuthProvider(store)
    finally:
        await store.close()


def _client(
    client_id: str = "cli-1",
    redirect_uris=("https://claude.ai/api/mcp/auth_callback",),
) -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret=None,
        redirect_uris=list(redirect_uris),
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
        client_name="Test Client",
    )


def _params(redirect_uri: str = "https://claude.ai/api/mcp/auth_callback") -> AuthorizationParams:
    return AuthorizationParams(
        state="xyz",
        scopes=["debate"],
        code_challenge="stored-challenge",
        redirect_uri=redirect_uri,
        redirect_uri_provided_explicitly=True,
    )


class TestClientRegistration:
    async def test_register_then_get_roundtrips(self, provider):
        await provider.register_client(_client())
        got = await provider.get_client("cli-1")
        assert got is not None
        assert got.client_id == "cli-1"
        # Stored redirect URIs round-trip as strings; pydantic wraps them
        # back into AnyUrl on the way out.
        assert "claude.ai" in str(got.redirect_uris[0])

    async def test_get_unknown_client_returns_none(self, provider):
        assert await provider.get_client("ghost") is None

    async def test_register_without_client_id_raises(self, provider):
        info = _client(client_id="")
        info.client_id = None  # simulate DCR request without id
        with pytest.raises(RegistrationError):
            await provider.register_client(info)

    async def test_register_without_redirect_uris_raises(self, provider):
        info = _client()
        info.redirect_uris = []
        with pytest.raises(RegistrationError):
            await provider.register_client(info)


class TestAuthorizeAndCodeLoad:
    async def test_authorize_returns_redirect_with_code_and_state(self, provider):
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        assert url.startswith("https://claude.ai/api/mcp/auth_callback")
        assert "code=" in url
        assert "state=xyz" in url

    async def test_load_unknown_code_returns_none(self, provider):
        await provider.register_client(_client())
        assert await provider.load_authorization_code(_client(), "never-issued") is None

    async def test_load_code_for_wrong_client_returns_none(self, provider):
        await provider.register_client(_client("cli-1"))
        await provider.register_client(_client("cli-2"))
        url = await provider.authorize(_client("cli-1"), _params())
        code = url.split("code=")[1].split("&")[0]
        assert await provider.load_authorization_code(_client("cli-2"), code) is None

    async def test_load_code_reads_back_pkce_challenge(self, provider):
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        code = url.split("code=")[1].split("&")[0]
        loaded = await provider.load_authorization_code(_client(), code)
        assert loaded is not None
        assert loaded.code_challenge == "stored-challenge"
        assert loaded.scopes == ["debate"]


class TestExchangeAuthorizationCode:
    async def _issue(self, provider):
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        code = url.split("code=")[1].split("&")[0]
        return await provider.load_authorization_code(_client(), code)

    async def test_happy_path_returns_bearer_with_refresh(self, provider):
        ac = await self._issue(provider)
        token = await provider.exchange_authorization_code(_client(), ac)
        assert token.token_type == "Bearer"
        assert token.access_token
        assert token.refresh_token
        assert token.expires_in is not None
        assert token.expires_in > 0
        assert token.scope == "debate"

    async def test_code_is_single_use(self, provider):
        ac = await self._issue(provider)
        await provider.exchange_authorization_code(_client(), ac)
        # Second exchange with the same code must fail — this is the
        # core PKCE replay defence guaranteed by the atomic consume.
        with pytest.raises(TokenError) as exc:
            await provider.exchange_authorization_code(_client(), ac)
        assert exc.value.error == "invalid_grant"

    async def test_code_issued_to_different_client_is_rejected(self, provider):
        await provider.register_client(_client("cli-1"))
        await provider.register_client(_client("cli-2"))
        url = await provider.authorize(_client("cli-1"), _params())
        code = url.split("code=")[1].split("&")[0]
        # Craft an AuthorizationCode that claims to belong to cli-1 but
        # the request arrives for cli-2. The store-side check rejects.
        ac = await provider.load_authorization_code(_client("cli-1"), code)
        with pytest.raises(TokenError) as exc:
            await provider.exchange_authorization_code(_client("cli-2"), ac)
        assert exc.value.error == "invalid_grant"

    async def test_exchange_issues_usable_access_token(self, provider):
        ac = await self._issue(provider)
        token = await provider.exchange_authorization_code(_client(), ac)
        loaded = await provider.load_access_token(token.access_token)
        assert loaded is not None
        assert loaded.client_id == "cli-1"
        assert loaded.scopes == ["debate"]


class TestRefreshFlow:
    async def _issue_refresh(self, provider):
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        code = url.split("code=")[1].split("&")[0]
        ac = await provider.load_authorization_code(_client(), code)
        token = await provider.exchange_authorization_code(_client(), ac)
        refresh = await provider.load_refresh_token(_client(), token.refresh_token)
        return token, refresh

    async def test_happy_path_rotates_access_and_refresh(self, provider):
        token, refresh = await self._issue_refresh(provider)
        new_token = await provider.exchange_refresh_token(_client(), refresh, ["debate"])
        assert new_token.access_token != token.access_token
        assert new_token.refresh_token != token.refresh_token
        # Old refresh must be unusable after rotation.
        stale = await provider.load_refresh_token(_client(), refresh.token)
        assert stale is None

    async def test_widening_scope_rejected(self, provider):
        _token, refresh = await self._issue_refresh(provider)
        # Original grant is ``debate``; asking for ``debate admin`` is an
        # escalation and must fail with ``invalid_scope``.
        with pytest.raises(TokenError) as exc:
            await provider.exchange_refresh_token(_client(), refresh, ["debate", "admin"])
        assert exc.value.error == "invalid_scope"

    async def test_load_refresh_token_rejects_access_token(self, provider):
        token, _refresh = await self._issue_refresh(provider)
        # Passing an access token where a refresh is expected must return
        # None — mixing kinds would let an access token be used long
        # after its expiry via the refresh path.
        assert await provider.load_refresh_token(_client(), token.access_token) is None

    async def test_load_refresh_token_rejects_other_client(self, provider):
        _token, refresh = await self._issue_refresh(provider)
        other = _client("cli-other")
        assert await provider.load_refresh_token(other, refresh.token) is None


class TestAccessTokenResolutionAndRevocation:
    async def test_load_access_token_filters_refresh_tokens(self, provider):
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        code = url.split("code=")[1].split("&")[0]
        ac = await provider.load_authorization_code(_client(), code)
        token = await provider.exchange_authorization_code(_client(), ac)
        # Passing the refresh token to load_access_token must return None
        # even though the token value exists in the DB.
        assert await provider.load_access_token(token.refresh_token) is None

    async def test_load_access_token_unknown_returns_none(self, provider):
        assert await provider.load_access_token("never-issued") is None

    async def test_revoke_access_token_makes_it_unresolvable(self, provider):
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        code = url.split("code=")[1].split("&")[0]
        ac = await provider.load_authorization_code(_client(), code)
        token = await provider.exchange_authorization_code(_client(), ac)
        loaded = await provider.load_access_token(token.access_token)
        await provider.revoke_token(loaded)
        assert await provider.load_access_token(token.access_token) is None

    async def test_revoke_is_idempotent(self, provider):
        # Revoking twice must not raise — operators retry on transient failures.
        await provider.register_client(_client())
        url = await provider.authorize(_client(), _params())
        code = url.split("code=")[1].split("&")[0]
        ac = await provider.load_authorization_code(_client(), code)
        token = await provider.exchange_authorization_code(_client(), ac)
        loaded = await provider.load_access_token(token.access_token)
        await provider.revoke_token(loaded)
        await provider.revoke_token(loaded)  # second call is silent no-op
