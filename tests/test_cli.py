"""Tests for the ploidy-ask terminal CLI.

The CLI drives the SSE endpoint, so the interesting assertions are
around SSE frame parsing and exit-code semantics. The HTTP transport
itself is stubbed via a fake ``httpx.stream`` context.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from ploidy import cli


class _FakeResponse:
    """Minimal stand-in for the object ``httpx.stream`` yields."""

    def __init__(self, status_code: int, frames: list[bytes]):
        self.status_code = status_code
        self._frames = frames

    def read(self) -> bytes:
        return b"".join(self._frames)

    def iter_bytes(self):
        yield from self._frames


def _frame(event_type: str, data: dict) -> bytes:
    payload = json.dumps({"type": event_type, "data": data})
    return f"event: {event_type}\ndata: {payload}\n\n".encode()


def _stream_ctx(response: _FakeResponse):
    ctx = MagicMock()
    ctx.__enter__ = lambda _self: response
    ctx.__exit__ = lambda *_args: False
    return ctx


class TestFrameParsing:
    def test_parses_event_type_and_data(self):
        raw = _frame("phase_started", {"phase": "position"})
        frames = list(cli._iter_sse_frames(iter([raw])))
        assert frames == [("phase_started", {"phase": "position"})]

    def test_multiple_frames_in_one_chunk(self):
        raw = _frame("phase_started", {"phase": "position"}) + _frame(
            "completed", {"confidence": 0.7, "points": 3}
        )
        frames = list(cli._iter_sse_frames(iter([raw])))
        assert [t for t, _ in frames] == ["phase_started", "completed"]

    def test_frame_split_across_chunks(self):
        raw = _frame("positions_generated", {"side": "deep", "count": 1})
        half = len(raw) // 2
        chunks = [raw[:half], raw[half:]]
        frames = list(cli._iter_sse_frames(iter(chunks)))
        assert frames == [("positions_generated", {"side": "deep", "count": 1})]

    def test_malformed_frame_is_skipped(self):
        bad = b"data: not-json\n\n"
        good = _frame("completed", {"confidence": 1.0, "points": 1})
        frames = list(cli._iter_sse_frames(iter([bad + good])))
        assert frames == [("completed", {"confidence": 1.0, "points": 1})]


class TestDescribe:
    def test_completed_formats_confidence_as_pct(self):
        out = cli._describe("completed", {"confidence": 0.72, "points": 3})
        assert "72%" in out
        assert "3 points" in out

    def test_challenges_generated_surfaces_actions(self):
        out = cli._describe(
            "challenges_generated", {"deep_action": "challenge", "fresh_action": "agree"}
        )
        assert "deep=challenge" in out
        assert "fresh=agree" in out


class TestStreamDebate:
    def test_happy_path_returns_rendered_markdown_and_zero(self):
        frames = [
            _frame("phase_started", {"phase": "position"}),
            _frame(
                "result",
                {
                    "rendered_markdown": "## RESULT",
                    "confidence": 0.8,
                    "debate_id": "abc",
                },
            ),
        ]
        fake_resp = _FakeResponse(status_code=200, frames=frames)

        with patch.object(cli, "httpx") as httpx_mod:
            httpx_mod.stream.return_value = _stream_ctx(fake_resp)
            httpx_mod.Timeout = MagicMock()
            httpx_mod.HTTPError = Exception

            md, code = cli._stream_debate("http://x/v1/debate/stream", {"prompt": "p"}, token=None)

        assert code == 0
        assert md == "## RESULT"

    def test_error_frame_returns_code_2(self):
        frames = [
            _frame("phase_started", {"phase": "position"}),
            _frame("error", {"message": "nope", "kind": "BoomError"}),
        ]
        fake_resp = _FakeResponse(status_code=200, frames=frames)

        with patch.object(cli, "httpx") as httpx_mod:
            httpx_mod.stream.return_value = _stream_ctx(fake_resp)
            httpx_mod.Timeout = MagicMock()
            httpx_mod.HTTPError = Exception

            md, code = cli._stream_debate("http://x/v1/debate/stream", {"prompt": "p"}, token=None)

        assert code == 2
        # Without a result frame there's no markdown to print.
        assert md is None

    def test_non_200_status_returns_code_3(self):
        fake_resp = _FakeResponse(status_code=401, frames=[b"unauthorized"])

        with patch.object(cli, "httpx") as httpx_mod:
            httpx_mod.stream.return_value = _stream_ctx(fake_resp)
            httpx_mod.Timeout = MagicMock()
            httpx_mod.HTTPError = Exception

            md, code = cli._stream_debate("http://x/v1/debate/stream", {"prompt": "p"}, token=None)

        assert code == 3
        assert md is None

    def test_missing_httpx_returns_code_3_with_install_hint(self, capsys):
        with patch.object(cli, "httpx", None):
            md, code = cli._stream_debate("http://x", {"prompt": "p"}, token=None)
        captured = capsys.readouterr()
        assert code == 3
        assert md is None
        assert "ploidy[cli]" in captured.err


class TestArgparseWiring:
    def test_url_flag_overrides_env(self):
        # main() calls _stream_debate; we stub it to inspect the endpoint.
        captured: dict = {}

        def fake_stream(url, body, token):
            captured["url"] = url
            captured["body"] = body
            captured["token"] = token
            return ("## OK", 0)

        with patch.object(cli, "_stream_debate", fake_stream):
            code = cli.main(["--url", "http://custom/", "--deep-n", "2", "hello"])

        assert code == 0
        assert captured["url"] == "http://custom/v1/debate/stream"
        assert captured["body"]["prompt"] == "hello"
        assert captured["body"]["deep_n"] == 2
