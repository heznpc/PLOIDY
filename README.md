# Ploidy

**Intentional context asymmetry to reduce confirmation bias in LLMs.**

[![CI](https://github.com/heznpc/ploidy/actions/workflows/ci.yml/badge.svg)](https://github.com/heznpc/ploidy/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-heznpc.github.io%2Fploidy-blue)](https://heznpc.github.io/ploidy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)

## Why

Ask the same model the same question in separate sessions. You'll get different answers every time — some agree, some disagree, some equivocate. If you continue in just one session, the model's first stochastic response becomes an anchor. It reinforces its own prior, the user builds on it, and the session locks into a trajectory that prompt engineering [cannot undo](https://arxiv.org/abs/2603.12123).

This means identical models, identical prompts, identical users — but different project outcomes depending on which random sample landed first. The user is in a probability lottery without knowing it. Task completion time varies, task success varies, and perceived "model performance" varies — all from the same model.

This is not the same problem that multi-agent teams solve. Agent teams (CrewAI, MetaGPT, Claude Agent Teams) divide labor across models for throughput. More hands, same perspective. Under symmetric information, scaling agents is [mathematically equivalent to majority voting](https://arxiv.org/abs/2508.17536) over identically biased samples — it cannot improve expected correctness.

Ploidy takes the orthogonal approach: **deliberately create context asymmetry within the same model, then make the asymmetric sessions debate**. A deep session carries full project context. A fresh session starts with zero prior commitment. When they disagree, the cause is isolatable — one has context the other doesn't. That disagreement is the signal.

## Quick Start

```bash
# Install
pip install ploidy

# Start the server
python -m ploidy
```

**Terminal 1 (Deep session)** — tell your AI:
> "Start a Ploidy debate: Should we use monorepo or polyrepo?"

**Terminal 2 (Fresh session)** — tell your AI:
> "Join Ploidy debate a1b2c3d4e5f6"

### MCP Client Configuration

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

## How It Works

```
Terminal 1 (Deep)              Terminal 2 (Fresh)
[Full project context]         [Zero context]
        |                              |
        └──── debate/start ──→ Ploidy Server ←── debate/join ────┘
                               (port 8765)
              position ──────→ [SQLite + WAL] ←────── position
              challenge ─────→ [State Machine] ←───── challenge
              converge ──────→ [Convergence]  ←────── converge
                                    ↓
                            Structured Result
                         (agreements, disagreements,
                          confidence score)
```

Sessions debate through typed semantic actions (agree, challenge, propose alternative, synthesize) across a five-phase protocol: Independent → Position → Challenge → Convergence → Complete. The Context Asymmetry Spectrum ranges from Deep (full context) through Semi-Fresh (compressed context, passively or actively delivered) to Fresh (zero context).

## Tools

| Tool | Description |
|------|-------------|
| `debate_start` | Begin a debate with a prompt |
| `debate_join` | Join as a fresh (zero-context) session |
| `debate_position` | Submit your stance |
| `debate_challenge` | Critique with semantic actions (agree/challenge/propose_alternative/synthesize) |
| `debate_converge` | Trigger convergence analysis |
| `debate_status` | Check current state |
| `debate_cancel` | Cancel in progress |
| `debate_delete` | Permanently delete |
| `debate_history` | List past debates |
| `debate_auto` | Run a full two-sided debate automatically via API |

## Configuration

All via environment variables:

```bash
PLOIDY_PORT=8765              # Server port
PLOIDY_DB_PATH=~/.ploidy/ploidy.db  # Database location
PLOIDY_LOG_LEVEL=INFO         # Logging level
PLOIDY_AUTH_TOKEN=secret      # Bearer token auth (optional)
PLOIDY_API_BASE_URL=https://api.openai.com/v1  # Optional auto-debate backend
PLOIDY_API_KEY=...            # Optional API key for auto mode
PLOIDY_API_MODEL=gpt-5.4      # Optional model override for auto mode
```

## Single-Terminal Auto Mode

If you configure an OpenAI-compatible API backend, Ploidy can run both sides of the
debate automatically in one tool call. In `debate_auto`, the server generates:

- an Experienced position using the provided `context_documents`
- a Fresh or Semi-Fresh counter-position
- challenge messages from both sides
- the final convergence analysis

Fresh auto sessions must use `delivery_mode="none"`. Semi-Fresh auto sessions must
use `delivery_mode="passive"` or `delivery_mode="active"`.

## Docker

```bash
docker compose up
```

## Documentation

- [Getting Started](https://heznpc.github.io/ploidy/getting-started/) — Install and first debate
- [How It Works](https://heznpc.github.io/ploidy/how-it-works/) — Core concept
- [Architecture](https://heznpc.github.io/ploidy/architecture/) — Technical overview
- [API Reference](https://heznpc.github.io/ploidy/api-reference/) — Tool documentation
- [Research](https://heznpc.github.io/ploidy/research/) — Academic positioning

## Research

Ploidy extends Cross-Context Review ([Song 2026](https://arxiv.org/abs/2603.12123)) from unidirectional fresh-session review to bidirectional structured debate. The intersection of context asymmetry × same-model debate × structured protocol has zero published papers as of March 2026.

In pilot experiments, context asymmetry shows no benefit on short-context tasks where entrenchment does not occur — but on long-context tasks with anchoring bias, asymmetric debate achieves the highest ground-truth recall (5/5 vs. single session's 3/5). These results bound where the intervention applies.

## License

MIT
