# Architecture

> Updated 2026-03-15 to reflect the v0.1 Two-Terminal architecture.

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
              ~/.ploidy/ploidy.db
```

Both terminals connect to `http://localhost:8765/mcp`. The server identifies sessions by connection order: the first client is assigned the **Deep** role, the second is assigned the **Fresh** role. This is configurable via tool arguments.

## Transport: Streamable HTTP

Ploidy uses **Streamable HTTP** transport, not stdio. The stdio transport is 1:1 -- one client per server process. For multiple clients to share a single debate, the server must accept multiple concurrent connections over HTTP.

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
| `protocol.py` | Debate state machine. Defines phases (`INDEPENDENT`, `POSITION`, `CHALLENGE`, `CONVERGENCE`, `COMPLETE`), valid transitions, and validation rules. |
| `session.py` | Session lifecycle management. Tracks Deep/Fresh role assignment, connection state, context metadata. |
| `convergence.py` | Convergence engine. Analyzes positions for agreement, disagreement, and synthesis. Produces structured `ConvergenceResult`. |
| `store.py` | SQLite persistence layer (via `aiosqlite`). Stores debates, sessions, messages, and convergence results. Uses WAL mode for concurrent access. |
| `exceptions.py` | Domain-specific exceptions (`PloidyError`, `ProtocolError`, `ConvergenceError`, `SessionError`). |

## Database Schema

Ploidy uses SQLite with WAL (Write-Ahead Logging) mode for concurrent access from multiple MCP clients.

```sql
-- Debate metadata
CREATE TABLE debates (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Session contexts and roles
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    debate_id TEXT NOT NULL REFERENCES debates(id),
    role TEXT NOT NULL,
    base_prompt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Individual debate messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id TEXT NOT NULL REFERENCES debates(id),
    session_id TEXT NOT NULL REFERENCES sessions(id),
    phase TEXT NOT NULL,
    content TEXT NOT NULL,
    action TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Convergence results
CREATE TABLE convergence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id TEXT NOT NULL UNIQUE REFERENCES debates(id),
    synthesis TEXT NOT NULL,
    confidence REAL NOT NULL,
    points_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### SQLite Concurrency

WAL mode allows concurrent readers with a single writer. The debate protocol's turn-based structure naturally serializes writes -- sessions rarely write simultaneously.

```python
await db.execute("PRAGMA journal_mode=WAL")
```

## Roadmap

### v0.1: Two-Terminal (Current)

The primary mode. Two MCP client sessions connect to one Ploidy server via Streamable HTTP. The Deep session carries full project context; the Fresh session starts clean. Zero additional cost for Claude Max / Gemini Pro subscribers.

### v0.2: API Fallback

Add an OpenAI-compatible API fallback for automated / single-terminal use. The server generates Fresh session responses via direct API calls using the `openai` SDK with configurable `base_url`. Supports Ollama (free, local), OpenRouter, Anthropic, OpenAI, Google.

Environment variables:

| Variable | Description |
|----------|-------------|
| `PLOIDY_API_BASE` | Base URL for the OpenAI-compatible endpoint |
| `PLOIDY_API_KEY` | API key (or `"ollama"` for local) |
| `PLOIDY_MODEL` | Model identifier |

### v0.3+: MCP Sampling

When major MCP clients support `sampling/createMessage` with strong context isolation guarantees, add a sampling-based provider as the lowest-friction option. The server will auto-detect client sampling capability during initialization and use it when available.
