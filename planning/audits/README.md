# Cross-Session Audits

Operationalises Ploidy on itself: multiple sessions of the same model
run `cross-session-review-prompt.md` independently against the
ploidy-research repository, write their findings to `runs/`, and a
separate convergence session reads only the per-role outputs (not the
underlying transcripts) to produce `<date>-convergence.md`.

## Layout

```
planning/audits/
├── README.md                          ← you are here
├── cross-session-review-prompt.md     ← the prompt (paste verbatim)
└── runs/
    ├── YYYY-MM-DD-HHMM-fresh-a.md     ← Fresh session A output
    ├── YYYY-MM-DD-HHMM-fresh-b.md     ← Fresh session B output
    ├── YYYY-MM-DD-HHMM-fresh-c.md     ← Fresh session C output (optional)
    ├── YYYY-MM-DD-HHMM-deep.md        ← Deep session output (transcript-bearing)
    └── YYYY-MM-DD-convergence.md      ← merge of the above, no transcripts
```

## How to invoke a new audit pass

1. **Pick the date** (UTC or KST, be consistent within a pass).
2. **Decide the roles**: minimum is `fresh-a + deep`; recommended is
   `fresh-a + fresh-b + deep`; full Ploidy is
   `fresh-a + fresh-b + fresh-c + deep + separate convergence`.
3. **For each role**, open a fresh Claude Code session at
   `/Users/ren/IdeaProjects/Paper/ploidy/`. Paste the contents of
   `cross-session-review-prompt.md` verbatim as the first user message.
   Append a single line at the end:
   ```
   My role is: fresh-a
   ```
   (or `fresh-b` / `fresh-c` / `deep`).
4. The session writes its output to
   `planning/audits/runs/<YYYY-MM-DD>-<HHMM>-<role>.md` and stops.
5. After all role outputs land, open one final fresh session for the
   convergence step. Paste only the role-output files (not the prompt,
   not the transcripts). Ask it to produce
   `runs/<YYYY-MM-DD>-convergence.md` highlighting:
   - claims all Fresh sessions agreed on but Deep disputed (or vice
     versa)
   - claims only Deep made that Fresh sessions independently flagged
     as unfalsifiable (§C1 entries)
   - disk-only catches that only one Fresh session raised (§C2
     entries) — strongest signal

## Discipline

- **Fresh sessions must not read** `~/.claude/projects/-Users-ren-IdeaProjects-Paper-ploidy/`
  jsonl transcripts or `memory/*.md` files. The prompt enforces this
  but you should also verify before invoking.
- **Deep sessions may read transcripts** but must tag every claim that
  depends on transcript evidence with `[from-transcript]`.
- **Convergence sessions read only the role outputs**. Never the
  underlying transcripts. This protects the convergence step from
  re-introducing the Deep anchoring it was meant to catch.

## Why not just trust the live Deep session

Every prior intra-session anchoring failure documented in
`paper/main.tex` §sec:implications happened *inside* a session that
was confident it had reviewed itself. The 6th case (2026-05-28) is
the most recent: a Deep session falsely claimed to have deleted a
contaminated directory; a cross-session audit found the directory
still on disk; the Deep session had been re-citing the false claim
across multiple chat turns. This is why audits run *across* sessions,
not within one.

If a cross-session audit pass produces useful Fresh-only catches,
those catches are themselves paper-thesis evidence and may be
incorporated into `paper/main.tex` §sec:implications as case #7+.

## Run history

| Date (KST) | Roles run | Convergence | Surfaced |
|---|---|---|---|
| 2026-05-27 | informal (one Fresh-like via separate Claude Code session) | manual | spec-v3 ↔ Line B undocumented; `040725` contaminated dir still on disk; `paper_v2_revision_kit.md` mis-classified as untracked |

The 2026-05-27 informal pass was the trigger for formalising this
audits/ infrastructure. Future passes log here with at least
`role-set / convergence-result-link / surfaced-issues` columns.
