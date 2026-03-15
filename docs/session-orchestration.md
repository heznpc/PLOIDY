# Session Orchestration

How does the "fresh" session actually get created and run? This is the central design question for Ploidy. This page documents the three approaches considered and explains why the Two-Terminal approach was chosen for v0.1.

## The Bootstrapping Problem

Ploidy's thesis is that N sessions of the same model, given intentionally asymmetric context, produce better decisions through structured debate. But a single MCP client cannot simultaneously be both "deep" (full context) and "fresh" (no context). The client has one conversation state, one system prompt, one accumulated context window. You cannot fork it.

Three approaches were analyzed to solve this.

## Three Approaches Compared

| Criterion | MCP Sampling | API Fallback | Two-Terminal |
|-----------|:-----------:|:------------:|:------------:|
| Works today (March 2026) | No | Yes | Yes |
| Context isolation guarantee | Weak (advisory) | Strong (server-controlled) | Strongest (process-level) |
| User setup steps | 1 | 2 (+ API key) | 2 |
| API key required | No | Yes | No |
| API cost per debate | None | ~$0.01--0.10 | None |
| Supports solo developer | Yes | Yes | Yes |
| Supports multi-person team | No | No | Yes |
| Auditable context isolation | No | Yes | Yes |
| Aligned with paper thesis | Poor | Moderate | Strongest |

## v0.1: Two-Terminal (Recommended)

The user runs two MCP client sessions (e.g., two Claude Code terminals). Both connect to the same Ploidy server via Streamable HTTP. The Deep session carries full project context; the Fresh session starts clean.

### How It Works

```
Terminal 1 (Deep Session)                Terminal 2 (Fresh Session)
─────────────────────────                ─────────────────────────
[Has full project context]               [Fresh, no context]

> debate/start
  "debate-id: abc123"
                                         > debate/join abc123
                                           "Prompt: Should we..."
> debate/position
  "I believe we should because..."       > debate/position
                                           "I'm skeptical because..."
> debate/status
  "Fresh says: I'm skeptical..."         > debate/status
                                           "Deep says: I believe..."
> debate/challenge
  "Your skepticism ignores..."           > debate/challenge
                                           "Your confidence assumes..."
> debate/converge
  "Result: {synthesis...}"               > debate/converge
                                           "Result: {synthesis...}"
```

### Why Two-Terminal First

1. **Zero additional cost.** If you have a Claude Max or Gemini Pro subscription, all sessions use existing quota -- no API keys, no per-token billing.

2. **Strongest context isolation.** Each terminal is a completely separate OS process with its own conversation history, system prompt state, context window, and memory. There is no mechanism by which the Fresh session could accidentally access the Deep session's context.

3. **Most aligned with the paper's thesis.** The paper argues for "real cross-session dialogue." The Two-Terminal approach is the only one that delivers this literally -- multiple real sessions, real conversations, mediated by a structured protocol.

4. **Simpler server implementation.** The server does not need to generate LLM responses itself. It only needs to store state, enforce protocol transitions, and coordinate turns.

### Transport Requirement

This approach requires **Streamable HTTP** transport. The stdio transport is 1:1 (one client per server process). For multiple clients to connect to the same server, the server must listen on an HTTP endpoint.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Ploidy", transport="streamable-http", port=8765)
```

## v0.2: API Fallback

Add an API fallback mode for automated / single-terminal use. The server generates Fresh session responses via direct API calls, giving it full control over what context Session B sees.

### How It Works

1. User (via the Deep session) calls `debate/start` with a prompt and their position
2. The server makes a direct API call for the Fresh session -- constructing a message array with *only* the debate prompt
3. The server orchestrates the full debate internally, alternating between the user's input and API-generated responses
4. The user receives the complete debate transcript and convergence result

### Supported Backends

Uses the `openai` SDK with a configurable `base_url`:

| Backend | Base URL | Cost |
|---------|----------|------|
| Ollama | `http://localhost:11434/v1` | Free (local) |
| OpenRouter | `https://openrouter.ai/api/v1` | Variable |
| Anthropic | Via OpenAI-compatible endpoint | Per-token |
| OpenAI | Direct | Per-token |
| Google | Via OpenAI-compatible endpoint | Per-token |

### Context Isolation

The server constructs Session B's message array from scratch. No client intermediary can inject additional context. The server controls exactly what the model sees -- system prompt, message history, everything. The exact payload can be logged for auditability.

### Tradeoffs

- Requires an API key (or local Ollama)
- Per-debate API costs (typically small: ~$0.01--0.10)
- Not truly "cross-session" in the MCP sense -- Session B is a raw API call, not a separate MCP session
- Context isolation is strong but server-controlled, not process-level

## v0.3: MCP Sampling

The MCP specification defines a `sampling/createMessage` request that allows an MCP server to ask the connected client to generate an LLM completion. In theory, this could create Session B within the same client process.

### Why Not Now

As of March 2026:

- **Claude Code does not support MCP sampling.** The feature is tracked but not implemented.
- **Claude Desktop does not support MCP sampling either.**
- The `includeContext` parameter is a *hint*, not a guarantee. The spec states: "The client MAY modify or ignore this field." A client that ignores `includeContext: "none"` would silently destroy context isolation.
- The `systemPrompt` is also advisory.
- Human-in-the-loop requirements mean every sampling request may pause for user approval.

### When to Revisit

When major MCP clients implement sampling with:

- Guaranteed `includeContext` enforcement (not just advisory)
- Verifiable context isolation
- Configurable human-in-the-loop behavior

The `SessionBProvider` abstraction in v0.2 is designed to accommodate a `SamplingProvider` implementation when this becomes viable.

## Why Two-Terminal Before API

The original design analysis rated the Two-Terminal approach's UX as "POOR" due to multi-terminal management. This was reconsidered:

- The two-terminal flow is two commands (`ploidy start` / `ploidy join`), not five steps
- Developers already work with multiple terminals daily
- A slightly higher-friction workflow that delivers **genuine** cross-session debate is better than a lower-friction workflow that simulates it
- The API fallback can always be added later (v0.2) without any architectural changes -- the debate protocol and persistence layer are identical
