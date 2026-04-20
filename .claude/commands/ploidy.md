---
description: Run a context-asymmetric debate on the current question — Deep (full project context) vs Fresh (zero context) — and return the convergence result.
argument-hint: <decision question>
---

The user asked you to run a context-asymmetric debate on a decision using
Ploidy. Follow these four steps without asking the user to confirm —
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

## 3 · Converge via Ploidy

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

## 4 · Present the synthesis

Render the tool response like this:

1. **Agreements** (confidence bar + the agreed points)
2. **Productive disagreements** (each side's view + where the truth
   probably lies)
3. **Irreducible disagreements** (state them plainly; do not paper over)
4. **Recommendation** — one paragraph the user can act on

Do not dump the raw JSON. Do not re-explain Ploidy. Do not ask
follow-up questions before presenting step 4.

## If something fails

- **Subagent refuses or returns empty** — rerun step 2 once with a
  tighter prompt. If it still fails, fall back to mode="auto" (needs
  `PLOIDY_API_BASE_URL`) or ask the user to provide the fresh
  perspective manually.
- **`debate` tool returns an error** — show the error verbatim, name
  the likely cause (usually a missing position or an API-key misconfig),
  and stop. Do not silently retry — that burns tokens without
  addressing the root cause.
