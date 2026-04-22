---
description: Evaluate an architecture proposal — deep-context take (full system) vs first-principles (proposal only) — to catch sunk-cost rationalisation before the change lands.
argument-hint: <architecture proposal or design doc path>
---

The user is weighing an architecture-level change:

> **$ARGUMENTS**

You hold the existing system's context (modules, prior decisions, fail
modes, operational history). That is **precisely the bias** the
proposal is competing against — Ploidy's paper shows deep-context
reviewers anchor on "fits the current shape" over "is actually
correct". Run the four-step eval without asking to confirm.

## 1 · Write the Deep-context take

If `$ARGUMENTS` is a filepath (ends in `.md`, `.txt`, contains `/`),
read that file first via the Read tool. Otherwise treat it as the
proposal text.

In ~300 words:

1. **Fit** — how does the proposal interact with the current system?
   Name the modules it touches and the abstractions it respects or
   violates.
2. **Concrete risks** — what breaks, what gets slower, what becomes
   harder to test / deploy / observe?
3. **Sunk-cost check** — list what in your current system you find
   yourself *defending* here. For each, state whether the defense is
   "this abstraction is load-bearing" or "we just spent a lot building
   it". If nothing, say so explicitly.
4. **Non-obvious alternatives** — is there a version of the proposal
   that solves the same problem with less change? One sentence each.

Tag every concern HIGH / MEDIUM / LOW confidence.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool (`subagent_type="general-purpose"`). It must see
only the proposal text, no repo knowledge.

Prompt the subagent with exactly:

> You are evaluating an architecture proposal in a codebase you have
> never seen. Only the proposal text is available:
>
> <PROPOSAL TEXT — paste the expanded $ARGUMENTS here>
>
> Answer in under 250 words:
> 1. Stated in your own words, what problem is this trying to solve?
>    If the problem is unclear, say so — do not guess.
> 2. What assumptions is the proposal making about the existing
>    system? List each; mark ones that sound uncommon.
> 3. What are generic architectural alternatives (event-driven, batch,
>    read-model, CQRS, etc.) that the proposal does not mention? One
>    sentence each.
> 4. Where is the proposal most likely to be overcomplicating? Be
>    specific about which piece.
>
> Do not ask for repo links. Do not request more context.

Capture the reply as the fresh position.

## 3 · Converge via Ploidy

```
debate(
    prompt="Architecture: " + <one-line summary of proposal>,
    mode="solo",
    deep_position=<step-1 text>,
    fresh_position=<step-2 text>,
    deep_label="System-context",
    fresh_label="First-principles",
)
```

- `deep_challenge`: if Fresh suggested an alternative that the current
  system actually can't accommodate — say exactly why, with file/module
  names.
- `fresh_challenge`: if Fresh surfaced an assumption you were skipping.

## 4 · Present

Prepend:

> **Architecture review:** <one-line summary>

Output `rendered_markdown` verbatim. After the markdown, add:

> **Go / No-go recommendation:** <one of `proceed`, `revise scope`,
> `adopt Fresh's alternative`, `defer`> — one sentence justification.

Do not rewrite the rendered body. Do not dump JSON.

## If something fails

- Subagent returns empty → rerun with "Even a partial answer to one
  question is acceptable."
- `debate` errors → show verbatim, stop.
- Proposal text >10k chars → summarise to ~500 words for the Fresh
  prompt but keep the full text in your Deep analysis.
