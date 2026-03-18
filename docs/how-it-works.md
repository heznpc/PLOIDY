# How It Works

## The Problem: The Chat-Chamber Effect

When you work with an AI assistant in a long session, something subtle happens. The model absorbs not just your code but your framing. It learns your assumptions, your preferred patterns, your prior decisions. Over time, it stops questioning and starts reinforcing.

This is the **chat-chamber effect**: a single long-running session becomes an echo chamber of its own accumulated context. The AI confirms your biases because your biases *are its context*.

You might notice it when you ask "Should we refactor this module?" and the AI agrees -- because it was there when you decided to build it that way. It has sunk-cost reasoning baked into its context window.

## The Insight: Context Asymmetry Is a Feature

Traditional multi-agent debate (MAD) uses **different models** to generate disagreement. GPT-4 debates Claude. Gemini debates Llama. The theory is that model diversity produces better reasoning.

The problem: when different models disagree, you can't isolate *why*. Is it training data? Architecture differences? RLHF tuning? The signal is noisy and uninterpretable.

Ploidy inverts this. Instead of varying the model, we vary the **context**:

- **Same model** -- eliminates model-specific noise
- **Different context depths** -- creates interpretable asymmetry
- **Structured protocol** -- ensures disagreements are articulated, not just asserted

When two sessions of Claude (or Gemini, or any model) disagree, the cause is clear: one session has context that the other doesn't. That's actionable information.

## The Biology Metaphor

In biology, **ploidy** refers to the number of complete sets of chromosomes in a cell:

| Term | Sets | Example |
|------|------|---------|
| Haploid | 1n | Gametes (sperm, egg) |
| Diploid | 2n | Most human cells |
| Triploid | 3n | Some plants |
| Polyploid | Nn | Wheat, strawberries |

Each chromosome set carries its own version of the genome. Together, they provide genetic diversity that makes the organism more resilient. Polyploid organisms (with many sets) are often more robust -- wheat, for example, is hexaploid (6n) and thrives in conditions that would kill its diploid ancestors.

Ploidy the project works the same way:

- **Session A** (the deep set) carries full project context, prior decisions, learned patterns. It has wisdom, but also accumulated bias.
- **Session B** (the fresh set) enters with minimal context, asks naive questions, challenges assumptions. It lacks experience, but also lacks anchoring.
- **Sessions C, D, ...** (additional sets) can carry varying depths of context, enabling richer multi-perspective analysis.

The system is not limited to two sessions. Like polyploid organisms, Ploidy supports N sessions with varying context levels -- from fully loaded to completely fresh.

The metaphor operates at the **population level**, not the cellular level. In evolutionary biology, ploidy variation within a population is a primary driver of speciation and adaptive diversity -- diploid and tetraploid individuals of the same species coexist, and their differing chromosome counts produce different capabilities from the same underlying genome. The number of forms does not matter; it is the **existence of variation itself** that makes the population resilient. Similarly, Ploidy's value comes not from having a specific number of sessions, but from the fact that sessions with differing context depths -- the same model, different "dosages" of accumulated knowledge -- produce a diversity of perspectives that no single session can achieve alone.

## The Generational Dialogue Metaphor

There is another way to think about it: a conversation between generations.

Session A is the **experienced practitioner** who has been working in this domain for years. They know the codebase intimately, remember why certain decisions were made, and have developed strong intuitions. Their weakness: they may over-anchor on historical decisions, treating sunk costs as constraints.

Session B is the **fresh graduate** who just walked in. They have no context beyond the question asked. Their weakness: they may reinvent wheels or propose solutions that were already tried and failed. Their strength: they ask "but why?" without the baggage.

Neither perspective is correct on its own. The structured debate forces both to defend their reasoning, and the synthesis captures what survives scrutiny from both directions.

## The Debate Protocol

Ploidy debates follow a structured protocol with five phases:

### 1. Independent Analysis

Each session receives the decision prompt and analyzes it independently. The Deep session has its full project context; the Fresh session has only the prompt.

### 2. Position Declaration

Each session declares its stance on the decision. Positions must be specific and actionable, not vague preferences.

### 3. Challenge

Each session reads the other's position and responds using **semantic actions**:

| Action | Meaning | Example |
|--------|---------|---------|
| `agree` | "I reached the same conclusion" | "I agree that microservices add operational complexity we're not ready for." |
| `challenge` | "I disagree, here's why" | "You're assuming the team will grow, but the current plan is to stay at 3 engineers." |
| `propose_alternative` | "Neither position is right, consider this" | "Instead of monorepo or polyrepo, consider a modular monolith with clear module boundaries." |
| `synthesize` | "Both positions have merit, here's a synthesis" | "Use a monorepo for now with module extraction points marked for future separation." |

These semantic actions make the debate transcript **machine-interpretable**. The convergence engine uses them to classify points of agreement and disagreement.

### 4. Convergence

The convergence engine analyzes the full debate transcript and produces a structured result:

- **Agreements** -- Points where both sessions independently converged. These are high-confidence conclusions.
- **Productive disagreements** -- Points where the Fresh session raised a concern that the Deep session's context blinded it to. These are the most valuable outputs.
- **Irreducible disagreements** -- Genuinely different priorities or values that cannot be resolved by more information. These require a human decision.
- **Confidence score** -- How much of the debate space was resolved.

### 5. Complete

The debate result is persisted to SQLite and optionally appended to a `DECISIONS.md` file in the project root, creating a record of decisions and the reasoning behind them.

## The Output: DECISIONS.md

Every debate produces a structured decision record. Over time, these accumulate into a project's decision history -- an auditable trail of what was decided, why, and what the Fresh session questioned.

```markdown
## Decision: Monorepo vs. Polyrepo

**Date:** 2026-03-15
**Confidence:** 0.78

### Synthesis
Use a monorepo for the initial phase. Mark module boundaries explicitly
so that extraction to separate repos is low-cost if the team grows
beyond 5 engineers.

### Agreements
- Current team size (3) does not justify polyrepo operational overhead
- CI/CD pipeline simplicity matters more than repo isolation at this scale

### Productive Disagreements
- Fresh session questioned the assumption that "monorepo = monolith"
  -- this led to the modular monolith recommendation
- Fresh session identified that the polyrepo argument was anchored on
  a team growth projection with no committed timeline

### Irreducible Disagreements
- Deep session values consistency of shared tooling
- Fresh session values team autonomy in technology choices
- Resolution: deferred to team discussion
```
