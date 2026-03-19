# Getting Started

This guide walks you through installing Ploidy and running your first cross-session debate.

## Prerequisites

- **Python 3.11 or later**
- **Two terminal windows** with an MCP-compatible AI client (Claude Code, Claude Desktop, etc.)

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

## Step 1: Start the Server

```bash
python -m ploidy
```

The server starts on `http://localhost:8765/mcp` using Streamable HTTP transport. Leave this running.

**Environment variables** (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `PLOIDY_PORT` | `8765` | Server port |
| `PLOIDY_DB_PATH` | `~/.ploidy/ploidy.db` | SQLite database path |
| `PLOIDY_LOG_LEVEL` | `INFO` | Logging level |
| `PLOIDY_AUTH_TOKEN` | *(none)* | Bearer token for auth (if set, all requests require it) |
| `PLOIDY_MAX_SESSIONS` | `5` | Max sessions per debate |

## Step 2: Configure MCP Clients

Both terminals need to connect to the same Ploidy server. Add to your MCP config:

=== "Claude Code (.mcp.json)"

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

## Step 3: Run Your First Debate

### Terminal 1 — The Deep Session

Open your MCP client in a terminal where you have project context. Tell the AI:

> "Start a Ploidy debate: Should we use monorepo or polyrepo for our microservices?"

The AI calls `debate_start` and gets back a `debate_id` like `a1b2c3d4e5f6`.

### Terminal 2 — The Fresh Session

Open a **new, clean** MCP client session. Tell the AI:

> "Join Ploidy debate a1b2c3d4e5f6"

The Fresh session receives **only the debate prompt** — no project context.

### The Debate Unfolds

Both sessions then go through the protocol:

```
INDEPENDENT → POSITION → CHALLENGE → CONVERGENCE → COMPLETE
```

1. **Position** — Each AI independently analyzes the question and submits a stance
2. **Challenge** — Each AI reads the other's position and responds with a semantic action:
    - `agree` — "I reached the same conclusion"
    - `challenge` — "I disagree, here's why"
    - `propose_alternative` — "Neither is right, consider this"
    - `synthesize` — "Both have merit, here's a synthesis"
3. **Converge** — Either session triggers convergence analysis

### Review the Result

The convergence result includes:

- **Agreements** — Points where both sessions independently converged
- **Productive disagreements** — Fresh session's lack of context revealed a valid concern
- **Irreducible disagreements** — Different priorities requiring a human decision
- **Confidence score** — 0.0 (full disagreement) to 1.0 (full agreement)

## Available Tools

| Tool | Description |
|------|-------------|
| `debate_start` | Begin a debate with a prompt |
| `debate_join` | Join as a fresh session |
| `debate_position` | Submit your stance |
| `debate_challenge` | Critique the other's position |
| `debate_converge` | Trigger convergence analysis |
| `debate_status` | Check current state and messages |
| `debate_cancel` | Cancel an in-progress debate |
| `debate_delete` | Permanently delete a debate |
| `debate_history` | List past debates |
| `debate_auto` | Run both sides automatically via API |

## Optional: Single-Terminal Auto Debate

If you want Ploidy to generate both sides itself, configure an OpenAI-compatible backend:

```bash
export PLOIDY_API_BASE_URL=https://api.openai.com/v1
export PLOIDY_API_KEY=your-key
export PLOIDY_API_MODEL=gpt-5.4
```

Then ask your MCP client to call `debate_auto`.

- `fresh_role="fresh"` requires `delivery_mode="none"`
- `fresh_role="semi_fresh"` requires `delivery_mode="passive"` or `delivery_mode="active"`
- the server will generate both positions, both challenges, and the convergence result

## Docker

```bash
docker compose up
```

Or build and run directly:

```bash
docker build -t ploidy .
docker run -p 8765:8765 -v ploidy-data:/data ploidy
```

## Example Debate Prompts

Architecture decisions work best because they have clear trade-offs:

- "Should we use monorepo or polyrepo for 12 microservices with a shared auth library?"
- "REST vs gRPC for internal service communication?"
- "SQLite vs PostgreSQL for a tool that starts local but may scale to multi-user?"
- "Should we migrate from Express to Fastify?"
- "Serverless functions vs containerized services for our event processing pipeline?"
