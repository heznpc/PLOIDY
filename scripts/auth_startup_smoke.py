#!/usr/bin/env python3
"""Start an installed bearer-auth server and verify an unauthorized 401."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def free_port() -> int:
    """Reserve and return an available loopback TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(url: str, process: subprocess.Popen[str], timeout: float = 20.0) -> None:
    """Wait for the child server's health endpoint or fail with its logs."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise SystemExit(
                f"authenticated server exited early ({process.returncode})\n{stdout}\n{stderr}"
            )
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise SystemExit("authenticated server did not become healthy")


def assert_unauthorized(mcp_url: str) -> None:
    """Assert that an MCP initialize request without a token returns 401."""
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "release-smoke", "version": "0.4.0"},
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        mcp_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return
        raise SystemExit(f"unauthorized MCP request returned {exc.code}, expected 401") from exc
    raise SystemExit("unauthorized MCP request succeeded, expected 401")


def stop_process(process: subprocess.Popen[str]) -> None:
    """Terminate the smoke server without leaving a background process."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    """Launch bearer auth from the installed interpreter and probe it."""
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="ploidy-auth-smoke-") as temp_dir:
        env = os.environ.copy()
        env.pop("PLOIDY_TOKENS", None)
        env.update(
            {
                "PLOIDY_AUTH_MODE": "bearer",
                "PLOIDY_AUTH_TOKEN": "release-smoke-token",
                "PLOIDY_TRANSPORT": "streamable-http",
                "PLOIDY_PORT": str(port),
                "PLOIDY_DB_PATH": str(Path(temp_dir) / "ploidy.db"),
                "PLOIDY_LOG_LEVEL": "WARNING",
            }
        )
        process = subprocess.Popen(
            [sys.executable, "-m", "ploidy"],
            cwd=temp_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            base_url = f"http://127.0.0.1:{port}"
            wait_for_health(f"{base_url}/healthz", process)
            assert_unauthorized(f"{base_url}/mcp")
            print("bearer-auth server started and rejected an unauthenticated MCP request")
        finally:
            stop_process(process)


if __name__ == "__main__":
    main()
