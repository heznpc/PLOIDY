# Architecture

> Updated 2026-03-19 to reflect the v0.2 architecture (Two-Terminal + API auto mode).

## System Overview

Ploidy is an MCP server that orchestrates structured debates between N sessions of the same model with intentionally asymmetric context. It supports two operational modes:

- **Two-Terminal mode (v0.1):** Two MCP client sessions connect to one Ploidy server via Streamable HTTP. Deep session has project context, Fresh session starts clean.
- **Auto mode (v0.2):** A single MCP client calls `debate_auto`. The server generates the opposing session's responses via an OpenAI-compatible API endpoint.

```
Two-Terminal mode                    Auto mode (debate_auto)
──────────────────                   ──────────────────────
Terminal 1 (Deep)   Terminal 2       Terminal 1 (Deep)
[Project context]   [No context]     [Project context]
     |                  |                  |
     |  Streamable HTTP |                  |  Streamable HTTP
     |                  |                  |
     +--------+---------+                  |
              |                            |
       Ploidy Server                Ploidy Server
       (FastMCP, port 8765)         (FastMCP, port 8765)
              |                            |          \
              |                            |           \ OpenAI-compat API
       SQLite (WAL)                 SQLite (WAL)        → Fresh/Semi-Fresh
       ~/.ploidy/ploidy.db          ~/.ploidy/ploidy.db    responses
```

Both terminals connect to `http://localhost:8765/mcp`. In two-terminal mode, the first client is assigned the **Experienced** role, the second is **Fresh** or **Semi-Fresh** (configurable via tool arguments). In auto mode, the server creates both sessions internally.

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

| Role | Context | Delivery Mode | Assignment |
|------|---------|---------------|------------|
| Experienced | Full project history, prior decisions, context documents | N/A | `debate/start` or auto mode |
| Semi-Fresh | Debate prompt + compressed summary of experienced position | `passive` (appended) or `active` (instruction to request) | `debate/join` with `role=semi_fresh` or auto mode |
| Fresh | Only the debate prompt, zero context | `none` | `debate/join` with `role=fresh` or auto mode |

**Two-terminal mode:** Context isolation is enforced at the OS process level -- each terminal is a separate process with its own conversation history. The server sends the Fresh/Semi-Fresh session only its designated context via the `debate/join` response.

**Auto mode:** The server constructs each session's API message array from scratch, ensuring the Fresh session receives only the debate prompt. For Semi-Fresh sessions, the experienced position is compressed and delivered according to the configured delivery mode.

## Debate Flow

### Two-Terminal Mode (manual)

```
1. CREATE      Experienced session calls debate/start with a prompt
               Server creates a debate record, returns debate-id

2. JOIN        Fresh/Semi-Fresh session calls debate/join with the debate-id
               Server assigns role, returns the prompt (+ compressed summary for semi-fresh)

3. ARGUE       All sessions submit positions via debate/position
               All read opponents' positions via debate/status
               All submit challenges via debate/challenge

4. CONVERGE    Any session calls debate/converge
               Server synthesizes positions into a convergence result

5. RECORD      Result is persisted to SQLite
```

### Auto Mode (debate_auto)

A single call to `debate_auto` runs the full protocol:

```
1. CREATE      Server creates debate + experienced session + fresh/semi-fresh session

2. POSITION    Server generates experienced position via API (with context documents)
               For semi-fresh: compresses experienced position, delivers to semi-fresh
               Server generates fresh/semi-fresh position via API

3. CHALLENGE   Server generates challenges from both perspectives via API

4. CONVERGE    Convergence engine analyzes the transcript
               Result persisted to SQLite, debate marked complete

5. CLEANUP     On success: in-memory state cleared
               On failure: debate deleted from DB (best-effort)
```

Auto mode requires `PLOIDY_API_BASE_URL` to be configured. See [session-orchestration.md](session-orchestration.md) for backend options.

## Module Overview

| Module | Role |
|--------|------|
| `server.py` | FastMCP server entry point. Registers 11 debate tools (`debate_start`, `debate_join`, `debate_position`, `debate_challenge`, `debate_converge`, `debate_cancel`, `debate_delete`, `debate_status`, `debate_history`, `debate_auto`, `debate_review`). Handles state recovery on startup and cleanup on completion/failure. |
| `protocol.py` | Debate state machine. Defines phases (`INDEPENDENT`, `POSITION`, `CHALLENGE`, `CONVERGENCE`, `COMPLETE`), valid transitions, and validation rules. |
| `session.py` | Session context. Tracks Experienced/Semi-Fresh/Fresh role, delivery mode (none/passive/active), context documents, and compressed summaries. |
| `convergence.py` | Convergence engine. Rule-based analysis of positions for agreement/disagreement/synthesis. Optional LLM-enhanced meta-analysis via `PLOIDY_LLM_CONVERGENCE`. |
| `api_client.py` | OpenAI-compatible API client for auto mode. Generates positions, challenges, and compressions via configurable `PLOIDY_API_BASE_URL` endpoint. |
| `dashboard.py` | Lightweight ASGI web dashboard for debate history visualization. Read-only DB access. |
| `store.py` | SQLite persistence layer (via `aiosqlite`). Stores debates, sessions (with context fields), messages, and convergence results. WAL mode, schema migrations for older databases. |
| `exceptions.py` | Domain-specific exceptions (`PloidyError`, `ProtocolError`, `ConvergenceError`, `SessionError`). |

## Database Schema

Ploidy uses SQLite with WAL (Write-Ahead Logging) mode for concurrent access from multiple MCP clients.

```sql
-- Debate metadata
CREATE TABLE debates (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- active | complete | cancelled
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Session contexts and roles
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    debate_id TEXT NOT NULL REFERENCES debates(id),
    role TEXT NOT NULL,                              -- experienced | semi_fresh | fresh
    base_prompt TEXT NOT NULL,
    context_documents TEXT NOT NULL DEFAULT '[]',     -- JSON array of document strings
    delivery_mode TEXT NOT NULL DEFAULT 'none',       -- none | passive | active
    compressed_summary TEXT,                          -- compressed experienced position (semi-fresh)
    metadata_json TEXT NOT NULL DEFAULT '{}',         -- extensible JSON metadata
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

-- Indexes
CREATE INDEX idx_debates_status ON debates(status);
CREATE INDEX idx_sessions_debate_id ON sessions(debate_id);
CREATE INDEX idx_messages_debate_id ON messages(debate_id);
```

Older databases are automatically migrated: `store.py` checks for missing session columns on startup and adds them via `ALTER TABLE`.

### SQLite Concurrency

WAL mode allows concurrent readers with a single writer. The debate protocol's turn-based structure naturally serializes writes -- sessions rarely write simultaneously.

```python
await db.execute("PRAGMA journal_mode=WAL")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLOIDY_PORT` | Server port | `8765` |
| `PLOIDY_DB_PATH` | SQLite database path | `~/.ploidy/ploidy.db` |
| `PLOIDY_API_BASE_URL` | OpenAI-compatible API base URL (required for auto mode) | — |
| `PLOIDY_API_KEY` | API key (or `"ollama"` for local) | — |
| `PLOIDY_MODEL` | Model identifier for API calls | — |
| `PLOIDY_LLM_CONVERGENCE` | Enable LLM-enhanced convergence meta-analysis (`1`/`true`) | disabled |
| `PLOIDY_AUTH_TOKEN` | Optional bearer token for server authentication | — |
| `PLOIDY_MAX_PROMPT_LEN` | Max prompt length | `10000` |
| `PLOIDY_MAX_CONTENT_LEN` | Max content length per message | `50000` |
| `PLOIDY_MAX_CONTEXT_DOCS` | Max context documents per session | `10` |
| `PLOIDY_MAX_SESSIONS` | Max sessions per debate | `5` |
| `PLOIDY_LOG_LEVEL` | Logging level | `INFO` |

## Roadmap

### v0.1: Two-Terminal (done)

Two MCP client sessions connect to one Ploidy server via Streamable HTTP. Zero additional cost for subscription-based AI clients.

### v0.2: API Auto Mode + Semi-Fresh Sessions (current)

- `debate_auto` tool: single-call automated debates via OpenAI-compatible API
- Semi-Fresh sessions with passive/active delivery modes
- LLM-enhanced convergence meta-analysis (optional)
- Web dashboard for debate history visualization
- Session context persistence (context_documents, delivery_mode, compressed_summary)
- Failure cleanup: auto-debates that fail mid-flow are deleted from DB

### v0.3+: MCP Sampling

When major MCP clients support `sampling/createMessage` with strong context isolation guarantees, add a sampling-based provider as the lowest-friction option. The server will auto-detect client sampling capability during initialization and use it when available.
