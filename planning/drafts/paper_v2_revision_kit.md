# Paper v2 Revision Kit — Status: TODO container, not draft

## Purpose
Research + draft TODO for two Ploidy paper revisions based on Stage B 2026-04 retrospective.
Next session picks this up and drafts actual content with user.

## §2 Related Work — MAST Positioning TODO

### Context
MAST (Cemri et al. 2025) is the most recent empirical taxonomy of multi-agent LLM failures; it groups root causes into specification issues, inter-agent coordination issues, and verification issues. Ploidy's intentional context asymmetry sits squarely at the intersection of "specification ambiguity" and "verification gap", so citing MAST lets us position the contribution against a concrete, recent reference point rather than an abstract literature.

### References to gather
- MAST arxiv (HTML): https://arxiv.org/html/2503.13657v3
- MAST arxiv (abstract): https://arxiv.org/abs/2503.13657
- Cemri et al. 2025 full bibtex — TODO: add to references.bib
- Cross-check with existing related-work citations already in paper/main.tex §2 to avoid duplicate framing

### TODO checklist
- [ ] Obtain Cemri 2025 bibtex (arxiv BibTeX export)
- [ ] Verify references.bib compatibility (key naming convention, field completeness)
- [ ] Draft 1-paragraph positioning of Ploidy against MAST's 3 root causes
- [ ] Integrate into §2 Related Work as a new subsection "Multi-Agent Failure Taxonomies"
- [ ] Sanity-check that MAST framing doesn't conflict with existing §2 structure

### Open questions [USER TO DICTATE]
- Exact framing: Ploidy addresses "specification ambiguity × verification gap" intersection — is this the precise contribution claim?
- Citation style: primary or secondary?
- Placement inside §2: new subsection at the top, middle, or end?

## §5.22 R6-R11 Casebook Expansion TODO

### Context
Current §5.22 has R1-R5 from the design review. The Stage B 2026-04 redesign retrospective (conducted 2026-04-23) surfaced R6-R11 as new meta-failures observed inside a working session — these strengthen §5.22's claim that confirmation-bias failure modes persist intra-session even when the operator is aware of them.

### References
- Design review log (R1-R5 source): /Users/ren/IdeaProjects/Paper/ploidy/.claude/worktrees/affectionate-cohen-f52bc6/experiments/data/processed/design_review_2026-04-23/README.md
- MAST taxonomy mapping (see URL above in §2 TODO)
- Existing §5.22 casebook in paper/main.tex (for R1-R5 wording conventions)

### R6-R11 summary (one-liners, wording TBD)

| Code | One-liner | MAST root cause (proposed) |
|------|-----------|---------------------------|
| R6   | review mode role drift (session keeps reviewing, never builds) | Specification ambiguity |
| R7   | worktree isolation + parallel duplicate implementation | Coordination breakdown |
| R8   | background run observability blackout | Verification gap |
| R10  | spec-code coherence drift (spec says X, implementation does Y) | Specification ambiguity |
| R11  | pattern completion over authorization granularity (session fills underspecified parameters without asking) | Specification ambiguity (sub-class) |

### TODO checklist
- [ ] Confirm row wording with user (current one-liners are raw observation notes, not paper-ready)
- [ ] Decide whether R9 (parallel rate-limit) is included or combined with R7
- [ ] Draft casebook table for §5.22 matching existing R1-R5 table style
- [ ] 3 explanatory paragraphs connecting R6-R11 to MAST findings
- [ ] Update §5.22 in paper/main.tex

### Open questions [USER TO DICTATE]
- Final wording of each row (R6-R11)
- Whether to include R9 as its own row, fold into R7, or drop
- Depth of MAST mapping explanation — one sentence per row, or dedicated paragraph?
- Should R6-R11 stay under §5.22 or move into a new §5.23 given the volume jump?
