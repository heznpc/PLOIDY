# Cross-Session Review Prompt — Ploidy 4th-Sweep State Audit

> **Goal**: Operationalise Ploidy on Ploidy. Multiple sessions of the same
> model run this prompt independently; their outputs are diffed; disagreements
> are the load-bearing signal. The Deep session (the one that produced the
> current main-branch state) cannot be trusted alone — every prior intra-session
> anchoring failure documented in `paper/main.tex` §sec:implications happened
> *inside* a session that was confident it had reviewed itself.

---

## 0. How to invoke

A fresh Claude Code (or compatible) session is opened at
`/Users/ren/IdeaProjects/Paper/ploidy/`. The full prompt below is pasted as
the initial user message, verbatim. No prior chat history is loaded. The
session writes its output to
`planning/audits/runs/<UTC-YYYY-MM-DD-HHMM>-<role>.md` where role is one of
`fresh-a`, `fresh-b`, `fresh-c`, `deep` (Deep = the session that holds the
state-producing transcript). At least two roles must run before convergence
is meaningful; three or more is preferred.

Convergence happens in a *separate* fourth session that reads only the
per-role audit outputs (not the underlying transcripts) and produces a
`<date>-convergence.md`. This protects against the convergence step
re-introducing the Deep anchoring it was meant to catch.

---

## 1. Identity and scope

You are a participant in a Ploidy cross-session audit of the
`ploidy-research` repository at
`/Users/ren/IdeaProjects/Paper/ploidy/`. Your role (`fresh-*` or `deep`)
is declared in the file name you will write to in §6. Treat the
declared role as binding: a `fresh-*` session must *not* read the
chat transcripts at `~/.claude/projects/-Users-ren-IdeaProjects-Paper-ploidy/`;
a `deep` session may read them but must annotate every claim that
depends on transcript evidence with `[from-transcript]`.

The repository is a paper + MCP-server monorepo (Brand5/Research,
Program 2 anchor). The paper is `paper/main.tex`, the pre-registration
log is `planning/decisions.md`, the runner is
`experiments/src/run_experiment.py`, and the latest sweep dirs are at
`experiments/results/2026052*/`.

**Time-sensitive work rule** (global, from `~/IdeaProjects/CLAUDE.md`):
capture `NOW`, `NOW_DATE`, `WINDOW_START` at session start and print them
verbatim at the top of your audit output. Every WebSearch query (if you
need them — usually you do not) must include a date anchor.

---

## 2. Read-only constraint

This is an **audit, not a fix**. You must not:

- Edit any committed file.
- Run any sweep cell (`python3 experiments/src/run_experiment.py`).
- Touch `experiments/results/2026052*/` contents.
- Commit, push, open PRs, or merge.

You may:

- Read any committed file.
- Run `git log`, `gh pr list`, `gh pr view`, `gh api repos/.../...`.
- Run analyse-only scripts (`python3 experiments/src/analyze_stats.py`)
  against existing result files.
- Read result JSONs and grep their contents.
- Write to `planning/audits/runs/<role>.md` — this is your only output channel.

If you find an issue that needs immediate action (e.g. an active
process leaking credentials), stop, document it as a §findings entry
with severity `CRITICAL-ACT-NOW`, and exit without acting. Acting is
a separate session.

---

## 3. The state inventory (every role does this verbatim)

Produce a deterministic state snapshot. Do not interpret it yet.

1. `date '+%Y-%m-%d %H:%M %Z'` → record as `NOW`.
2. `git log --oneline --since=2026-05-20 --until=NOW` → record all commits
   since the 2026-05-20 KST 4th-sweep launch.
3. `gh pr list --state merged --search 'merged:>=2026-05-20' --limit 50`
   → record number, title, mergedAt for each.
4. For every `experiments/results/2026052*/` directory:
   - `ls *.json | wc -l` (cell count, excluding `summary.json` and
     `.contaminated.json` and `secondary_judge_kappa.json`)
   - presence of `.contaminated.json` marker (yes / no)
   - presence of `secondary_judge_kappa.json` (yes / no, plus
     `kappa` value if present)
5. `grep -nE '^## 2026-' planning/decisions.md` → list every dated
   entry header in the pre-registration log.
6. `grep -nE '\\label\\{(sec|tab):' paper/main.tex` → list every labelled
   anchor in the paper.

Paste the raw outputs of all six in a `### A. State inventory (raw)`
section of your audit file. **Do not paraphrase.** Future merge passes
need the verbatim text.

---

## 4. Five mandatory consistency checks

For each check below, emit a `### B<N>. <name>` subsection with the
result. The expected outcomes column tells you what `PASS` looks like
— but the audit is more valuable when you can articulate a `FAIL` and
which file:line evidences it.

### B1. Decision-log ↔ paper consistency

For every `## 2026-05-*` entry in `planning/decisions.md`, identify
the corresponding paragraph or section in `paper/main.tex` that
operationalises the entry's `**Decisions**` block. If an entry has
no paper-side counterpart, that is a `FAIL: paper drift`.

Specifically check that these decisions have paper-side text:

- `2026-05-21` original pre-registration → §sec:threshold falsification
  criteria
- `2026-05-21` Major amendment → §sec:threshold anti-circularity +
  context-length-gradient paragraphs
- `2026-05-21` model-version drift → §sec:experiments "Model transition
  mid-program" paragraph
- `2026-05-27` 44-cell partial pilot amendment → §sec:threshold
  falsification triple amended for `{F1, recall}` co-primaries
- `2026-05-27` κ gate executed (κ = 0.768) → either §sec:partial-pilot
  or §sec:threshold (current state: the partial-pilot section was
  reverted on commit `01c72e3` — note whether the κ result is still
  cited anywhere in the paper after the revert)
- `2026-05-27` audit trail spec-v3 ↔ Line B → likely no paper-side
  counterpart yet (acceptable; this is a planning entry)
- `2026-05-27` contaminated dir preserved as evidence → likely no
  paper-side counterpart yet (acceptable for now; the dir is gitignored)

### B2. Result-dir ↔ marker consistency

For each `experiments/results/2026052*/`:

- If `.contaminated.json` exists, verify:
  - `do_not_use_for` lists at least F1, recall, and any aggregate
  - `valid_replacement_dir` points at a sibling dir that exists
  - At least one cell JSON in the contaminated dir has either
    `judgment.parse_error == true` *or* `f1 < 0.05` *or* an
    `output` string containing "fabrication" / "refus" /
    "casebook" / "recurrence" — confirming the marker's claim
- If no marker but the dir holds < 30 cells, that is suspicious
  (small dir, possibly aborted) — flag as `INVESTIGATE`
- If a marker exists but `analyze_stats.py` does not check for it,
  that is `FAIL: marker ignored downstream`

### B3. Result-JSON model-field consistency

Sample 5 cells per directory at random. Confirm every sampled JSON has
`model` set to `claude-opus-4-7`. Any other value is `FAIL: model
drift` *unless* the directory mtime is before 2026-04-23 (in which
case `claude-opus-4-6` is correct).

### B4. Memory-contamination ground-truth

For each non-contaminated `2026052*/` directory: pick one cell at
random, read its `output` and `judgment.summary` fields. Search for
the substrings: "fabrication", "refus", "casebook", "recurrence",
"memory file", "project_*_review_*", "self-quote".

- Zero hits across all sampled cells → cwd-neutral patch is working
- Any hit on a `2026052*` dir mtime *after* 2026-05-21 18:00 KST
  (the PR #57 merge time) → `FAIL: contamination persists`

### B5. Asymmetric port spec-v3 → main

Run `git diff v0.5-experiments-spec-2026-04-30 main -- experiments/src/tasks_*.py`.
The diff should show the v0.5 tag has files / definitions that main
lacks (AD1-AD4 adversarial task definitions per the 2026-05-27
decision log).

- Asymmetric in the v0.5 → main direction: `PASS` (recorded gap)
- Symmetric (both have AD1-AD4): `FAIL` — decisions.md asymmetry
  claim is wrong, paper does not reflect this either
- Asymmetric in the main → v0.5 direction (main has tasks v0.5
  lacks): `INVESTIGATE` (drift the audit-trail did not predict)

---

## 5. Two open-ended sections

### C1. "What I cannot verify from disk"

List, in bullet form, every claim in the most recent three
`planning/decisions.md` entries (the two 2026-05-27 entries and the
2026-05-21 Major-amendment entry) that you, as a session reading only
disk + git state, cannot falsify. Examples of unfalsifiable-from-disk
claims:

- "The user's intent from the start was *X*."
- "The author of the 4th-sweep replication line inherited Line B as
  the active path without re-deriving the choice."
- "I (current session) … recommended paper write-up after seeing the
  F1*/recall headline."

These are claims that *only* a transcript-bearing session can
evaluate. Listing them isolates the dependency: if a transcript-bearing
Deep session later re-asserts them, Fresh sessions can document that
those re-assertions are *not independently verifiable* — exactly the
asymmetry Ploidy is built to surface.

### C2. "Disk-only catches" (Fresh-only signal)

Walk the repository and report anything that surprised you, regardless
of whether the decisions.md log mentions it. Examples of valuable
disk-only catches:

- Untracked files in the working tree that look paper-relevant
- `.gitignore` patterns that mask result files the paper claims to
  use
- Test failures (`pytest --collect-only` for now; do not run)
- Branches on origin not merged to main that have meaningful diffs
- Worktrees with old commits and no obvious owner
- LaTeX warnings or undefined references the paper PDF build would
  raise
- Memory index entries (`~/.claude/projects/<encoded-cwd>/memory/*.md`)
  not referenced by any planning file — note role: `fresh-*` must
  **not** read these files; only `deep` may, and any deep findings
  here must be flagged `[from-transcript]`

The most valuable Fresh-only catches are ones that nobody (including
the Deep author) has yet noticed. If your role is `fresh-*` and you
catch nothing here, write a short paragraph explaining what you
*looked at* anyway — that is itself useful for the convergence step.

---

## 6. Output file

Write exactly one file:

```
planning/audits/runs/<YYYY-MM-DD>-<HHMM>-<role>.md
```

Where `<role>` is one of `fresh-a`, `fresh-b`, `fresh-c`, `deep`,
declared at invocation time. Multiple `fresh-*` runs are encouraged
(stochastic-N at the audit layer).

Required top-of-file metadata:

```yaml
---
role: fresh-a   # or fresh-b, fresh-c, deep
now: 2026-MM-DD HH:MM KST
now_date: 2026-MM-DD
window_start: 2026-MM-DD
git_head_at_audit_start: <SHA>
prompt_version: 2026-05-28
---
```

Required sections, in order:

1. `## A. State inventory (raw)` — §3 verbatim
2. `## B1. Decision-log ↔ paper consistency`
3. `## B2. Result-dir ↔ marker consistency`
4. `## B3. Result-JSON model-field consistency`
5. `## B4. Memory-contamination ground-truth`
6. `## B5. Asymmetric port spec-v3 → main`
7. `## C1. What I cannot verify from disk`
8. `## C2. Disk-only catches`
9. `## D. Single-paragraph summary` — under 100 words, what changed,
   what is broken, what should next session do
10. `## E. Recommended decisions.md amendment` (optional) — bulleted,
    not prose. If you have nothing to add here, write `None.`

Length cap: 2000 lines per output file. If a single section runs over
500 lines, paginate by topic into `<...>-<role>-part1.md`,
`<...>-<role>-part2.md`, etc.

---

## 7. What success looks like

Convergence (in the separate fourth session) is meaningful when:

- Multiple `fresh-*` outputs agree on §B1–B5 verdicts
- The `deep` output adds `[from-transcript]` content the Fresh
  sessions explicitly listed as unfalsifiable in §C1
- At least one Fresh session catches a §C2 issue the Deep session
  did not raise
- At least one `fresh-*` ↔ `deep` disagreement is recorded — agreement
  on everything signals the Fresh sessions have anchored on the same
  document as Deep (which would be a Ploidy protocol violation)

Disagreement is the signal. Agreement on the disk-state inventory is
table stakes; agreement on the interpretive sections (§C1, §C2) is
suspicious.

---

## 8. Do-not-do list (re-affirmation)

- Do not edit `paper/main.tex`, `planning/decisions.md`,
  `experiments/src/*.py`, or any committed file.
- Do not run `experiments/scripts/run_4th_sweep.sh` or any sub-runner.
- Do not push, merge, or open PRs.
- Do not call any tool that costs > $0.10 in API charges (this audit
  is a Max-subscription / free-tier-only operation).
- Do not, as a Fresh session, read
  `~/.claude/projects/-Users-ren-IdeaProjects-Paper-ploidy/` jsonl or
  memory files. Read only the on-disk repository.

---

## Appendix: Why this prompt looks the way it does

This prompt is itself a Ploidy-style intervention against the
intra-session anchoring failure mode documented in `paper/main.tex`
§sec:implications. The current Deep session (the one that produced the
present main-branch state) cannot be trusted alone, because the
prior 5+ intra-session anchoring cases in §sec:implications all
happened *inside* a session that was confident it had reviewed
itself. The 6th case (logged informally in chat on 2026-05-28 but
not yet in §sec:implications) is the most recent: a Deep session
claimed to have deleted a contaminated directory; a cross-session
audit found the directory still on disk; the Deep session had been
re-citing the false claim across multiple chat turns.

If this prompt produces useful Fresh-only catches, those catches are
themselves paper-thesis evidence and may be incorporated into
§sec:implications as case #7+.
