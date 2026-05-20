# Ploidy

**Intentional context asymmetry to reduce confirmation bias in LLMs.**

> Research Program: 2 (Epistemic Failure and Correction)
> Status: Reproducible artifact + paper under preparation
> Relationship to other work: Anchor for Program 2; companion theory paper at [heznpc/lifespan](https://github.com/heznpc/lifespan)

[![CI](https://github.com/heznpc/ploidy-research/actions/workflows/ci.yml/badge.svg)](https://github.com/heznpc/ploidy-research/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-heznpc.github.io%2Fploidy-research-blue)](https://heznpc.github.io/ploidy-research/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)

## Two ways to read this repo

This monorepo ships both a **paper** (the mechanism — *why* intentional context asymmetry reduces confirmation bias) and an **MCP server** (the tool — *how* to run that asymmetric debate inside your own workflow). The two share the same evidence base.

- **Read the paper.** [`paper/main.tex`](paper/main.tex) is the working preprint. Drafts, review notes, and the shared research program live in [`planning/`](planning/).
- **Run the tool.** Skip to [Quick Start](#quick-start) below.

## Why

Ask the same model the same question in separate sessions. You'll get different answers every time — some agree, some disagree, some equivocate. If you continue in just one session, the model's first stochastic response becomes an anchor. It reinforces its own prior, the user builds on it, and the session locks into a trajectory that prompt engineering [cannot undo](https://arxiv.org/abs/2603.12123).

This means identical models, identical prompts, identical users — but different project outcomes depending on which random sample landed first. The user is in a probability lottery without knowing it. Task completion time varies, task success varies, and perceived "model performance" varies — all from the same model.

This is not the same problem that multi-agent teams solve. Agent teams (CrewAI, MetaGPT, Claude Agent Teams) divide labor across models for throughput. More hands, same perspective. Under symmetric information, scaling agents is [mathematically equivalent to majority voting](https://arxiv.org/abs/2508.17536) over identically biased samples — it cannot improve expected correctness.

Ploidy takes the orthogonal approach: **deliberately create context asymmetry within the same model, then make the asymmetric sessions debate**. A deep session carries full project context. A fresh session starts with zero prior commitment. When they disagree, the cause is isolatable — one has context the other doesn't. That disagreement is the signal.

## Quick Start

```bash
# Install
pip install ploidy              # core server
pip install ploidy[api]         # + auto-debate mode (requires OpenAI SDK)
```

### MCP Client Configuration (stdio — recommended)

The default transport is `stdio`, so the MCP client spawns the server on
demand and there is no separate process to manage:

```json
{
  "mcpServers": {
    "ploidy": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "ploidy"]
    }
  }
}
```

### Recommended: `/ploidy` slash command (Claude Code)

```
/ploidy Should we rewrite the ingestion pipeline in Rust?
```

The command ([`.claude/commands/ploidy.md`](.claude/commands/ploidy.md))
writes your deep-context analysis, spawns a fresh sub-agent for the
zero-context side, calls the MCP tool with both texts, and renders the
synthesis. No API key needed.

### Single-terminal flow (direct tool call)

Inside one MCP client session, ask the assistant to write two analyses
— one with full project context, one from a fresh sub-agent that only
sees the prompt — then call `debate(mode="solo", ...)` with both texts.
Ploidy persists the debate, classifies the challenges, and returns the
convergence in a single tool call. See
[`docs/v0.4-migration.md`](docs/v0.4-migration.md) for the full API.

### Two-terminal flow (cross-session, multi-client)

For the original cross-session experience, run the server over HTTP and
configure each MCP client to point at it:

```bash
PLOIDY_TRANSPORT=streamable-http python3 -m ploidy
```

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

**Terminal 1 (Deep session)** — tell your AI:
> "Start a Ploidy debate: Should we use monorepo or polyrepo?"

**Terminal 2 (Fresh session)** — tell your AI:
> "Join Ploidy debate a1b2c3d4e5f6"

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
| `debate_review` | Review and resume a paused auto-debate (HITL) |
| `debate_solo` | Caller-supplied positions; converge in one call (no API key) |

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

## Claude.ai Custom Connector

Deploy once, register once, use from Claude.ai web / mobile:

```sh
# Fly.io (recommended prototype)
flyctl launch --no-deploy --copy-config --config deploy/fly/fly.toml
flyctl secrets set PLOIDY_TOKENS='{"<token>": "<tenant>"}'
flyctl deploy --config deploy/fly/fly.toml
```

Then in Claude.ai → Settings → Connectors → Add custom → point at
`https://<your-app>.fly.dev/mcp` with the token as bearer auth. Full
walkthrough in [`docs/custom-connector.md`](docs/custom-connector.md).

## Documentation

- [Getting Started](https://heznpc.github.io/ploidy-research/getting-started/) — Install and first debate
- [How It Works](https://heznpc.github.io/ploidy-research/how-it-works/) — Core concept
- [Architecture](https://heznpc.github.io/ploidy-research/architecture/) — Technical overview
- [API Reference](https://heznpc.github.io/ploidy-research/api-reference/) — Tool documentation
- [Research](https://heznpc.github.io/ploidy-research/research/) — Academic positioning

## Research

This monorepo contains both the MCP server and the **mechanism paper** that the software accompanies. See `paper/main.tex` for the preprint and `planning/` for drafts, review notes, and the shared research program. The companion **theory paper** ("The Accumulation–Renewal Dilemma") lives in a sibling repository: [heznpc/lifespan](https://github.com/heznpc/lifespan).

### Positioning

Ploidy extends Cross-Context Review ([Song 2026](https://arxiv.org/abs/2603.12123)) from unidirectional fresh-session review to bidirectional structured debate. The intersection of context asymmetry × same-model debate × structured protocol has zero published papers as of March 2026.

### Pilot results (n=1 per condition)

In pilot experiments, context asymmetry shows no benefit on short-context tasks where entrenchment does not occur — but on long-context tasks with anchoring bias, asymmetric debate achieves the highest ground-truth recall (5/5 vs. single session's 3/5). **These pilots are n=1 per condition** unless explicitly noted: treat them as existence proofs and bound-finders for where the intervention applies, not as effect-size estimates. Cross-model validation (Opus / Sonnet / Gemini / GPT-5.4) and stochastic-N baselines are the v0.3 layer firming up that bound; see [`experiments/`](experiments/) for the current sweep matrix.

### Dual remote (DOI provenance)

This repo pushes to two GitHub remotes — [`heznpc/ploidy-research`](https://github.com/heznpc/ploidy-research) (canonical development) and [`heznpc/PLOIDY`](https://github.com/heznpc/PLOIDY) (archival snapshot). Originally split to obtain a new Zenodo DOI for the research artifact after the working repo had accumulated history that confused archival metadata; the academic/tool separation is a useful side effect. Cite the `PLOIDY` snapshot via its Zenodo DOI; develop against `ploidy-research`.

## License

MIT
