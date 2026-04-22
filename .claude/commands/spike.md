---
description: Sanity-check a design idea BEFORE implementation — runs a Ploidy debate between the full-context view and a zero-context fresh sub-agent to surface rationalisation before code gets written.
argument-hint: <idea or design proposal>
---

The user is asking for a pre-implementation gut check on the following
idea:

> **$ARGUMENTS**

You hold full project context (repo layout, prior decisions, constraints).
That context is **exactly what biases you** — Ploidy's paper shows that
Deep sessions rationalise ideas that fit the existing system even when
they are objectively weak. Run the four-step spike without asking the
user to confirm.

## 1 · Write the Deep-context take

In ~200 words, answer these in order:

1. **Fit** — does this idea slot cleanly into the existing architecture?
   Name the concrete touch points.
2. **Implementation risks** — what will actually break or be annoying?
   Be specific (files, components, tests, deploy paths).
3. **Honesty check** — what piece of your support for this idea is
   because it's *convenient to build* rather than *correct*? If none,
   say so explicitly.

Tag every risk / concern HIGH / MEDIUM / LOW. Do not hedge.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool (`subagent_type="general-purpose"`). It must see only
the idea, not the repo.

Prompt the subagent with exactly:

> You have no background about any existing system. Evaluate this idea
> on its own merits: **$ARGUMENTS**
>
> Cover in under 200 words:
> 1. What problem does this solve? State it in your own words — if you
>    can't, say "unclear".
> 2. What assumptions does the idea rely on?
> 3. What would make this a *bad* idea, assuming nothing about the
>    existing stack?
>
> Do not ask for more context. Do not request a repo link.

Capture the subagent's reply as the fresh position.

## 3 · Converge via Ploidy

Call the `debate` MCP tool:

```
debate(
    prompt=$ARGUMENTS,
    mode="solo",
    deep_position=<your step-1 text>,
    fresh_position=<subagent's step-2 text>,
    deep_label="Project-context",
    fresh_label="First-principles",
)
```

Add a `deep_challenge` if you found Fresh missing a project-specific
constraint. Add a `fresh_challenge` if Fresh surfaced an assumption you
were glossing over. Both optional.

## 4 · Present the verdict

The tool response includes a `rendered_markdown` field with the
confidence headline + collapsed `<details>` for the transcript. **Output
that string verbatim** as your final reply.

Above the rendered output, prepend one line:

> **Spike verdict for:** *$ARGUMENTS*

Do not rewrite the markdown. Do not dump raw JSON. Do not ask follow-up
questions before showing the verdict — if confidence is low or
disagreements are irreducible, the verdict itself says so and the user
will steer from there.

## If something fails

- **Subagent refuses or returns empty** — rerun step 2 once with
  "Answer in bullet points, any reasoning is fine, even 'unclear'". If
  still empty, fall back to `mode="auto"` (needs `PLOIDY_API_BASE_URL`).
- **`debate` returns an error** — show the error verbatim and stop.
  Likely cause: missing position text. Do not silently retry.
- **Response missing `rendered_markdown`** — server is pre-v0.4.1.
  Format manually from `synthesis` + `points`, one section per
  category, confidence on top.
