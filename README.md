# Ploidy

**Same model, different context depths, better decisions.**

Requires: Claude Max, Gemini Pro, or any MCP-compatible AI client.

---

## Quick Start

```
# Terminal 1 -- start the server and create a debate
ploidy start "Should we use monorepo or polyrepo?"

# Terminal 2 -- join the debate from a fresh session
ploidy join debate-xxxx
```

Both terminals connect to the same Ploidy MCP server. Terminal 1 carries your full project context (the "Deep" session). Terminal 2 starts clean (the "Fresh" session). They debate through a structured protocol, and the disagreements are interpretable because context is the only variable.

## Installation

```bash
pip install ploidy
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Code `mcp.json`):

```json
{
  "ploidy": {
    "type": "streamable-http",
    "url": "http://localhost:8765/mcp"
  }
}
```

## How It Works

Ploidy orchestrates **cross-session multi-agent debate** between N instances of the same model. The key insight: you don't need different models to get meaningful disagreement -- you need **different context**.

### The N-Session Model

1. **Deep session** (Terminal 1) -- You've been working in this session. It has your full project context: prior decisions, accumulated assumptions, file history, conversation state.
2. **Fresh session** (Terminal 2) -- A clean session with no prior context. It sees only the debate prompt.
3. **Additional sessions** (Terminal 3+) -- Optional sessions with varying context depths, enabling richer multi-perspective debates.

### The Debate Protocol

1. **Start** -- Deep session creates a debate with a decision prompt
2. **Join** -- Fresh session(s) join with only the prompt (no project context)
3. **Position** -- All sessions independently analyze the decision and submit their stance
4. **Challenge** -- Each session critiques the others' positions
5. **Converge** -- The server synthesizes positions into a structured result: agreements, disagreements, synthesis, and confidence scores

### Why This Works

Traditional multi-agent debate (MAD) pits different models against each other. But model differences are noisy -- you can't isolate *why* they disagree. Is it training data? Architecture? RLHF tuning?

Ploidy uses the **same model** with **different context**. When sessions of the same model disagree, you know exactly why: one has context the others don't. That's a signal, not noise.

- The Deep session may over-anchor on sunk costs or prior decisions
- The Fresh session asks "but why?" without the baggage
- The structured debate forces all sessions to defend their reasoning
- The convergence engine identifies what survives scrutiny

## Status

**Pre-alpha.** The server runs, the debate protocol is defined, and tools are registered as stubs. The Streamable HTTP transport, session coordination, and convergence engine are under active implementation.

## Etymology

In biology, **ploidy** refers to the number of complete sets of chromosomes in a cell. A haploid cell has one set (1n), a diploid has two (2n), a triploid has three (3n), and polyploid cells carry many sets (Nn). Each set contributes its own perspective on the genome -- together, they create diversity that makes the organism more resilient.

Ploidy the project works the same way:

- **Session A** (the experienced set) -- carries full project context, prior decisions, learned patterns. It has wisdom, but also accumulated bias.
- **Session B** (the fresh set) -- enters with minimal context, asks naive questions, challenges assumptions. It lacks experience, but also lacks anchoring.
- **Session C, D, ...** (additional sets) -- can carry varying depths of context, enabling richer multi-perspective analysis.

The system is not limited to two sessions. Like polyploid organisms that thrive through having multiple chromosome sets, Ploidy supports N sessions with varying context levels -- from fully loaded to completely fresh -- producing decisions that are more robust through structured diversity.

## Key References

- [Knowledge Divergence in LLM Multi-Agent Debate](https://arxiv.org/abs/2603.05293) -- Analysis of how knowledge asymmetry affects debate dynamics
- [Bias Reinforcement in Multi-Agent Debate](https://arxiv.org/abs/2503.16814) -- Why naive MAD can amplify rather than correct biases (and how structured protocols help)

## License

MIT
