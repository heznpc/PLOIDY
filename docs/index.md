# Ploidy

**Same model, different context depths, better decisions.**

---

## What is Ploidy?

Ploidy is an MCP server that orchestrates **structured debates between multiple sessions of the same AI model** -- each with intentionally different amounts of context.

You open two terminals. Terminal 1 has been working on your project for hours -- it knows your codebase, your constraints, your prior decisions. Terminal 2 starts completely fresh. They debate a decision through a structured protocol, and because context is the *only* variable, every disagreement tells you something specific: Terminal 1 is anchored on something Terminal 2 questions, or Terminal 2 is missing context that Terminal 1 has.

The result is a structured synthesis -- not a majority vote, but an interpretable map of agreements, productive disagreements, and irreducible differences.

## Why Context Asymmetry Matters

When you've been deep in a project, your AI assistant has absorbed your assumptions along with your context. It knows your prior decisions and tends to build on them rather than question them. This is the **chat-chamber effect**: the longer a session runs, the more it reinforces its own framing.

Traditional multi-agent debate (MAD) tries to fix this by pitting *different models* against each other. But when GPT-4 disagrees with Claude, you can't tell if it's a meaningful difference or just a quirk of training data.

Ploidy takes a different approach: **same model, different context**. When two sessions of the same model disagree, the cause is clear -- one has context the other doesn't. That's a signal you can act on.

## Quick Example

```bash
# Terminal 1 -- you've been working here for an hour
# Start a debate about a decision you're facing
ploidy start "Should we use monorepo or polyrepo?"

# Terminal 2 -- fresh session, no prior context
# Join the debate with just the prompt
ploidy join debate-xxxx
```

Both terminals connect to the same Ploidy MCP server. They go through a structured protocol: independent analysis, position statements, challenges, and convergence. The output is a `DECISIONS.md` entry with the synthesized result.

## Current Status

!!! warning "Pre-alpha"

    Ploidy is in early development. The server runs, the debate protocol is defined, and MCP tools are registered. The full debate orchestration, convergence engine, and persistence layer are under active implementation.

## Next Steps

<div class="grid cards" markdown>

- [:material-rocket-launch: **Getting Started**](getting-started.md)

    Install Ploidy and run your first debate.

- [:material-lightbulb-on: **How It Works**](how-it-works.md)

    Understand the core concept and why it matters.

- [:material-file-tree: **Architecture**](architecture.md)

    Technical architecture and module overview.

- [:material-api: **API Reference**](api-reference.md)

    Complete MCP tool reference.

</div>
