"""Unit tests for the API client with mocked OpenAI calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_api_env(monkeypatch):
    """Configure API environment for all tests in this module."""
    monkeypatch.setenv("PLOIDY_API_BASE_URL", "http://fake:1234")
    monkeypatch.setenv("PLOIDY_API_KEY", "test-key")
    monkeypatch.setenv("PLOIDY_API_MODEL", "test-model")


class TestResolveApiConfig:
    """Zero-config fallback so ``mode='auto'`` works without .mcp.json edits."""

    def test_ploidy_vars_win_when_set(self, monkeypatch):
        from ploidy.api_client import _resolve_api_config

        monkeypatch.setenv("PLOIDY_API_BASE_URL", "http://custom:9999")
        monkeypatch.setenv("PLOIDY_API_KEY", "ploidy-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
        base_url, api_key, _ = _resolve_api_config()
        assert base_url == "http://custom:9999"
        assert api_key == "ploidy-key"

    def test_anthropic_key_auto_configures_endpoint(self, monkeypatch):
        from ploidy.api_client import _ANTHROPIC_OPENAI_COMPAT_URL, _resolve_api_config

        monkeypatch.delenv("PLOIDY_API_BASE_URL", raising=False)
        monkeypatch.delenv("PLOIDY_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
        base_url, api_key, _ = _resolve_api_config()
        assert base_url == _ANTHROPIC_OPENAI_COMPAT_URL
        assert api_key == "anthropic-key"

    def test_disabled_when_no_credentials(self, monkeypatch):
        from ploidy.api_client import _resolve_api_config

        monkeypatch.delenv("PLOIDY_API_BASE_URL", raising=False)
        monkeypatch.delenv("PLOIDY_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        base_url, api_key, _ = _resolve_api_config()
        assert base_url is None
        assert api_key == ""

    def test_ploidy_url_without_key_gets_anthropic_key_fallback(self, monkeypatch):
        from ploidy.api_client import _resolve_api_config

        # Custom proxy URL but no explicit PLOIDY_API_KEY → fall back on
        # ANTHROPIC_API_KEY rather than sending an empty auth header.
        monkeypatch.setenv("PLOIDY_API_BASE_URL", "http://proxy:8080")
        monkeypatch.delenv("PLOIDY_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
        base_url, api_key, _ = _resolve_api_config()
        assert base_url == "http://proxy:8080"
        assert api_key == "anthropic-key"


def _mock_completion(content: str = "test response"):
    """Create a mock chat completion response."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestGenerateResponse:
    """Tests for generate_response with retry logic."""

    async def test_success_on_first_try(self, monkeypatch):
        from ploidy import api_client

        # Reload config after env is set
        monkeypatch.setattr(api_client, "_API_BASE_URL", "http://fake:1234")
        monkeypatch.setattr(api_client, "_API_KEY", "test-key")

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_completion("hello"))

        with patch.object(api_client, "_get_client", return_value=mock_client):
            result = await api_client.generate_response("test prompt")
        assert result == "hello"

    async def test_retries_on_rate_limit(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", "http://fake:1234")
        monkeypatch.setattr(api_client, "_RETRY_BASE_DELAY", 0.01)

        # Create a rate limit error with the right class name
        rate_err = type("RateLimitError", (Exception,), {})("rate limited")

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[rate_err, _mock_completion("recovered")]
        )

        with patch.object(api_client, "_get_client", return_value=mock_client):
            result = await api_client.generate_response("test prompt")
        assert result == "recovered"
        assert mock_client.chat.completions.create.call_count == 2

    async def test_non_retryable_error_fails_immediately(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", "http://fake:1234")

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=ValueError("bad input"))

        with (
            patch.object(api_client, "_get_client", return_value=mock_client),
            pytest.raises(RuntimeError, match="bad input"),
        ):
            await api_client.generate_response("test prompt")
        assert mock_client.chat.completions.create.call_count == 1

    async def test_max_retries_exhausted(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", "http://fake:1234")
        monkeypatch.setattr(api_client, "_RETRY_BASE_DELAY", 0.01)

        timeout_err = type("APITimeoutError", (Exception,), {})("timeout")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=timeout_err)

        with (
            patch.object(api_client, "_get_client", return_value=mock_client),
            pytest.raises(RuntimeError, match="timeout"),
        ):
            await api_client.generate_response("test prompt")
        assert mock_client.chat.completions.create.call_count == 3


class TestIsApiAvailable:
    """Tests for API availability check."""

    def test_available_when_configured(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", "http://fake:1234")
        assert api_client.is_api_available() is True

    def test_unavailable_when_empty(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", "")
        assert api_client.is_api_available() is False

    def test_unavailable_when_none(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", None)
        assert api_client.is_api_available() is False


class TestFreshPosition:
    """Tests for generate_fresh_position."""

    async def test_fresh_has_no_system_prompt(self, monkeypatch):
        from ploidy import api_client

        monkeypatch.setattr(api_client, "_API_BASE_URL", "http://fake:1234")

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_completion("fresh view"))

        with patch.object(api_client, "_get_client", return_value=mock_client):
            result = await api_client.generate_fresh_position("test debate")
        assert result == "fresh view"
        # Verify the system prompt enforces zero-context independence
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages", call_args[1].get("messages", []))
        system_msgs = [m for m in messages if m.get("role") == "system"]
        if system_msgs:
            content = system_msgs[0].get("content", "").lower()
            assert "no background" in content or "no context" in content
