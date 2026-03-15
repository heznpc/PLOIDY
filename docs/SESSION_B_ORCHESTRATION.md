# Session B Orchestration: Design Document

> How does the "fresh" session actually get created and run?

## The Problem

Ploidy's thesis is that N sessions of the same model, given intentionally asymmetric context, produce better decisions through structured debate. Session A carries full project context. Session B starts fresh with minimal context. They debate, and the disagreements are interpretable because context is the only variable.

But there is a fundamental bootstrapping problem: a single MCP client (e.g., Claude Code) cannot simultaneously be both "deep" (full context) and "fresh" (no context). The client has one conversation state, one system prompt, one accumulated context window. You cannot fork it.

This document analyzes three approaches to creating and running Session B, recommends one for initial implementation, and defines a migration path.

---

## Approach A: MCP Sampling

### How It Would Work

The MCP specification defines a `sampling/createMessage` request that allows an MCP server to ask the connected client to generate an LLM completion. The server provides:

- `messages`: The conversation history to send to the LLM
- `systemPrompt`: An optional system prompt for the request
- `modelPreferences`: Hints for model selection (cost, speed, intelligence priorities)
- `includeContext`: One of `"none"`, `"thisServer"`, or `"allServers"`
- `maxTokens`, `temperature`, `stopSequences`, `metadata`

In theory, Ploidy could use this mechanism to simulate Session B:

1. User (via Session A) calls `debate/start` tool
2. Inside the tool handler, the server calls `ctx.session.create_message()` with:
   - `includeContext: "none"` to prevent the client's accumulated context from leaking in
   - A `systemPrompt` crafted for the "fresh" role
   - The debate prompt as the sole user message
3. The client's LLM generates a response as Session B
4. The server captures this response and feeds it into the debate protocol
5. Repeat for each debate phase (challenge, convergence)

```python
# Conceptual code -- what this would look like in the server
@mcp.tool()
async def debate_start(prompt: str, ctx: Context) -> str:
    # Session A's position comes from the calling client naturally
    session_a_position = await get_session_a_position(prompt, ctx)

    # Session B via sampling -- ask the SAME client to generate
    # but with different context
    session_b_result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"You are a fresh analyst. No prior context. "
                         f"Analyze this decision:\n\n{prompt}"
                ),
            )
        ],
        max_tokens=2000,
        include_context="none",
        system_prompt="You have no prior knowledge of this project. "
                      "Question every assumption.",
    )
    # ... feed both positions into debate protocol
```

### Analysis

**1. Technical Feasibility: POOR**

This is the critical blocker. As of March 2026:

- **Claude Code does not support MCP sampling.** There is an open feature request (anthropics/claude-code#1785) but no implementation. When the server calls `create_message()`, Claude Code will reject the request.
- **Claude Desktop does not support MCP sampling either.** Same situation.
- The MCP spec defines sampling as an optional client capability. Clients declare support via `capabilities.sampling` during initialization. No major Anthropic client currently declares this.
- Some third-party clients (Cline, some custom implementations) have experimental sampling support, but these are not the target deployment environment for Ploidy.

Even if sampling were supported, there are protocol-level concerns:

- The `includeContext` parameter is a *hint*, not a guarantee. The spec explicitly states: "The client MAY modify or ignore this field without communicating this to the server." A client that ignores `includeContext: "none"` and injects the full conversation history would destroy context isolation silently.
- The `systemPrompt` is also advisory. The spec states: "The client MAY modify or ignore this field."
- Human-in-the-loop requirements mean every sampling request may pause for user approval, making multi-turn debates painfully slow.

**2. Context Isolation Guarantee: WEAK**

The server cannot verify what context the client actually included. The `includeContext` field is advisory. The `systemPrompt` is advisory. The client controls everything. The server receives only the final text response -- it has no way to audit whether the response was generated with fresh context or with the full conversation history leaking through.

This is a fundamental architectural mismatch. Ploidy's thesis depends on *guaranteed* context asymmetry. MCP sampling provides, at best, *requested* context asymmetry with no verification mechanism.

**3. User Experience: MIXED**

If it worked and human-in-the-loop were configurable:
- Single command to start a debate (good)
- No API keys needed (good)
- But: user would see repeated approval popups for each sampling request (bad)
- But: the "debate" would be the same model talking to itself through the client, which may feel artificial

**4. Dependency Requirements: MINIMAL**

Only the `mcp` SDK is needed. No additional API keys or services.

**5. Alignment with Paper's Thesis: POOR**

The paper argues for "cross-session" context asymmetry. MCP sampling is fundamentally single-session -- the same client, the same conversation, with the server trying to trick the model into pretending it has different context. The model's weights still carry whatever priming happened earlier in the conversation. Even with `includeContext: "none"`, the client's LLM may have been influenced by prior turns in ways that are not captured in the explicit context window.

This is simulated asymmetry, not real asymmetry.

### Verdict: Not viable for v0.1. Revisit when major clients implement sampling with strong context isolation guarantees.

---

## Approach B: Subprocess / Direct API Call

### How It Would Work

The Ploidy MCP server, during a tool call, directly invokes an LLM API (Anthropic, OpenAI, or other) to generate Session B's responses. The server has full control over what context is sent.

1. User (via Session A) calls `debate/start` tool
2. The server captures Session A's position from the tool arguments (the user provides it, or it was generated by the client)
3. The server makes a direct API call for Session B:
   - Constructs a fresh message array with only the debate prompt
   - Sets a system prompt for the "fresh" role
   - Sends it to the Anthropic Messages API (or OpenAI, etc.)
4. The server orchestrates the full debate internally:
   - Session A responses come from the user/client
   - Session B responses come from the API
   - Each phase feeds the previous phase's output as context
5. The server returns the complete debate transcript and convergence result

```python
# Conceptual implementation
import anthropic

class SessionBProvider:
    """Generates Session B responses via direct API call."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 2000,
    ) -> str:
        """Generate a response with precisely controlled context."""
        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.content[0].text


# In the server tool handler:
@mcp.tool()
async def debate_start(
    prompt: str,
    session_a_position: str,
    context_documents: list[str],
    ctx: Context,
) -> str:
    # Session A's position is provided directly by the user/client
    # (they have full context, they wrote it with full context)

    # Session B gets ONLY the prompt -- no context_documents
    session_b = SessionBProvider(api_key=config.api_key)
    session_b_position = await session_b.generate_response(
        system_prompt=(
            "You are analyzing a decision with fresh eyes. "
            "You have no prior context about this project. "
            "Question every assumption. Identify what is being "
            "taken for granted."
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    # Now run the challenge phase
    session_a_challenge = ...  # Return to user for their challenge
    session_b_challenge = await session_b.generate_response(
        system_prompt="...",
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": session_b_position},
            {"role": "user", "content": f"Challenge from the experienced analyst:\n{session_a_challenge}"},
        ],
    )

    # Convergence...
```

### Analysis

**1. Technical Feasibility: STRONG**

This works today. The Anthropic Python SDK (`anthropic`) is mature, async-native, and well-documented. The `AsyncAnthropic` client supports `messages.create()` with full control over system prompt, messages, model selection, temperature, and all other parameters. No experimental features, no optional capabilities, no client-side dependencies.

The server can also support multiple API providers (Anthropic, OpenAI, local models via Ollama) through a provider abstraction, giving users flexibility.

**2. Context Isolation Guarantee: STRONG**

This is the strongest guarantee of any approach. The server constructs Session B's message array from scratch. There is no client intermediary that might inject additional context. The server controls exactly what the model sees:

- System prompt: fully controlled by the server
- Message history: constructed by the server with only the debate-relevant content
- No ambient context: the API call has no "conversation state" beyond what is explicitly provided

The server can even hash or log the exact payload sent to the API, providing an auditable record of what Session B knew at each phase.

**3. User Experience: GOOD**

From the user's perspective:
- One-time setup: provide an API key (via environment variable or config file)
- Single command to start a debate: `debate/start` with a prompt
- The debate runs to completion within a single tool call (or across a few tool calls if Session A needs to provide input at each phase)
- Results are returned as structured output

The main friction point is API key management. This can be mitigated by:
- Reading from `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variables (standard practice)
- Supporting a config file at `~/.ploidy/config.toml`
- Clear error messages when no key is configured

**4. Dependency Requirements: MODERATE**

- Requires `anthropic` (or `openai`, or both) as an additional dependency
- Requires a valid API key with sufficient quota
- Each debate incurs API costs (typically small -- a full debate might use ~10K tokens for Session B)

Cost can be managed by:
- Defaulting to a cheaper model for Session B (e.g., Claude Haiku, GPT-4o-mini)
- Making the model configurable
- Showing estimated cost before starting a debate

**5. Alignment with Paper's Thesis: MODERATE**

The paper argues for "cross-session" context asymmetry. This approach provides genuine context asymmetry -- Session B's API call is a truly independent inference with no shared state. However, it is not "cross-session" in the MCP sense. Session B is not an MCP session; it is a raw API call managed by the server.

This is a pragmatic compromise: the asymmetry is real and verifiable, even if the mechanism is not a separate MCP client session. The debate protocol, convergence analysis, and interpretability properties all hold.

### Verdict: Best option for v0.1. Provides real context isolation with proven technology.

---

## Approach C: Manual Two-Terminal (Cross-Session via Shared Server)

### How It Would Work

Two separate human-driven MCP client sessions connect to the same Ploidy MCP server. Each session is a real, independent MCP client with its own conversation state. The server mediates the debate through shared persistence (SQLite).

1. User opens Terminal 1, starts Claude Code connected to the Ploidy MCP server
   - This becomes Session A. The user has been working in this session, accumulating context.
2. User opens Terminal 2, starts a fresh Claude Code instance connected to the same Ploidy server
   - This becomes Session B. Fresh conversation, no prior context.
3. In Terminal 1 (Session A): `debate/start --prompt "Should we migrate to microservices?"`
   - Server creates a debate record, assigns Session A as "experienced"
   - Returns a debate ID
4. In Terminal 2 (Session B): `debate/join --debate-id abc123`
   - Server assigns this session as "fresh"
   - Returns the debate prompt (and only the prompt -- no context documents)
5. Both sessions proceed through debate phases:
   - Each calls `debate/position` to submit their stance
   - Each calls `debate/challenge` after seeing the other's position (retrieved via `debate/status`)
   - Either calls `debate/converge` to trigger convergence analysis
6. Server tracks state in SQLite, ensures phase transitions are valid

```
Terminal 1 (Session A)                    Terminal 2 (Session B)
---------------------                    ---------------------
[Has full project context]               [Fresh, no context]

> debate/start
  "debate-id: abc123"
                                         > debate/join abc123
                                           "Prompt: Should we..."
> debate/position
  "I believe we should because..."       > debate/position
                                           "I'm skeptical because..."
> debate/status
  "Session B says: I'm skeptical..."     > debate/status
                                           "Session A says: I believe..."
> debate/challenge
  "Your skepticism ignores..."           > debate/challenge
                                           "Your confidence assumes..."
> debate/converge
  "Result: {synthesis...}"               > debate/converge
                                           "Result: {synthesis...}"
```

### Transport Requirement

This approach requires the Ploidy MCP server to use **Streamable HTTP transport** (or the older SSE transport), not stdio. The stdio transport is 1:1 -- one client per server process. For multiple clients to connect to the same server, the server must listen on an HTTP endpoint.

```python
# Server must be started with HTTP transport
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Ploidy", transport="streamable-http", port=8765)
```

Both Claude Code instances would be configured to connect to `http://localhost:8765/mcp` (or a remote URL).

### SQLite Concurrency

With multiple clients writing to the same SQLite database, WAL (Write-Ahead Logging) mode is essential:

```python
async def initialize(self) -> None:
    self._db = await aiosqlite.connect(self.db_path)
    await self._db.execute("PRAGMA journal_mode=WAL")
```

WAL mode allows concurrent readers with a single writer, which is sufficient for a multi-session debate where writes are infrequent and serialized by the debate protocol.

### Analysis

**1. Technical Feasibility: STRONG (with caveats)**

The MCP spec and Python SDK fully support Streamable HTTP transport with multiple concurrent clients. SQLite with WAL mode handles the concurrency requirements. The debate protocol's turn-based structure naturally serializes writes.

Caveats:
- Requires the user to manage multiple terminal sessions manually
- Requires configuring Claude Code to connect to an HTTP MCP server (slightly more involved than stdio)
- The server process must be started independently (not spawned by the client)
- Session identification: the server needs a way to distinguish which client is which session. This can be done via the tool arguments (the `debate/join` call) or via MCP session IDs.

**2. Context Isolation Guarantee: STRONGEST**

This is the gold standard for context isolation. Each MCP client session is a completely separate process with its own:
- Conversation history
- System prompt state
- Context window
- Memory

There is no mechanism by which Session B's client could accidentally access Session A's context. The isolation is enforced at the OS process level, not by protocol hints or server-side construction.

The server sends Session B only the debate prompt via the `debate/join` response. Session B's human operator can choose to provide additional context (or not), but the default path ensures asymmetry.

**3. User Experience: POOR**

This is the weakness. The user must:
1. Start the Ploidy server as a standalone process
2. Configure multiple Claude Code instances to connect to it
3. Manually coordinate between terminals
4. Copy debate IDs between sessions
5. Wait for other sessions to complete each phase before proceeding

For a solo developer (the likely early user), this means switching between terminals and essentially role-playing multiple sides. This is cognitively expensive and defeats some of the automation benefit.

For a multi-person team, this is more natural -- each person runs their own session. But this is a niche use case.

**4. Dependency Requirements: LOW**

No API keys needed. No additional Python packages beyond `mcp` and `aiosqlite`. The only requirement is that the user can run multiple terminal sessions, which is universally available.

**5. Alignment with Paper's Thesis: STRONGEST**

This is the most faithful implementation of the paper's "cross-session" vision. Multiple real, independent AI sessions with genuinely different context, debating through a structured protocol. The context asymmetry is not simulated or approximated -- it is real, arising from the fundamental separation of independent conversations.

### Verdict: Best long-term architecture. Too much friction for v0.1 solo use.

---

## Comparison Matrix

| Criterion                    | A: MCP Sampling | B: Subprocess/API | C: Two-Terminal |
|------------------------------|:---------------:|:-----------------:|:---------------:|
| Works today (March 2026)     | No              | Yes               | Yes             |
| Context isolation guarantee  | Weak (advisory) | Strong (server-controlled) | Strongest (process-level) |
| User setup steps             | 1               | 2 (+ API key)     | 5+              |
| API key required             | No              | Yes               | No              |
| API cost per debate          | None            | ~$0.01-0.10       | None            |
| Supports solo developer      | Yes             | Yes               | Awkward         |
| Supports multi-person team   | No              | No                | Yes             |
| Multi-turn debate in one cmd | Possible        | Yes               | No              |
| Auditable context isolation  | No              | Yes               | Yes             |
| Aligned with paper thesis    | Poor            | Moderate          | Strongest       |
| Implementation complexity    | Low             | Medium            | High            |

---

## Recommendation: Approach C First, Then B, Then A

> **Updated 2026-03-15.** Original recommendation was B-first. Revised after considering that the user has Claude Max + Gemini Pro subscriptions, making Approach C zero additional cost.

### Phase 1: Approach C (v0.1) -- Two-Terminal

Implement the two-terminal cross-session architecture as the primary mode. The user runs two Claude Code sessions (or any MCP-compatible client). Both connect to the same Ploidy MCP server via Streamable HTTP. The Deep session carries full project context; the Fresh session starts clean.

**Why C first:**

- **Zero additional cost.** The user has Claude Max and Gemini Pro subscriptions. All sessions use existing subscription quota -- no API keys, no per-token billing.
- **Strongest context isolation.** Process-level separation is the gold standard. No advisory hints, no server-side message construction -- each session is a genuinely independent OS process with its own context window.
- **Most aligned with the paper's thesis.** The paper argues for "real cross-session dialogue." Approach C is the only approach that delivers this literally -- multiple real sessions, real conversations, mediated by a structured protocol.
- **Simpler server implementation.** The server does not need to generate LLM responses itself. It only needs to store state, enforce protocol transitions, and coordinate turns. This is a simpler, more testable codebase.

Implementation plan:
1. Streamable HTTP transport (FastMCP with `transport="streamable-http"`)
2. Session role assignment: first client = Deep, second client = Fresh (configurable)
3. `debate/start` creates a debate, returns a debate ID
4. `debate/join` allows additional sessions to join
5. Turn-based argument submission via `debate/position`, `debate/challenge`
6. `debate/converge` triggers convergence analysis
7. SQLite with WAL mode for concurrent access
8. CLI helper: `ploidy start "prompt"` and `ploidy join debate-xxxx`

### Phase 2: Approach B (v0.2) -- API Fallback for Automation

Add an API fallback mode for automated/single-terminal use. Uses the `openai` SDK with a configurable `base_url`, supporting multiple backends:

- **Ollama** (free, local) -- `base_url=http://localhost:11434/v1`
- **OpenRouter** -- `base_url=https://openrouter.ai/api/v1`
- **Anthropic** -- via OpenAI-compatible endpoint
- **OpenAI** -- direct
- **Google** -- via OpenAI-compatible endpoint

Environment variables:
- `PLOIDY_API_BASE` -- base URL for the OpenAI-compatible endpoint
- `PLOIDY_API_KEY` -- API key (or "ollama" for local)
- `PLOIDY_MODEL` -- model identifier

This mode is for when the user wants single-command debate execution or CI/CD integration, where managing multiple terminals is impractical.

### Phase 3: Approach A (v0.3+) -- MCP Sampling

If/when major MCP clients implement sampling with strong context isolation guarantees:
1. Add a `SamplingProvider` that uses `ctx.session.create_message()`
2. Auto-detect client sampling capability during initialization
3. Use sampling when available, fall back to API (v0.2) or prompt user to open additional terminals (v0.1)

### Why C Before B?

The original analysis rated Approach C's UX as "POOR" due to manual multi-terminal management. This was overweighted. In practice:

- The user already works with multiple terminals daily.
- The two-terminal flow (`ploidy start` / `ploidy join`) is two commands, not five steps.
- The "awkward for solo developer" concern is valid but secondary to the core value: **real context isolation produces real insight**. A slightly higher-friction workflow that delivers genuine cross-session debate is better than a lower-friction workflow that simulates it.
- Approach B can always be added later (v0.2) for automation use cases without any architectural changes -- the debate protocol and persistence layer are the same.

---

## Detailed Design: Phase 1 (Approach B)

### New Module: `provider.py`

```python
"""Session B response providers.

Abstracts the mechanism for generating Session B responses,
allowing different backends (API, sampling, cross-session)
to be swapped without changing the debate orchestration logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationConfig:
    """Configuration for a Session B generation request."""
    model: str
    system_prompt: str
    max_tokens: int = 2000
    temperature: float = 1.0


class SessionBProvider(ABC):
    """Abstract interface for generating Session B responses."""

    @abstractmethod
    async def generate(
        self,
        config: GenerationConfig,
        messages: list[dict[str, str]],
    ) -> str:
        """Generate a Session B response.

        Args:
            config: Generation parameters.
            messages: The message history for Session B.
                      Contains ONLY what Session B should see.

        Returns:
            The generated response text.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether this provider is configured and reachable."""
        ...
```

### New Module: `orchestrator.py`

```python
"""Debate orchestration engine.

Coordinates the full lifecycle of a debate:
1. Receives Session A's position from the calling client
2. Generates Session B's position via a SessionBProvider
3. Runs challenge rounds
4. Triggers convergence analysis
5. Returns the structured result

This module contains the core logic that makes Ploidy work
as a single-command experience for solo developers.
"""
```

The orchestrator manages the interplay between Session A (the calling client) and Session B (the provider). It constructs Session B's message history at each phase, ensuring that Session B only sees:
- The original debate prompt
- Its own prior responses
- Session A's responses from completed phases (for challenge/convergence)

Session B never sees Session A's context documents, prior debate history, or accumulated project knowledge.

### Configuration

```toml
# ~/.ploidy/config.toml (optional, env vars take precedence)

[provider]
backend = "anthropic"  # or "openai", "ollama"
model = "claude-sonnet-4-20250514"  # model for Session B

[provider.anthropic]
api_key_env = "ANTHROPIC_API_KEY"  # env var name, NOT the key itself

[provider.openai]
api_key_env = "OPENAI_API_KEY"
model = "gpt-4o"

[debate]
max_tokens_per_turn = 2000
temperature = 1.0
max_challenge_rounds = 2
```

### Modified Data Flow

```
Client (Session A)
    |
    | debate/start(prompt, position, context_docs)
    v
Server
    |
    |--> SessionManager.create_session_pair()
    |       Session A: full context
    |       Session B: prompt only
    |
    |--> SessionBProvider.generate()  -----> External API
    |       (prompt only, fresh system prompt)    |
    |       <--- Session B position -------------|
    |
    |--> DebateProtocol.submit_message() (A's position)
    |--> DebateProtocol.submit_message() (B's position)
    |--> DebateProtocol.advance_phase()
    |
    | [Challenge phase: repeat with cross-fed positions]
    |
    |--> ConvergenceEngine.analyze()
    |
    |--> DebateStore.save()
    |
    v
Client receives ConvergenceResult
```

### Tool Interface Changes

The `debate/start` tool becomes richer:

```python
@mcp.tool()
async def debate_start(
    prompt: str,
    session_a_position: str,
    context_documents: list[str] | None = None,
) -> dict:
    """Start a debate and run it to completion.

    Args:
        prompt: The decision to debate.
        session_a_position: Your (Session A's) position on this decision.
            Write this with full awareness of your project context.
        context_documents: Optional list of context documents that inform
            your position. These are stored for the record but NOT shown
            to Session B.

    Returns:
        The complete debate transcript and convergence result.
    """
```

For users who want more control, individual phase tools remain available:

- `debate/start_async` -- Start a debate, get a debate ID, submit positions separately
- `debate/position` -- Submit a position for a specific phase
- `debate/challenge` -- Submit a challenge
- `debate/converge` -- Trigger convergence
- `debate/status` -- Check debate state

---

## Open Questions

1. **Should Session A's position be generated by the server too?** In the current design, the user writes Session A's position manually (leveraging their client's full context). An alternative: the server asks the client to articulate its position via a structured prompt, then uses the API for Session B. This adds a sampling dependency for Session A.

2. **Same model for all sessions?** The paper's thesis argues for same-model comparison. But in practice, users may want to use a cheaper model for Session B (cost savings) or a different model (diversity). The `SessionBProvider` abstraction supports this, but the default should be same-model for thesis alignment.

3. **How many challenge rounds?** The protocol currently defines a single challenge round. The paper suggests that 2-3 rounds may be optimal before diminishing returns. This should be configurable.

4. **Convergence engine: rule-based or LLM-powered?** The convergence analysis itself may benefit from LLM assistance. This creates a third LLM call (neither Session A nor B). The `SessionBProvider` abstraction can be reused for this, with a "convergence analyst" system prompt.

---

## References

- [MCP Specification: Sampling](https://modelcontextprotocol.io/specification/draft/client/sampling) -- Defines `sampling/createMessage` request format
- [MCP Specification: Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) -- Streamable HTTP transport for multi-client
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) -- Official Python SDK with sampling examples
- [Claude Code MCP Sampling Feature Request](https://github.com/anthropics/claude-code/issues/1785) -- Tracks client sampling support
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) -- For Approach B API calls
- [SQLite WAL Mode for Concurrent MCP Sessions](https://dev.to/daichikudo/fixing-claude-codes-concurrent-session-problem-implementing-memory-mcp-with-sqlite-wal-mode-o7k) -- WAL mode for Approach C
