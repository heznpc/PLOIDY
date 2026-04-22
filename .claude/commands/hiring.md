---
description: Hiring decision second opinion — manager's view (full résumé + interview context + team fit) vs identity-blind qualifications-only view — to catch familiarity / pedigree bias in candidate evaluation.
argument-hint: <candidate name or résumé file path>
---

The user is evaluating a hiring candidate:

> **$ARGUMENTS**

You know the team's current composition, who's already on the loop,
what the hiring manager said in hallway chatter, the candidate's
school / last employer pedigree. **That context is precisely where
similarity bias enters** — "good cultural fit" and "from a place we
trust" are classic rationalisation patterns that selection-studies
have measured. Run the four-step pass without asking.

## 1 · Write the Manager's take

If `$ARGUMENTS` is a file path, read the résumé / interview notes.
Otherwise treat it as the candidate name and locate the file in a
sensible place (`hiring/<name>/`, `resumes/`).

In ~300 words:

1. **Role fit (concrete)** — which job-description requirements does
   the candidate meet, with evidence from the résumé. List met /
   partial / missing.
2. **Interview signal** — what came up in the interview(s) that's
   *specific* to this candidate. Not "seemed thoughtful" — what did
   they say or build?
3. **Similarity-bias check** — list every reason you're finding
   yourself favourable that is actually *similarity* rather than
   *signal*: same school as the manager, same prior employer as
   half the team, same technical taste, same communication style.
   Label each "similarity" vs "signal".
4. **Gap check** — what requirement is *least* well-evidenced? Be
   honest even if the rest looks strong.

Tag each finding HIGH / MEDIUM / LOW.

## 2 · Spawn a Fresh sub-agent

Use the Agent tool. Sanitise the résumé before passing:

- Strip: full name, school names, employer names, physical location,
  photo references, dates more specific than years.
- Keep: job title progression (by generic rank/scope), skills list,
  project descriptions (with proper nouns replaced by "a company"
  / "a product"), years of experience, education *level* only.

Prompt the subagent with:

> You are evaluating a candidate for a software role. You have only
> the sanitised résumé and the job requirements. You do not know the
> candidate's name, school, employer, or demographics.
>
> **Job requirements:**
> <JD REQUIREMENTS>
>
> **Sanitised résumé:**
> <SANITISED TEXT>
>
> Answer in under 250 words:
> 1. For each listed job requirement, is there evidence in the
>    résumé? Met / partial / missing — cite the specific résumé
>    line.
> 2. What does the trajectory of the candidate's roles and scope
>    suggest about their growth curve?
> 3. What project or experience stands out *on its own technical
>    merit*, independent of where it was done?
> 4. What gaps or concerns do you see — where would you probe in a
>    follow-up interview?
>
> Do not ask for identifying information. Do not guess at
> employer / school.

Capture the reply as fresh.

## 3 · Converge via Ploidy

```
debate(
    prompt="Hiring: " + <candidate-role> + " (" + <level> + ")",
    mode="solo",
    deep_position=<step-1>,
    fresh_position=<step-2>,
    deep_label="Manager",
    fresh_label="Identity-blind",
)
```

- `deep_challenge`: Fresh rated a skill weak, but the interview
  produced specific evidence that the résumé bullet alone can't
  convey — quote the interview signal.
- `fresh_challenge`: Fresh surfaced a gap you'd rationalised past
  because of similarity signal.

## 4 · Present

Prepend:

> **Hiring review:** <role, level>

Output `rendered_markdown` verbatim. Append one-line disposition:

> **Recommendation:** `hire`, `hire at lower level`, `no-hire`,
> `more evidence (name specific probe)` — one sentence justification.

Do not rewrite the rendered body. Do not surface candidate identity
in the final output beyond what's needed for the role line above.

## If something fails

- Can't fully sanitise (names deeply interleaved in project
  descriptions) → do your best, note the caveat at the top of the
  Fresh prompt ("some proper nouns may remain; disregard them").
- Fresh refuses to evaluate → rerun with "Even partial ratings for
  some requirements are useful."
- `debate` errors → show verbatim, stop.

## Important

This skill is a bias counterweight, not a decision oracle. The goal
is to make similarity-driven reasoning *visible* so you can discount
it deliberately — not to rubber-stamp hires. If the Fresh and Deep
analyses converge on uncertainty, the answer is **run another round
of evaluation**, not "pick one".
