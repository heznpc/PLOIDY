---
description: Pressure-test a deprecation decision — builder's view (knows why it exists, who depends on it) vs cold reader (just sees the thing and the question "should this go?") — to catch attachment-driven maintenance.
argument-hint: <thing to deprecate — module, feature, or file path>
---

The user is considering removing / deprecating:

> **$ARGUMENTS**

You know why this was built, who uses it, how much effort went in.
**That history is how sunk-cost keeps dead code alive** — Ploidy's
result applies symmetrically: context-rich reviewers defend old
investments past their usefulness.

## 1 · Write the Builder's take

If `$ARGUMENTS` is a file path, read the file first. If it's a
module / feature name, grep the repo for call sites and summarise
their shape.

In ~250 words:

1. **Why it exists** — one sentence of the original motivation.
   State the year / quarter if you can.
2. **Who actually uses it today** — concrete call sites, tests,
   external consumers. "Team uses it" is not enough; name the paths
   or endpoints.
3. **Attachment check** — what are you finding yourself saying to
   *defend* keeping it? For each, say whether the defense is (a)
   concrete (a real user / test / revenue depends on it) or (b)
   sentimental ("it was fun to build", "might be useful someday",
   "generalised at the time").
4. **Cost of keeping** — enumerate: CI time, surface-area-cognitive
   load for new contributors, risk of stale dependencies, migration
   debt when the surrounding system changes.
5. **Cost of removing** — enumerate: migration work, breakage for
   known callers, feature loss.

Tag each finding HIGH / MEDIUM / LOW.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool. The fresh reviewer sees only: the thing's public
description, its external interface, and the question "should this be
removed?"

Prompt:

> You are evaluating whether a software component should be removed
> from a codebase. You have never seen this codebase or the component
> before. Only the public interface and description are available:
>
> <PUBLIC INTERFACE + DESCRIPTION>
>
> Answer in under 200 words:
> 1. What does this component do? State it in plain language.
> 2. Is the problem it solves one that is still common in 2026?
> 3. Are there obvious simpler / newer alternatives that solve the
>    same problem? Name them generically.
> 4. Given only this, would you build this component from scratch
>    today? Yes / no, one sentence why.
>
> Do not ask for call-site information. Do not guess at internal
> context.

Capture the reply as fresh.

## 3 · Converge via Ploidy

```
debate(
    prompt="Deprecate: " + <thing>,
    mode="solo",
    deep_position=<step-1>,
    fresh_position=<step-2>,
    deep_label="Builder",
    fresh_label="Cold-reader",
)
```

- `deep_challenge`: if Fresh missed a real user you've named in step
  1.2 — quote that call site.
- `fresh_challenge`: if Fresh's "don't build this today" is correct
  and your defenses in step 1.3 were (b)-sentimental.

## 4 · Present

Prepend:

> **Deprecation review:** <thing>

Output `rendered_markdown` verbatim. Append one-line disposition:

> **Recommended action:** `keep`, `deprecate with migration period`,
> `delete immediately`, or `keep but freeze (no new features)` —
> single sentence rationale.

Do not rewrite markdown. Do not dump JSON.

## If something fails

- No public interface to show Fresh (pure-internal module) → describe
  its role at the interface boundary that *does* exist. E.g. for a
  CLI subcommand, show the help text.
- Fresh refuses → rerun with "Even a yes/no on question 4 is useful."
- `debate` errors → show verbatim, stop.
