#!/usr/bin/env python3
"""Smoke-test an installed Ploidy wheel outside the source tree."""

from __future__ import annotations

import asyncio
import os

EXPECTED_TOOLS = {
    "debate",
    "debate_start",
    "debate_join",
    "debate_position",
    "debate_challenge",
    "debate_converge",
    "debate_cancel",
    "debate_delete",
    "debate_status",
    "debate_history",
    "debate_solo",
    "debate_auto",
    "debate_review",
}


async def inspect_tools() -> set[str]:
    """Return the tool names exposed by the installed FastMCP server."""
    from ploidy.server import mcp

    tools = await mcp.list_tools()
    return {tool.name for tool in tools}


def main() -> None:
    """Verify package metadata, imports, console modules, and tool surface."""
    from ploidy import __version__, cli, dashboard, history_cli, retention

    expected_version = os.environ.get("EXPECTED_PLOIDY_VERSION")
    if expected_version and __version__ != expected_version:
        raise SystemExit(f"installed version is {__version__}, expected {expected_version}")

    for module in (cli, dashboard, history_cli, retention):
        if not callable(module.main):
            raise SystemExit(f"{module.__name__}.main is not callable")

    tools = asyncio.run(inspect_tools())
    if tools != EXPECTED_TOOLS:
        missing = sorted(EXPECTED_TOOLS - tools)
        extra = sorted(tools - EXPECTED_TOOLS)
        raise SystemExit(f"tool mismatch: missing={missing}, extra={extra}")
    print(f"ploidy {__version__}: {len(tools)} installed MCP tools")


if __name__ == "__main__":
    main()
