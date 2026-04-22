---
description: Run a Ploidy debate on a post-mortem — context-rich account (knows history, people, prior judgements) vs timeline-only reader — to surface blame anchoring and unexplored root causes.
argument-hint: <incident summary or post-mortem file path>
---

The user wants a second pass on an incident analysis:

> **$ARGUMENTS**

You hold the context: who was on-call, what the team already blamed,
how similar incidents played out, which systems had prior issues.
**That context is how blame-anchoring creeps in** — once "ah, it was
the retry storm again" becomes the narrative, reviewers stop looking.
Run the four-step pass without asking.

## 1 · Write the Deep-context take

If `$ARGUMENTS` is a path (ends in `.md` / contains `/`), read the
file first. Otherwise treat it as the incident summary.

In ~300 words:

1. **Proximate cause** — the one-step-back trigger, stated plainly.
2. **Root causes (candidates)** — list every plausible contributing
   factor. For each: technical / process / organisational.
3. **Blame anchoring check** — list who or what in this incident the
   team is *already* converging on as responsible. For each, state
   whether the convergence is (a) backed by the timeline or (b)
   convenient because the target has a track record.
4. **Unasked questions** — three questions the post-mortem has not
   asked but probably should.

Tag every candidate cause HIGH / MEDIUM / LOW confidence.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool (`subagent_type="general-purpose"`). It must see
only the timeline of events, no names of teams, no history of prior
incidents.

Sanitise the input: strip team / person names, prior-incident
references, and any "as usual / again / typical" phrases. Replace
names with roles ("on-call engineer", "service owner"). Keep
technical facts intact.

Prompt the subagent with:

> You are reading the timeline of an incident in a system you have
> never seen. Only the sanitised timeline is available:
>
> <SANITISED TIMELINE>
>
> Answer in under 250 words:
> 1. What is the most likely proximate cause, stated as one sentence?
> 2. List every plausible root cause you can infer from the timeline
>    alone. For each, say what the timeline would need to show to
>    confirm or refute it.
> 3. What information is missing from the timeline that, if present,
>    would change your assessment?
> 4. What recurring failure patterns in generic distributed systems
>    does this timeline match (retry storm, thundering herd, partial
>    deployment, clock skew, quota exhaustion, …)?
>
> Do not ask for context. Do not guess at team / org details.

Capture the reply as the fresh position.

## 3 · Converge via Ploidy

```
debate(
    prompt="Post-mortem: " + <one-line incident summary>,
    mode="solo",
    deep_position=<step-1>,
    fresh_position=<step-2>,
    deep_label="Context-rich",
    fresh_label="Timeline-only",
)
```

- `deep_challenge`: if Fresh raised a candidate the timeline actually
  rules out — cite the timeline event that rules it out.
- `fresh_challenge`: if Fresh surfaced a root cause you hadn't even
  considered because familiarity steered you elsewhere.

## 4 · Present

Prepend:

> **Post-mortem second opinion:** <incident summary>

Output `rendered_markdown` verbatim. After the markdown, add one line:

> **Action change:** `none` if the team's current fix still holds, or
> name the specific change — e.g. "add chaos test for the retry
> storm case the Fresh reviewer identified."

Do not dump raw JSON. Do not re-narrate.

## If something fails

- Can't sanitise cleanly (names deeply interleaved) → run the Fresh
  prompt with a note "some role labels may remain; please ignore
  who-did-what".
- Subagent refuses → rerun with "Even if you can only match this to
  one generic failure pattern, that's useful."
- `debate` errors → show verbatim, stop.
