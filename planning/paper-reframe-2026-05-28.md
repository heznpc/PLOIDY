# Paper Reframe — 4th-Sweep H2 Falsification Result

**Date**: 2026-05-28 11:00 KST
**Trigger**: Pre-registered 4th-sweep replication (n=5 × 10 long-tier tasks × 3 methods × 3 tiers = 450 cells) completed.
**Verdict**: **H2 NOT SUPPORTED on any tier (short / medium / long). Effect direction INVERTED from the earlier 1,601-entry aggregate.**

---

## 1. The numerical inversion (the central finding)

| Aspect | Pre-4th-sweep paper claim (N=95) | 4th-sweep replication (N=150 per method) |
|---|---|---|
| Headline | Ploidy > CCR on F1 | Ploidy **<** CCR on F1 |
| ΔF1 (Ploidy − CCR) | **+0.054** | **−0.054** |
| Cohen's d | +0.53 (medium) | **−0.50** (medium) |
| p_corr | 0.0013 | **< 0.0001** |
| N pairs | 95 | 150 |
| Direction | H1 supported | **H1 rejected** |

The replication did not merely fail to reproduce — it produced the *exact opposite* effect at the same magnitude with 1.6× the sample size. The earlier finding was a real measurement; under cleaner conditions it inverts. This is the paper's central honest finding.

## 2. Why the earlier finding was an artifact (post-hoc, not pre-registered)

The 4th-sweep applied four corrections that the pre-4th-sweep N=95 data lacked:

1. **Model version**: opus-4-6 → opus-4-7 (April 2026 upgrade; opus-4-7 has expanded 1M-token context window, plausibly reducing the "entrenchment regime" that motivated H2)
2. **Memory contamination fix (PR #57)**: `tempfile.mkdtemp` cwd-neutral subprocess so the runner does not auto-load `~/.claude/projects/<encoded-cwd>/memory/*.md` fabrication casebook into each Fresh seat. Before this fix, Fresh seats were partially contaminated with the user's own prior refusal-case memory — they were not actually "fresh."
3. **Quota classifier (PR #68/#69/#70)**: stopped misclassifying model refusals and ordinary review text ("the rate limit resets every 60s") as 5h quota exhaustion, which had silently dropped cells during older sweeps.
4. **CLI banner detection (PR #69)**: stopped flagging valid review outputs containing `"resets"` / `"hit your limit"` as quota errors.

These four corrections compound. The original +0.054 was measured on a data state that no longer exists; the cleaner replication is the correct one.

## 3. Tier-stratified result (the H2 falsification gate itself)

Per pre-registration (planning/decisions.md, 2026-05-21 + 2026-05-27 amendments), H2 required:
- ΔF1 (or recall) ≥ 0.030
- Cohen's d ≥ 0.30
- Holm-Bonferroni p_corr < 0.05
- Cohen's κ ≥ 0.40 secondary judge gate
- ≥30% external-source tasks
- Co-primary metrics: F1 + recall (F1\* supplementary)

| Tier | Single F1 | CCR F1 | **Ploidy F1** | ΔF1 (P−C) | d | p (one-sided) | Verdict |
|---|---|---|---|---|---|---|---|
| short (~500 tok) | 0.502 | 0.483 | **0.432** | −0.051 | −0.52 | 0.9996 | **H2 not supported** |
| medium (~1000 tok) | 0.563 | 0.532 | **0.476** | −0.056 | −0.52 | 1.0000 | **H2 not supported** |
| **long (full)** | 0.534 | **0.542** | **0.488** | **−0.054** | **−0.58** | **0.9998** | **H2 not supported** |

The context-length-gradient prediction (H2 supported at long, fails at short/medium) is also falsified: the effect direction is *uniform* across all three tiers. There is no entrenchment-threshold tier at which Ploidy emerges.

## 4. Cost-accuracy verdict

| Method | F1 | Tokens / cell | Wall / cell | F1 per kToken |
|---|---|---|---|---|
| **single** | **0.533** | 6,223 | 75s | 0.0857 |
| ccr | 0.519 | 12,123 | 171s | 0.0428 |
| ploidy | 0.465 | **31,937** | **260s** | **0.0146** (worst) |

Ploidy is the worst of the three on F1 and uses 5× more tokens than Single, 2.6× more than CCR, and 3.4× more wall time than Single. In raw-injection mode, the framework provides no advantage on any axis the pre-registration cared about.

## 5. What remains intact

The 4th-sweep falsifies the H2 *prediction* (Ploidy > CCR on long-context tasks). It does not falsify the paper's *contributions*, which were always conceptual:

1. **The Event A / Event B distinction** is still a valid analytical decomposition; the 4th-sweep just shows that at 1n in raw injection mode, Event A's contribution is null-or-negative rather than positive.
2. **The Context Asymmetry Spectrum and injection-mode taxonomy** remain the experimental design space; the paper's contribution is the framework that lets this hypothesis be tested at all, regardless of the verdict.
3. **The pre-registration discipline** itself — committing to a falsification triple before running, then reporting the verdict honestly — is a methodological contribution distinct from the empirical finding. Many MAD papers do not pre-register; the explicit Δ ≥ 0.030 + d ≥ 0.30 + p_corr < 0.05 + κ ≥ 0.40 + external-source 30% + tier-gradient gate set is reusable scaffolding.
4. **Falsification result as evidence**: the inversion (+0.054 → −0.054 with cleaner data) is itself an interesting result. It suggests context-asymmetric debate at 1n is not a free win even on long-context tasks, and that earlier MAD findings claiming asymmetric debate benefits should be re-evaluated under similar memory-contamination and model-version controls.

## 6. Open questions the 4th-sweep does NOT answer

- **Does 2n+ help?** The Event A / Event B separation requires 2n+. The 4th-sweep is 1n only. The hypothesis that ploidy level itself (more sessions per depth, separating within-group from between-group variance) overcomes the 1n null remains testable.
- **Does stronger asymmetry help?** The injection-mode sweep (inj-memory, inj-skills) on the *older* opus-4-6 data showed Ploidy +0.064 over CCR with inj-memory, but those runs predate all four corrections in §2 and cannot be directly compared. A clean inj-memory sweep with current code (opus-4-7 + fixes) is the next testable hypothesis.
- **Cross-model**: opus-4-7 may be a particularly bad model family for context-asymmetric debate because its expanded context window reduces the entrenchment regime H2 was designed for. Sonnet, Gemini, GPT-5.4 may show different patterns.
- **Effort/lang interactions**: not addressed by the 4th-sweep, which fixed effort=high lang=en.

## 7. Concrete paper edits required

### 7a. Abstract / §1 Introduction headline (lines ~64-76)

**Replace** finding (2) and (3) and (5) with:

> **(2) Pre-registered 4th-sweep replication inverts the original Ploidy > CCR finding.** Under cleaner conditions (opus-4-7, memory-contamination fix, tightened quota classifier, 5× sample size at N=150 per method), Ploidy is significantly *worse* than CCR at d = −0.50 (p_corr < 0.0001), with the same magnitude (|ΔF1| = 0.054) as the original effect but in the opposite direction. The inversion is uniform across short / medium / long context tiers; the predicted entrenchment threshold does not appear.
>
> **(3) Ploidy is the most expensive method on every axis.** 5× more tokens than Single, 2.6× more than CCR, 3.4× more wall time. Combined with the F1 inversion, raw-injection 1n Ploidy is Pareto-dominated by CCR and Single.
>
> **(5) The paper's value is now methodological rather than empirical.** The pre-registration falsification triple + secondary-judge κ gate + tier-gradient gate + external-source quota are the reusable contribution; the original hypothesis itself is rejected by the cleaner data.

### 7b. New subsection: `\subsection{Experiment 7: 4th-Sweep H2 Falsification Replication}`

Insert after §sec:effort-sweep (Experiment 6). Body: §1-§5 above, condensed to ~2 pages with the tier-stratified table and the cost-accuracy table.

### 7c. §sec:threshold rewrite

Currently the §Context Asymmetry Threshold Hypothesis section presents H2 as predicted-but-not-yet-tested. Rewrite as:

> The hypothesis was pre-registered with explicit falsification criteria (Δ ≥ 0.030, d ≥ 0.30, p_corr < 0.05, κ ≥ 0.40, ≥30% external-source, tier-gradient) before any 4th-sweep data was collected. The replication failed all three primary gates on all three tiers. We report this as falsification rather than reframing against a weaker hypothesis (per the pre-registration's anti-reframing clause).

### 7d. §sec:conclusion update

Add an explicit subsection `\subsection{What we got wrong}` documenting:
- The original +0.054 effect was real on the data state it was measured on
- The data state itself had four confounders (model, memory, quota, banner)
- The inversion to −0.054 under cleaner conditions is the paper's central honest finding
- The framework remains a useful experimental design space even when the headline prediction fails

### 7e. Remove or qualify all "Ploidy > CCR" claims throughout

Search-replace targets:
- Line 68 "Ploidy outperforms unidirectional Cross-Context Review~\citep{song2026ccr} on F1 ($\Delta = +0.054$, $d = 0.53$, $p_\text{corr} = 0.0013$, $N = 95$)" — qualify with "in the pre-4th-sweep N=95 measurement; inverted to ΔF1 = −0.054, d = −0.50, p_corr < 0.0001 at N = 150 under the 4th-sweep replication conditions."
- Line 855 "Ploidy reliably beats lower-cost LLM-only ensembles (Tool+LLM Parallel) and unidirectional review (CCR) on F1 with no confounders" — replace "CCR" with "Tool+LLM Parallel" only; note CCR claim was inverted by 4th-sweep.

## 8. Honest re-statement of contribution

The paper's contribution after the inversion is best stated as:

> Ploidy formalizes intentional context-asymmetric debate as a multi-axis experimental design space (Spectrum × Injection × Ploidy Level × Effort × Language × Model) and pre-registers a falsification protocol for the headline 1n raw-injection prediction. The pre-registered replication falsifies the prediction in the opposite direction at medium effect size under cleaner experimental conditions (model upgrade, memory-contamination fix, tightened quota detection). The honest negative result, combined with the design-space framework and the reusable pre-registration discipline, is more publishable than a marginal positive on confounded data.

The framework is intact. The headline empirical prediction is rejected. Both can be true.

---

## 9. Sequencing for next 24h

1. **κ gate (in flight)** — if κ < 0.40 the verdict is "judge-invalid" not "H2 rejected"; need to wait
2. **Paper edits 7a, 7b, 7c, 7d** — draft directly into main.tex once κ gate returns valid
3. **planning/decisions.md** — append 4th-sweep replication entry with the inversion verdict
4. **README.md status badge** — update from "pending" to "replicated, H2 rejected"
5. **Zenodo + arXiv preparation** — bundle the 4th-sweep raw results into the next release

Decisions still needed from user before drafting 7a-7d into the .tex:
- Confirm the "honest negative" framing is the preferred direction (vs. e.g. reframing as "context-asymmetry-conditional hypothesis" which requires the inj-memory re-run to validate)
- Decide whether to defer paper submission until the inj-memory/skills re-run is done (would validate the conditional-asymmetry hypothesis) or submit the negative result now (faster, sharper)
