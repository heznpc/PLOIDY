"""End-to-end HTTP test for the Ploidy MCP server.

Starts the server, runs a full debate via HTTP, and verifies results.
"""

import json
import subprocess
import sys
import time

import httpx

BASE = "http://localhost:8765/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def rpc(session_id: str | None, method: str, params: dict, req_id: int = 1) -> dict:
    """Send a JSON-RPC request and parse the SSE response."""
    headers = {**HEADERS}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

    with httpx.Client(timeout=10) as client:
        resp = client.post(BASE, headers=headers, json=body)

    # Parse SSE: find "data: {...}" line
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise ValueError(f"No data in response: {resp.text[:200]}")


def init_session(name: str) -> str:
    """Initialize an MCP session, return the Mcp-Session-Id."""
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            BASE,
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
    return resp.headers["mcp-session-id"]


def call_tool(session_id: str, tool: str, args: dict) -> dict:
    """Call an MCP tool and return the parsed result."""
    data = rpc(session_id, "tools/call", {"name": tool, "arguments": args}, req_id=2)
    text = data["result"]["content"][0]["text"]
    return json.loads(text)


def main():
    # Start server
    proc = subprocess.Popen(
        [sys.executable, "-m", "ploidy"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)

    try:
        # 1. Init sessions
        deep_sid = init_session("deep")
        fresh_sid = init_session("fresh")
        print(f"Deep MCP session:  {deep_sid[:16]}...")
        print(f"Fresh MCP session: {fresh_sid[:16]}...")

        # 2. Start debate
        start = call_tool(
            deep_sid,
            "debate_start",
            {
                "prompt": "Monorepo vs polyrepo for 3 teams, 12 microservices?",
                "context_documents": ["Shared auth lib, cross-team deps"],
            },
        )
        debate_id = start["debate_id"]
        exp_id = start["session_id"]
        print(f"\nDebate started: {debate_id}")
        print(f"Experienced session: {exp_id}")

        # 3. Fresh joins
        join = call_tool(fresh_sid, "debate_join", {"debate_id": debate_id})
        fresh_id = join["session_id"]
        print(f"Fresh session: {fresh_id}")
        print(f"Fresh sees prompt: {join['prompt'][:50]}...")

        # 4. Positions
        pos1 = call_tool(
            deep_sid,
            "debate_position",
            {
                "session_id": exp_id,
                "content": "Monorepo. Shared auth lib + cross-team deps "
                "= version sync nightmare in polyrepo.",
            },
        )
        print(f"\nExp position: phase={pos1['phase']}, all_in={pos1['all_positions_in']}")

        pos2 = call_tool(
            fresh_sid,
            "debate_position",
            {
                "session_id": fresh_id,
                "content": "Polyrepo. Independent CI/CD per service. "
                "Monorepo = merge conflicts + slow builds.",
            },
        )
        print(f"Fresh position: phase={pos2['phase']}, all_in={pos2['all_positions_in']}")

        # 5. Status
        status = call_tool(deep_sid, "debate_status", {"debate_id": debate_id})
        print(f"\nStatus: phase={status['phase']}, messages={status['message_count']}")
        for s in status["sessions"]:
            print(f"  {s['role']}: {s['session_id'][:24]}...")

        # 6. Challenges
        ch1 = call_tool(
            deep_sid,
            "debate_challenge",
            {
                "session_id": exp_id,
                "content": "Polyrepo ignores shared auth. 12 repos = 12 PRs per security patch.",
                "action": "challenge",
            },
        )
        print(f"\nExp challenge: action={ch1['action']}")

        ch2 = call_tool(
            fresh_sid,
            "debate_challenge",
            {
                "session_id": fresh_id,
                "content": "Extract shared auth as versioned package "
                "on private registry. No monorepo needed.",
                "action": "propose_alternative",
            },
        )
        print(f"Fresh challenge: action={ch2['action']}")

        # 7. Converge
        result = call_tool(deep_sid, "debate_converge", {"debate_id": debate_id})
        print(f"\n{'=' * 60}")
        print("CONVERGENCE RESULT")
        print(f"{'=' * 60}")
        print(f"Phase: {result['phase']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Points: {len(result['points'])}")
        for p in result["points"]:
            print(f"  [{p['category']}] {p['summary'][:80]}")
        print(f"\n{result['synthesis']}")

        # 8. History
        history = call_tool(deep_sid, "debate_history", {})
        print(f"\n{'=' * 60}")
        print(f"DEBATE HISTORY: {history['total']} debate(s)")
        for d in history["debates"]:
            print(f"  [{d['status']}] {d['id']}: {d['prompt'][:50]}")

        print(f"\n{'=' * 60}")
        print("E2E TEST PASSED")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
