# Research Decisions Log

Records non-obvious choices with rationale. Append-only; don't rewrite history.

Format: `## YYYY-MM-DD -- <short title>` with **Context**, **Decision**, **Why**.

---

## 2026-04-20 -- Claude Code session extraction pipeline

**Context**: Past experiments ran via Claude Code `Bash` tool calls invoking
`experiments/src/run_experiment.py` (and siblings). The script normally writes
results to `experiments/results/<timestamp>/`, but several runs during
2026-04-07~16 produced no such directory — interrupted, errored, or redirected.
The only complete trace of those runs lives in
`~/.claude/projects/-Users-ren-IdeaProjects-*ploidy*/**/*.jsonl`, which is local
per-machine state, not version-controlled. "실험 내용이 매번 누락되는" 구조적 문제.

**Decision**: Introduce
[`experiments/src/extract_claude_sessions.py`](../experiments/src/extract_claude_sessions.py),
which walks every `~/.claude/projects/` jsonl, filters to entries with
Ploidy-relevant cwd or experiment-script invocations, and writes compact
per-session JSON summaries to
[`experiments/data/processed/claude_sessions/`](../experiments/data/processed/claude_sessions/)
plus `INDEX.json` and `INDEX.md`. Idempotent — re-run after every session.
First-run coverage (2026-04-20): 10 sessions, 44 experiment runs, 13 MCP calls,
3 errored.

**Why**: Claude Code conversation logs are the ground truth for what actually
ran, but they're large, scattered across multiple project-dir variants
(`-paper-ploidy`, `-Paper-ploidy-experiments`, `-ploidy`, `-paper`,
`-IdeaProjects`), and too raw to browse directly. The extraction turns that
substrate into a queryable research artifact so partial/failed runs stop
silently disappearing. The output fits under `data/processed/` (derived,
regenerable) per the template.

---

## 2026-05-21 -- Pre-registration for the 10-task long-context replication

**Context**: §10.1 of `paper/main.tex` names a minimum requirement for upgrading
the `Ploidy > Single (long-context)` directional advantage to a validated claim:
`≥10 long-context tasks × ≥5 runs × each (model, ploidy, injection) cell`. The
current paper only has 3 long-context tasks (`tasks_longcontext.py`), and the
remaining cell `Ploidy F1 0.595 vs Single F1 0.565` (`p = 0.44`, `n = 5 × 3`)
is the one open hypothesis whose direction has been observed but not statistically
confirmed at the family-corrected significance level. Before scaling that cell
to `n = 5 × 10` we are locking the predictions in writing to prevent HARKing
once the new results land.

**Decision**: Pre-register the following falsification criteria, *binding before
the new experiment runs*. Three independent gates; the hypothesis is supported
only if all three are met.

1. **Effect-size gate (H2 — Context Asymmetry Threshold)**:
   `Ploidy mean F1 − Single mean F1 ≥ 0.030` on the new 10 long-context tasks,
   measured at `effort=high`, `injection=raw`, `lang=en`, `claude-opus-4-6`.
2. **Standardized-effect gate**: Cohen's d (paired) ≥ 0.30 over the same cell.
3. **Significance gate**: Holm–Bonferroni family-corrected `p_corr < 0.05` on the
   paired Wilcoxon signed-rank test (`scripts: experiments/src/analyze_stats.py`).

**Falsification**: any single gate failing means H2 (in its current form) is
*not supported* by this experiment. The paper must report the failure as such
— not be revised to a weaker hypothesis that the data happens to support.

**Capability threshold (H3) is not re-tested here**: cross-model validation is
already in the paper at smaller `n`. Future work scales it.

**External-source gate (anti-circularity)**: of the 10 long-context tasks, at
least 2 must come from `experiments/src/tasks_external.py` (sourced from public
GitHub architecture-decision RFCs or stale issues — not author-designed). This
addresses the circular-task-design risk in `paper/main.tex` §sec:limitations.

**Secondary-judge gate (Cohen's κ)**: a 5-task subset of the same run is
re-evaluated by a second judge model (Gemini 3.1 Pro or GPT-5.4 — chosen at
script-invocation time, not at result-inspection time) via
`experiments/src/run_secondary_judge.py`. Cohen's κ on the per-issue
`{FOUND, PARTIAL, MISSED}` verdicts must be reported. κ < 0.40 means the
primary judge measurement is too noisy to support the H2 verdict regardless
of the three gates above — in which case the experiment is reported as
*judge-invalid* and the result is held until cross-judge agreement is re-tested.

**Why**: §sec:limitations already concedes three known invalidators —
same-model judge, author-defined ground truth (circular task design), and
unverified Cohen's κ. Running another 150-call sweep against the same
three weaknesses would just generate more entries in the same uncorrected
cell. Locking the cutoffs and the external-source / secondary-judge gates
*before* the run is what turns the 4th sweep into evidence rather than
another underpowered observation.

