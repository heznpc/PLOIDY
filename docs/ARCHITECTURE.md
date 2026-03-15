# Architecture

> Updated 2026-03-15 to reflect the v0.1 Two-Terminal decision.

## System Overview

Ploidy is an MCP server that orchestrates structured debates between N sessions of the same model with intentionally asymmetric context. In v0.1, the sessions are independent MCP client processes (e.g., two Claude Code terminals) connected to the same Ploidy server via Streamable HTTP.

```
Terminal 1 (Deep)              Terminal 2 (Fresh)
[Full project context]         [No prior context]
        |                              |
        |  MCP (Streamable HTTP)       |  MCP (Streamable HTTP)
        |                              |
        +----------- + ---------------+
                     |
              Ploidy Server
              (FastMCP, port 8765)
                     |
                     |
              SQLite (WAL mode)
              ~/.ploidy/debates.db
```

Both terminals connect to `http://localhost:8765/mcp`. The server identifies sessions by connection order: the first client is assigned the **Deep** role, the second is assigned the **Fresh** role. This is configurable via tool arguments.

## Transport

**Streamable HTTP** (not stdio). The stdio transport is 1:1 -- one client per server process. For multiple clients to share a single debate, the server must accept multiple concurrent connections over HTTP.

```python
mcp = FastMCP("Ploidy", transport="streamable-http", port=8765)
```

MCP client configuration (e.g., Claude Code `mcp.json`):
```json
{
  "ploidy": {
    "type": "streamable-http",
    "url": "http://localhost:8765/mcp"
  }
}
```

## Session Management

| Role | Context | Assignment |
|------|---------|------------|
| Deep | Full project history, prior decisions, accumulated assumptions | First client to connect, or explicitly via `debate/start` |
| Fresh | Only the debate prompt, no project context | Second client, via `debate/join` |

The server does not inject or strip context from the client. Context isolation is enforced at the OS process level -- each terminal is a separate process with its own conversation history. The server sends the Fresh session only the debate prompt via the `debate/join` response.

## Debate Flow

```
1. CREATE      Deep session calls debate/start with a prompt
               Server creates a debate record, returns debate-id

2. JOIN        Fresh session calls debate/join with the debate-id
               Server assigns Fresh role, returns the prompt (only)

3. ARGUE       All sessions submit positions via debate/position
               All read opponents' positions via debate/status
               All submit challenges via debate/challenge
               (Repeat for configurable number of rounds)

4. CONVERGE    Any session calls debate/converge
               Server synthesizes positions into a convergence result

5. RECORD      Result is persisted to SQLite
               Optionally appended to DECISIONS.md in the project
```

## Module Overview

| Module | Role |
|--------|------|
| `server.py` | FastMCP server entry point. Registers all debate tools (`debate/start`, `debate/join`, `debate/position`, `debate/challenge`, `debate/status`, `debate/converge`). Handles Streamable HTTP transport. |
| `protocol.py` | Debate state machine. Defines phases (CREATED, POSITIONS, CHALLENGE, CONVERGENCE, COMPLETE), valid transitions, and validation rules. |
| `session.py` | Session lifecycle management. Tracks Deep/Fresh role assignment, connection state, context metadata. |
| `convergence.py` | Convergence engine. Analyzes positions for agreement, disagreement, and synthesis. Produces structured `ConvergenceResult`. |
| `store.py` | SQLite persistence layer (via `aiosqlite`). Stores debates, sessions, messages, and convergence results. Uses WAL mode for concurrent access. |
| `exceptions.py` | Domain-specific exceptions (`DebateNotFound`, `InvalidPhaseTransition`, `SessionRoleConflict`, etc.). |

## SQLite Concurrency

With multiple clients writing to the same database, WAL (Write-Ahead Logging) mode is essential:

```python
await db.execute("PRAGMA journal_mode=WAL")
```

WAL allows concurrent readers with a single writer. The debate protocol's turn-based structure naturally serializes writes -- sessions rarely write simultaneously.

## Future Roadmap

### v0.2: API Fallback

Add an OpenAI-compatible API fallback for automated/single-terminal use. The server generates Fresh session responses via direct API calls using the `openai` SDK with configurable `base_url`. Supports Ollama (free), OpenRouter, Anthropic, OpenAI, Google.

Environment variables: `PLOIDY_API_BASE`, `PLOIDY_API_KEY`, `PLOIDY_MODEL`.

### v0.3+: MCP Sampling

When major MCP clients support `sampling/createMessage` with strong context isolation guarantees, add a sampling-based provider as the lowest-friction option.

## References

- [MCP Specification: Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [MCP Specification: Sampling](https://modelcontextprotocol.io/specification/draft/client/sampling)
- [Session B Orchestration Design Document](./SESSION_B_ORCHESTRATION.md) -- Full analysis of all three approaches
