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
   measured at `effort=high`, `injection=raw`, `lang=en`, `claude-opus-4-7`.
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

---

## 2026-05-21 -- Pre-registration amendment (post-Major-review)

**Context**: After the Critical fixes landed (PR #50), a same-session
Major review surfaced four further gaps. The user selected `fix → 실험`
on all four. This amendment is appended *before* the new sweep runs.

**Decisions**:

1. **External-source ratio raised to 3/10 (30 %)** — `tasks_external.py`
   now ships 3 task variants (`ext_gitlab_2017_db_posture`,
   `ext_github_2018_mysql_topology`, `ext_knight_2012_smars_deploy`),
   each anchored to a public post-mortem or SEC filing. The original
   pre-registration's "≥2 of 10" gate is upgraded to "≥3 of 10".

2. **Context-length gradient added** — `experiments/src/tasks_gradient.py`
   expands the 10 base tasks into 30 variants at three length tiers
   (`short ≈ 500 tokens`, `medium ≈ 1000 tokens`, `long = full`). The
   replication runs all 30 variants × n=5 × {Single, Ploidy, CCR} =
   450 runs. The gradient is what lets H2's "entrenchment threshold"
   move from a qualitative claim ("regime") to a numeric cutoff
   (the smallest tier at which Δ̄F1 ≥ 0.030 reproduces).

3. **Falsification gates reported per length tier** — the
   `Δ̄F1 ≥ 0.030 / d ≥ 0.30 / p_corr < 0.05` triple is evaluated on
   each tier independently. Reporting form: "H2 supported at
   long tier / not supported at medium tier / not supported at short
   tier" — the threshold *is* the result.

4. **Paper body reflects the gates** — abstract, §1 Introduction
   Contributions list, §sec:aggregate-stats honest-summary
   paragraph, and §sec:threshold all carry the cutoff triple
   verbatim so the paper cannot be revised post-hoc to a weaker
   hypothesis (the cross-reference would be visible in the diff).

5. **Raw artefact publication path** —
   `experiments/data/processed/claude_sessions/INDEX.{json,md}` is
   already tracked. The 4th-sweep `experiments/results/<timestamp>/`
   tree is bundled into the Zenodo deposit alongside the
   `v0.3.4-paper` git tag for reviewer end-to-end verification.

**Why**: Critical fixes addressed measurement invalidity. These four
Major decisions close the externally-visible drift between (a) what
the paper claims about H2 and (b) what the data can actually support
under family-corrected significance. Combined with the Critical
secondary-judge κ gate, this means a reviewer reading the abstract,
the contributions list, the aggregate-stats summary, and the
threshold section will see the same falsifiable triple in every
location.

---

## 2026-05-21 -- Model-version drift discovered (and fixed)

**Context**: Mid-amendment, the user pointed out that the 4th-sweep
target model should be Claude Opus 4.7, not 4.6 as the pre-registration
had been written. Cross-checking the per-cell result JSONs revealed
the actual experimental subject already transitioned on **2026-04-23**:
~420 entries from 2026-03-18 through 2026-04-17 are on `claude-opus-4-6`,
and 59 entries from 2026-04-23 onward are on `claude-opus-4-7`. The
runner default (`MODEL = "claude-opus-4-6"` in `run_experiment.py:49`)
plus paper §sec:experiments text were therefore lagging the actual
experimental state by ~28 days. The smoke run kicked off earlier today
inherited the stale default and produced 4.6 results, polluting the
nominally-4.7 4th-sweep tree.

**Decision**:

1. **Runner default** flipped to `claude-opus-4-7` at three sites in
   `experiments/src/run_experiment.py` (line 49 `MODEL`, line 50
   `JUDGE_MODEL`, line 269 `BACKEND_DEFAULTS["claude"]`) plus the
   negation comparison at line 2362.
2. **Pre-registration falsification triple** (above amendment, gate~1)
   updated `claude-opus-4-6` → `claude-opus-4-7`.
3. **Paper** picks up a new "Model transition mid-program" paragraph
   in §sec:experiments that explicitly attributes 1,601 of the 1,660
   aggregate entries to 4.6 and 59 to 4.7, removes the abstract claim
   that the 4th-sweep runs on 4.6, and adds the 2026-04-23 transition
   date to the acknowledgement section.
4. **Partial smoke results** from the killed run (a single dir under
   `experiments/src/results/20260521_030404_*` containing two 4.6
   cells) were removed before they could pollute any future analysis.
5. **Per-experiment cells** in the existing paper (§sec:exp1, §sec:exp2,
   §sec:cross-model, §sec:effort-sweep) retain their factually-correct
   4.6 model attribution — those sweeps really did run on 4.6 and the
   per-table model label is the truthful record.

**Why**: This is a *self-evidencing* mistake — the pre-experiment
review missed a paper↔runner↔result drift that the actual data file
metadata had been broadcasting for four weeks. The new pre-reg locks
4.7 and the paper now records the transition openly so the same
mistake cannot survive another review pass. This particular drift
(model version inferred from default constants rather than read from
result files) is added to §sec:implications as a sixth intra-session
anchoring case in a follow-up paper edit (not in this commit).

