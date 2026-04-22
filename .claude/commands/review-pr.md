---
description: Run a Ploidy debate on a pull request — deep-context reviewer vs zero-context reviewer that sees only the diff + description — to catch over-engineering, scope creep, and rationalised author bias before merge.
argument-hint: [pr-number] (default = current branch's PR)
---

The user wants a second-opinion review on a pull request before merging.
If `$ARGUMENTS` is empty, target the **current branch's** PR; if it's a
number or `#N`, target that PR on the configured remote.

## 1 · Gather the PR payload

Decide the target:
- If `$ARGUMENTS` is blank → `gh pr view --json title,body,author,headRefName,baseRefName,url`
  for the current branch.
- If `$ARGUMENTS` is a number → `gh pr view $ARGUMENTS --json title,body,author,headRefName,baseRefName,url`.

Then capture the diff:
- `gh pr diff <target>` — limit to ~3000 lines for the fresh payload.
  If larger, keep the full diff for the Deep step and pass a
  `<head>` + `<tail>` + `<... N lines elided ...>` truncation to the
  Fresh sub-agent.

Store:
- `pr_title`, `pr_body`, `pr_url`, `base_ref`, `head_ref`
- `diff_full` (for Deep), `diff_compact` (for Fresh)

## 2 · Write the Deep-context review

You have the full repo. In ~250 words:

1. **Stated goal check** — does the diff actually achieve what the PR
   body claims? Quote the specific claim and mark match / partial /
   mismatch.
2. **Scope discipline** — is anything in the diff *unrelated* to the
   stated goal? Flag each file that looks scope-creeping.
3. **Over-engineering** — are there abstractions, generalisations, or
   tests added "because we always do that" rather than *needed* for
   this change? Name them. If none, say so.
4. **Coverage gaps** — given your knowledge of the repo, what *didn't*
   get touched that probably should have? (migrations, docs,
   `CONVENTIONS.md`, call sites elsewhere, …)
5. **Author-bias check** — what in the PR author's decisions do you
   find yourself defending because *you also would have written it
   that way*? Name it explicitly. If nothing, say so.

Tag each finding HIGH / MEDIUM / LOW.

## 3 · Spawn a Fresh sub-agent

Use the Agent tool (`subagent_type="general-purpose"`). The fresh
reviewer must see only the PR description + the (possibly truncated)
diff — **no** repo context, **no** CLAUDE.md, **no** prior
conversation.

Prompt the subagent with exactly:

> You are reviewing a pull request in a repo you've never seen.
> You have only the PR description and the diff.
>
> **PR title:** <pr_title>
>
> **PR description:**
> <pr_body>
>
> **Diff:**
> <diff_compact>
>
> Answer in under 250 words:
> 1. What does this change try to do? State it in your own words.
> 2. What's unclear from the diff and description alone — anything
>    that forces you to *guess* about context?
> 3. What looks over-built or misaligned with the stated goal?
> 4. What classes of risk does this diff introduce (security, data
>    loss, backward compat, performance)?
>
> Do not request a repo link. Do not ask clarifying questions.

Capture the subagent's reply as the fresh position.

## 4 · Converge via Ploidy

Call the `debate` MCP tool:

```
debate(
    prompt="PR review: " + pr_title,
    mode="solo",
    deep_position=<your step-2 text>,
    fresh_position=<subagent's step-3 text>,
    deep_label="Repo-context",
    fresh_label="Diff-only",
)
```

- Add `deep_challenge` if the fresh reviewer raised a concern that you
  can confidently rebut with context (quote the context).
- Add `fresh_challenge` if the fresh reviewer surfaced something you
  were rationalising (own it plainly).

## 5 · Present

Prepend one header line:

> **PR review:** <pr_title> (<pr_url>)

Then output the tool response's `rendered_markdown` field verbatim.

After the markdown, add a single-line recommendation from your own
judgement:

> **Suggested action:** one of `merge as-is`, `revise <specific item>`,
> `split into N PRs`, `do not merge` — one line, named item.

Do not rewrite the rendered markdown body. Do not ask follow-up
questions before showing the review.

## If something fails

- **`gh pr view` errors** — no PR for current branch. Ask the user for
  a PR number or say "current branch has no open PR, nothing to
  review" and stop.
- **Diff is enormous** (>10k lines) — still do the review but warn in
  the header line that Fresh saw a truncated diff.
- **Subagent refuses** — rerun step 3 with "Even if you can only
  comment on one of the four questions, answer that one". Do not
  fall back to `mode="auto"` here — auto mode regenerates positions
  and the whole point of this skill is to review a *specific* diff.
- **`debate` returns an error** — show verbatim and stop.
- **Response missing `rendered_markdown`** — server is pre-v0.4.1.
  Format manually from `synthesis` + `points`.
