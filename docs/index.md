# Ploidy

**Same model, different context depths, better decisions.**

Ploidy is a structured debate protocol between physically separate sessions of the same LLM with intentionally asymmetric context depths. Unlike multi-model approaches that rely on model diversity, Ploidy exploits **context diversity** within a single model.

The name draws from biological polyploidy, where gene duplication provides redundancy that enables both error tolerance and functional diversification.

---

## The Problem: Stochastic Prior Lock-in

When you ask the same model the same question in different sessions, you get different answers. If you only use one session, that first stochastic response anchors all subsequent reasoning. Prompt-based mitigations (chain-of-thought, reflection, "think again") have **no statistically significant effect** on this anchoring bias.

A user confined to a single session is unknowingly subject to a stochastic lottery.

## The Mechanism: Context Asymmetry Spectrum

Ploidy introduces a 2D framework for multi-session verification:

| | Passive (in prompt) | Active (on request) | None |
|---|---|---|---|
| **Full context** | Deep | Deep-Active | -- |
| **Compressed** | Semi-Fresh-Passive | Semi-Fresh-Active | -- |
| **None** | -- | -- | Fresh |

Two terminals connect to one Ploidy MCP server. Terminal 1 (Deep) has full project context. Terminal 2 (Fresh) starts clean. They debate through typed semantic actions (`agree`, `challenge`, `propose_alternative`, `synthesize`) before a convergence phase.

## Key Finding: Primacy Anchoring Effect

In factorial ablation experiments across 10 tasks and 11 methods, we identified **information position as the dominant factor** in context delivery:

| Condition | Summary Position | Instruction | Avg Recall |
|---|---|---|---|
| SF-Passive | Top | No | 89% |
| SF-Passive+Independent | Top | Yes | 94% |
| **SF-Passive+Bottom** | **Bottom** | No | **100%** |
| SF-Active | Bottom | Yes | 100% |

Moving a compressed summary from the top to the bottom of the prompt improves recall from 89% to 100% (+11pp) -- with no other changes. This is consistent with primacy anchoring effects in human cognition.

!!! info "Pilot study caveat"
    These results are from 10 tasks with single runs per condition. Statistical validation with 30+ tasks and 5+ runs is in progress.

## Architecture

```
Terminal A (Deep)              Terminal B (Fresh)
   | debate/start                | debate/join
   | debate/position             | debate/position
   | debate/challenge            | debate/challenge
   | debate/converge
        |
   Ploidy Server (FastMCP, Streamable HTTP :8765)
        |
   SQLite (WAL, ~/.ploidy/ploidy.db)
```

5-phase protocol: `INDEPENDENT` -> `POSITION` -> `CHALLENGE` -> `CONVERGENCE` -> `COMPLETE`

## Paper

**Ploidy: Context-Asymmetric Structured Debate for LLM Decision Verification**

- [Paper (LaTeX source)](https://github.com/heznpc/ploidy/tree/main/paper/latex)
- [Experiment code](https://github.com/heznpc/ploidy/blob/main/experiments/run_experiment.py)
- [Experiment results (100+ JSON)](https://github.com/heznpc/ploidy/tree/main/experiments/results)

Target venues: ICML 2026 Workshop, NeurIPS 2026, AAMAS 2027

24 references including CCR, AceMAD, SR-DCR, and 6 cognitive science papers (generation effect, directed forgetting, incubation, testing effect, primacy anchoring).

## Quick Start

```bash
pip install ploidy
python -m ploidy  # starts MCP server on :8765
```

Connect two MCP clients (e.g., Claude Code terminals) to `http://localhost:8765/mcp`, then use the debate tools:

```bash
# Terminal 1 (Deep session) — call via MCP tool
debate_start prompt="Should we migrate from PostgreSQL to TimescaleDB?"

# Terminal 2 (Fresh session) — call via MCP tool
debate_join debate_id="debate-xxxx" role="fresh"
```

Or use single-terminal auto mode (requires API key):

```bash
export PLOIDY_API_BASE_URL=https://api.anthropic.com
# Call debate_auto via MCP — server runs both sides automatically
```

## Documentation

<div class="grid cards" markdown>

- [:material-rocket-launch: **Getting Started**](getting-started.md)

    Install Ploidy and run your first debate.

- [:material-lightbulb-on: **How It Works**](how-it-works.md)

    Core concept and why context asymmetry matters.

- [:material-file-tree: **Architecture**](architecture.md)

    Technical architecture and module overview.

- [:material-api: **API Reference**](api-reference.md)

    Complete MCP tool reference.

- [:material-flask: **Research**](research.md)

    Experimental design, results, and related work.

</div>

---

MIT License | [GitHub](https://github.com/heznpc/ploidy) | heznpc
