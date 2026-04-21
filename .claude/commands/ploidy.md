---
description: Run a context-asymmetric debate on the current question — Deep (full project context) vs Fresh (zero context) — and return the convergence result.
argument-hint: <decision question>
---

The user asked you to run a context-asymmetric debate on a decision using
Ploidy. Follow the three steps below without asking the user to confirm —
`/ploidy` is explicit consent to the whole flow.

The decision prompt is: **$ARGUMENTS**

## 1 · Write your own deep analysis

You already hold the full project context. In ~200 words, write the
deep-context position on the decision. List every bug, risk, or issue you
can find. Tag each with your confidence (HIGH / MEDIUM / LOW). Be
specific and technical — do not hedge.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool (subagent_type="general-purpose") to spin up a
subagent that sees only the decision prompt — no project context, no
repo paths, no prior conversation.

Prompt the subagent with:

> You have no background about this system. Analyse only the question
> itself: **$ARGUMENTS**
> List every bug, risk, or issue. Tag each finding HIGH / MEDIUM / LOW.
> Reply in under 200 words. Do not ask for more context.

Capture the subagent's return text as the fresh position.

## 3 · Converge and display

Call the Ploidy MCP tool:

```
debate(
    prompt="$ARGUMENTS",
    mode="solo",
    deep_position=<your step-1 text>,
    fresh_position=<subagent's step-2 text>,
)
```

If your deep analysis flagged concerns the fresh side missed, add them
as `deep_challenge`. If the fresh side surfaced something you
rationalised away, write `fresh_challenge`. Both are optional.

The tool response includes a `rendered_markdown` field that already
formats the confidence headline, a collapsed synthesis, and the full
transcript inside `<details>` blocks — the "answer first, expand for
internals" shape. **Output that string verbatim as your final reply.**
Do not rebuild the sections yourself, do not strip the `<details>`
blocks, do not dump the raw JSON around it.

Do not ask follow-up questions before showing the markdown.

## If something fails

- **Subagent refuses or returns empty** — rerun step 2 once with a
  tighter prompt. If it still fails, fall back to `mode="auto"` (needs
  `PLOIDY_API_BASE_URL`) or ask the user to provide the fresh
  perspective manually.
- **`debate` tool returns an error** — show the error verbatim, name
  the likely cause (usually a missing position or an API-key misconfig),
  and stop. Do not silently retry — that burns tokens without
  addressing the root cause.
- **Response has no `rendered_markdown` field** — you are talking to an
  older Ploidy (< v0.4.1). Fall back to formatting from `synthesis` +
  `points` manually, one section per category, confidence on top.
