---
description: Evaluate a product decision — maker's view (knows users, history, constraints) vs first-time-reader view (spec only) — to catch sunk-cost feature bias and "because we always do it this way" product choices.
argument-hint: <feature proposal or one-pager path>
---

The user is deciding on a product / feature question:

> **$ARGUMENTS**

You hold product context: user research, prior launches, roadmap
promises, stakeholder positions. **Same problem as the engineering
version** — Ploidy shows context-rich reviewers rationalise features
that fit existing investments even when they wouldn't be built from
scratch. Run the four-step without confirming.

## 1 · Write the Maker's take

If `$ARGUMENTS` is a path, read the file first.

In ~300 words:

1. **Problem statement** — who is the user, what's broken for them?
   State it in language the user would actually use, not PM-ese.
2. **Why this solution** — the specific mechanism the proposal picks,
   and what the alternatives would have been.
3. **Sunk-cost check** — what part of this proposal is because we've
   already built something adjacent (platform reuse) vs because it's
   the right answer? For each line item, label "load-bearing reuse"
   vs "convenient reuse".
4. **Who this hurts** — any segment or existing user who gets worse
   off. If none is named explicitly, name who you think it is.

Tag each finding HIGH / MEDIUM / LOW.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool. The fresh reviewer sees only the one-pager /
proposal text, no company context, no user research, no roadmap.

Sanitise: strip company / product / competitor names, prior-launch
references, and any "we already know our users want X" claims.
Replace with generic roles ("the user", "the product").

Prompt the subagent with:

> You are evaluating a product feature proposal. You have never seen
> this product. You know nothing about the company's prior launches,
> users, or stated roadmap. Only the sanitised proposal is available:
>
> <SANITISED PROPOSAL>
>
> Answer in under 250 words:
> 1. What problem is this supposed to solve? State it in plain
>    language. If unclear, say so.
> 2. Given only this proposal, what are the simplest possible
>    solutions to that problem? List 3, shortest-first. Does the
>    proposal match any of them?
> 3. What assumptions about the user does the proposal rely on?
>    Which of those would you want evidence for before shipping?
> 4. Is this feature worth building at all, given only what is
>    written here? One sentence verdict with reasoning.
>
> Do not ask for more context. Do not invent company details.

Capture the reply as the fresh position.

## 3 · Converge via Ploidy

```
debate(
    prompt="Product decision: " + <one-line summary>,
    mode="solo",
    deep_position=<step-1>,
    fresh_position=<step-2>,
    deep_label="Maker",
    fresh_label="First-time-reader",
)
```

- `deep_challenge`: Fresh rejected a feature that actual user research
  clearly justifies → cite the research.
- `fresh_challenge`: Fresh suggested the problem could be solved
  without this feature and you don't have a good reply.

## 4 · Present

Prepend:

> **Product decision:** <summary>

Output `rendered_markdown` verbatim. Append:

> **Disposition:** `build`, `build smaller`, `not now`, or `don't
> build` — one sentence.

Do not rewrite markdown. Do not dump JSON.

## If something fails

- Spec unclear even after reading the file → output "Spec lacks
  enough detail for a useful second opinion. Specific gaps:
  <list>" and stop. Do not spawn the sub-agent with an incoherent
  proposal.
- Sub-agent refuses → rerun with "Even a verdict on one of the four
  questions is useful."
- `debate` errors → show verbatim, stop.
