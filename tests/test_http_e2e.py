"""End-to-end HTTP test for the Ploidy MCP server.

Spawns the server with the streamable-http transport, walks a complete
debate over the wire (init → start → join → positions → challenges →
converge → history), and asserts the result. Marked ``slow`` so the
fast unit suite can skip it.

Run only this file:

    pytest tests/test_http_e2e.py -m slow
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import httpx
import pytest

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _free_port() -> int:
    """Pick an unused TCP port for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 10.0) -> None:
    """Block until ``127.0.0.1:port`` accepts TCP connections.

    Loopback ECONNREFUSED returns in <1ms, so a 50ms back-off is plenty
    and keeps the median fixture startup wait under one server tick.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.05)
            try:
                sock.connect(("127.0.0.1", port))
                return
            except OSError:
                time.sleep(0.05)
    raise TimeoutError(f"server did not bind to port {port} within {timeout}s")


def _rpc(base: str, session_id: str | None, method: str, params: dict, req_id: int) -> dict:
    """Send a JSON-RPC request and parse the SSE ``data:`` line."""
    headers = {**HEADERS}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
    with httpx.Client(timeout=10) as client:
        resp = client.post(base, headers=headers, json=body)
    resp.raise_for_status()

    for line in resp.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise AssertionError(f"no SSE data frame in response: {resp.text[:200]}")


def _init_session(base: str, name: str) -> str:
    """Open an MCP session and return the assigned ``Mcp-Session-Id``."""
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            base,
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": name, "version": "0.1"},
                },
            },
        )
    resp.raise_for_status()
    return resp.headers["mcp-session-id"]


def _call_tool(base: str, session_id: str, tool: str, args: dict) -> dict:
    """Invoke an MCP tool and return its decoded JSON payload."""
    data = _rpc(base, session_id, "tools/call", {"name": tool, "arguments": args}, req_id=2)
    text = data["result"]["content"][0]["text"]
    return json.loads(text)


@pytest.fixture
def http_server(tmp_path) -> Iterator[str]:
    """Start a Ploidy server on a free port over streamable-http."""
    port = _free_port()
    db = tmp_path / "ploidy_e2e.db"
    env = {
        **os.environ,
        "PLOIDY_TRANSPORT": "streamable-http",
        "PLOIDY_PORT": str(port),
        "PLOIDY_DB_PATH": str(db),
        "PLOIDY_LOG_LEVEL": "WARNING",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "ploidy"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        _wait_for_port(port)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


@pytest.mark.slow
def test_full_debate_over_http(http_server: str) -> None:
    """Drive a debate end-to-end via the streamable-http MCP transport."""
    deep_sid = _init_session(http_server, "deep")
    fresh_sid = _init_session(http_server, "fresh")
    assert deep_sid and fresh_sid
    assert deep_sid != fresh_sid

    start = _call_tool(
        http_server,
        deep_sid,
        "debate_start",
        {
            "prompt": "Monorepo vs polyrepo for 3 teams, 12 microservices?",
            "context_documents": ["Shared auth lib, cross-team deps"],
        },
    )
    debate_id = start["debate_id"]
    deep_session_id = start["session_id"]
    assert start["role"] == "deep"
    assert start["phase"] == "independent"

    join = _call_tool(http_server, fresh_sid, "debate_join", {"debate_id": debate_id})
    fresh_session_id = join["session_id"]
    assert join["role"] == "fresh"
    assert join["prompt"] == start["prompt"]

    pos1 = _call_tool(
        http_server,
        deep_sid,
        "debate_position",
        {
            "session_id": deep_session_id,
            "content": "Monorepo. Shared auth lib + cross-team deps "
            "= version sync nightmare in polyrepo.",
        },
    )
    assert pos1["status"] == "recorded"
    assert pos1["all_positions_in"] is False
    assert pos1["phase"] == "position"

    pos2 = _call_tool(
        http_server,
        fresh_sid,
        "debate_position",
        {
            "session_id": fresh_session_id,
            "content": "Polyrepo. Independent CI/CD per service. "
            "Monorepo = merge conflicts + slow builds.",
        },
    )
    assert pos2["status"] == "recorded"
    assert pos2["all_positions_in"] is True
    assert pos2["phase"] == "challenge"

    status = _call_tool(http_server, deep_sid, "debate_status", {"debate_id": debate_id})
    assert status["phase"] == "challenge"
    assert status["message_count"] == 2
    assert {s["role"] for s in status["sessions"]} == {"deep", "fresh"}

    ch1 = _call_tool(
        http_server,
        deep_sid,
        "debate_challenge",
        {
            "session_id": deep_session_id,
            "content": "Polyrepo ignores shared auth. 12 repos = 12 PRs per security patch.",
            "action": "challenge",
        },
    )
    assert ch1["action"] == "challenge"

    ch2 = _call_tool(
        http_server,
        fresh_sid,
        "debate_challenge",
        {
            "session_id": fresh_session_id,
            "content": "Extract shared auth as versioned package "
            "on private registry. No monorepo needed.",
            "action": "propose_alternative",
        },
    )
    assert ch2["action"] == "propose_alternative"

    result = _call_tool(http_server, deep_sid, "debate_converge", {"debate_id": debate_id})
    assert result["phase"] == "complete"
    assert isinstance(result["confidence"], (int, float))
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["points"], list)
    assert len(result["points"]) >= 1
    assert result["synthesis"]

    history = _call_tool(http_server, deep_sid, "debate_history", {})
    assert history["total"] >= 1
    assert any(d["id"] == debate_id and d["status"] == "complete" for d in history["debates"])
