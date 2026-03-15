# Getting Started

This guide walks you through installing Ploidy and running your first cross-session debate.

## Prerequisites

- **Python 3.11 or later**
- **An MCP-compatible AI client** -- Claude Code, Claude Desktop, or any client that supports Streamable HTTP transport
- **Two terminal windows** (for the two-terminal debate flow)

## Installation

```bash
pip install ploidy
```

Or install from source:

```bash
git clone https://github.com/heznpc/ploidy.git
cd ploidy
pip install -e .
```

## MCP Client Configuration

Add Ploidy to your MCP client's server configuration. The exact location depends on your client.

=== "Claude Code"

    Add to your project's `.mcp.json` or global MCP config:

    ```json
    {
      "ploidy": {
        "type": "streamable-http",
        "url": "http://localhost:8765/mcp"
      }
    }
    ```

=== "Claude Desktop"

    Add to `claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "ploidy": {
          "type": "streamable-http",
          "url": "http://localhost:8765/mcp"
        }
      }
    }
    ```

=== "Other MCP Clients"

    Any MCP client that supports Streamable HTTP transport can connect to:

    ```
    http://localhost:8765/mcp
    ```

## Start the Server

Before opening your AI client sessions, start the Ploidy server:

```bash
ploidy
```

The server starts on port 8765 using Streamable HTTP transport. Both terminals will connect to this single server instance.

## Your First Debate

### Step 1: Open Terminal 1 (the Deep session)

Open your MCP client in a terminal where you've been working on your project. This session has accumulated context -- it knows your codebase, your prior decisions, your constraints.

Start a debate:

```
ploidy start "Should we use monorepo or polyrepo for our microservices?"
```

The server creates a debate and returns a debate ID (e.g., `debate-a1b2c3d4`).

### Step 2: Open Terminal 2 (the Fresh session)

Open a **new** MCP client instance in a separate terminal. This is a fresh session with no prior context.

Join the debate using the ID from Step 1:

```
ploidy join debate-a1b2c3d4
```

The Fresh session receives only the debate prompt -- no project context, no prior decisions, no accumulated assumptions.

### Step 3: The Debate Protocol

Both sessions proceed through the structured protocol:

1. **Position** -- Each session independently analyzes the decision and submits their stance
2. **Challenge** -- Each session critiques the other's position using semantic actions (`agree`, `challenge`, `propose_alternative`, `synthesize`)
3. **Converge** -- The server synthesizes positions into a structured result

### Step 4: Review the Result

The convergence result includes:

- **Agreements** -- Points where both sessions independently reached the same conclusion
- **Productive disagreements** -- Points where the Fresh session's lack of context revealed a valid concern
- **Irreducible disagreements** -- Genuinely different priorities that require a human decision
- **Synthesis** -- An overall recommendation with a confidence score

## What to Expect

!!! info "Pre-alpha status"

    Ploidy is in early development. The server starts, MCP tools are registered, and the protocol is defined. The full debate orchestration and convergence engine are being implemented. Expect rough edges and breaking changes.

What works today:

- Server starts and accepts MCP connections via Streamable HTTP
- All six debate tools are registered and callable
- Debate protocol state machine is defined

What is coming:

- Full debate orchestration across sessions
- Convergence engine with structured synthesis
- Persistent debate history via SQLite
- API fallback mode for single-terminal use (v0.2)
