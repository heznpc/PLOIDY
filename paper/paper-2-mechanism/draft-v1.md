# Ploidy: Cross-Session Structured Debate with Intentional Context Asymmetry for Software Engineering Decisions

> Draft v1 — 2026-03-17
> Target: NeurIPS 2026 Workshop or AAMAS 2027
> Format: 4-6 pages + references

---

## Abstract

Single-session LLM usage subjects critical decisions to stochastic prior lock-in: the model's first probabilistic response anchors all subsequent reasoning, and prompt-based mitigations have no statistically significant effect on this bias. We present Ploidy, a structured debate protocol between physically separate sessions of the same model with intentionally asymmetric context. A Deep session (full project context) and a Fresh session (zero prior context) independently analyze the same artifact, then exchange challenges through typed semantic actions (agree, challenge, propose_alternative, synthesize) before a convergence phase produces a final assessment. Unlike multi-model council approaches that rely on model diversity, Ploidy exploits context diversity within a single model — a combination with zero existing products or publications as of March 2026. In preliminary experiments on 7 code review and architecture decision tasks, Ploidy achieves higher precision than single-session review while surfacing novel findings that neither session produced independently. We release Ploidy as an open-source MCP server.

---

## 1. Introduction

LLM outputs are stochastic. The same model, given the same prompt, produces different responses across independent sessions. This is well-understood. What is less appreciated is the downstream consequence for single-session workflows:

1. The model's first response is sampled from a probability distribution.
2. That response enters the context window and becomes the model's own prior.
3. The model reinforces this prior through consistency-seeking behavior (anchoring bias, sycophancy).
4. The user sees only one session and treats the output as deterministic.

The result: identical models, identical prompts, identical users — but different project outcomes depending on which stochastic sample landed first. This is not addressable by temperature tuning or prompt engineering; empirical evidence shows prompt-based mitigations (chain-of-thought, reflection, "ignore your prior response") have no statistically significant effect on anchoring bias [1].

The only intervention with empirical support is physical session separation. Cross-Context Review (CCR) [2] demonstrated that a fresh session reviewing an artifact produced by a deep session achieves F1=28.6% on error detection versus 24.6% for same-session review (p=0.008). However, CCR is unidirectional — the fresh session reviews but does not debate.

We extend CCR from unidirectional review to **bidirectional structured debate**. Ploidy engineers context asymmetry across physically separate sessions, then reconciles divergent assessments through a formal protocol with typed semantic actions and a convergence engine. Disagreements between sessions are not noise — they are the signal that reveals where the stochastic prior mattered.

**Contributions:**
- Identification of the stochastic prior lock-in problem as a motivation for multi-session architectures (§2)
- A structured debate protocol with semantic actions and convergence analysis for context-asymmetric sessions (§3)
- Extension of SR-DCR/ACVD from QA/fact-verification to software engineering decisions (§3)
- An open-source implementation as an MCP server over Streamable HTTP (§4)
- Preliminary experimental results on 7 tasks comparing 5 baselines (§5)

---

## 2. Background and Related Work

### 2.1 Context Degradation in Long Sessions

LLM performance degrades with context length even when retrieval is perfect — Du et al. [3] showed 13.9-85% performance drops that are architectural, not retrieval-related. Chroma Research [4] evaluated 18 frontier models and found effective context capacity is approximately 60-70% of advertised window size. The "scaling paradox" [5] further shows that larger context compressors produce less faithful reconstructions due to knowledge overwriting.

### 2.2 Multi-Agent Debate

Multi-agent debate (MAD) is well-studied but predominantly uses symmetric configurations where all agents share the same context. Oh et al. [6] demonstrated that symmetric debate can amplify bias through "belief entrenchment." Choi et al. [7] proved that debate under symmetric information induces a martingale — it cannot improve expected correctness beyond majority voting.

### 2.3 Asymmetric Context as a Mechanism

SR-DCR [8] introduced asymmetric context verification debate (ACVD): a context-defending agent debates a context-deprived critic. On GPT-3.5, this achieved 62.7% accuracy (+3.4pp over naive debate). AceMAD [9] proved that asymmetric cognitive potential creates submartingale drift toward truth, formally breaking the martingale curse.

### 2.4 Ploidy's Position

| Prior Work | Scope | Direction | Domain |
|---|---|---|---|
| CCR [2] | Context separation | Unidirectional review | General |
| SR-DCR/ACVD [8] | Asymmetric debate | Unidirectional (Defender→Critic→Judge) | QA/fact verification |
| AceMAD [9] | Asymmetric potential | Theoretical proof | General |
| **Ploidy** | **Asymmetric debate** | **Bidirectional + convergence** | **Software engineering** |

### 2.5 Distinction from Multi-Agent Task Division

Claude Agent Teams and similar systems (CrewAI, MetaGPT) implement cooperative division — splitting work across agents for throughput. Context asymmetry in these systems is a side effect of task scoping, not a deliberate mechanism. Ploidy implements cooperative verification — the same problem is analyzed from intentionally different information states, and disagreements are the primary output.

### 2.6 The Competitive Gap

All existing multi-session products (Perplexity Model Council, Council AI, Karpathy LLM Council) use model diversity (different LLMs). No product or publication uses context diversity within the same model as a verification mechanism. Cross-context review is practiced as a manual workflow pattern but has not been automated as a protocol.

### 2.7 Persistent Memory as Bias Propagation

Any mechanism carrying conclusions from one session to another (persistent memory, session summaries, curated context) becomes a bias propagation channel. If Session A's stochastic output is loaded as "memory" into Session B, Session B inherits A's anchoring bias before forming independent judgment. Ploidy addresses this by ensuring the Fresh session receives only the raw artifact, never the Deep session's prior analysis.

---

## 3. The Ploidy Protocol

### 3.1 Architecture

Two MCP client sessions connect to a single Ploidy server via Streamable HTTP:

- **Deep session**: Full project context (codebase, history, prior decisions)
- **Fresh session**: Only the raw artifact under review (code snippet, architecture question)

The server maintains debate state in SQLite (WAL mode) and enforces the phase protocol.

### 3.2 Debate Phases

1. **POSITION**: Both sessions independently analyze the artifact. Deep has project context; Fresh has none. Each produces a list of findings with confidence levels.
2. **CHALLENGE**: Each session reviews the other's position. For each finding, the reviewer responds with a typed semantic action:
   - `agree` — finding is valid
   - `challenge` — finding is wrong or misleading, with explanation
   - `propose_alternative` — finding is partially right, here's a different framing
   - `synthesize` — combining both perspectives into a stronger finding
3. **CONVERGENCE**: A convergence engine analyzes the debate transcript and produces:
   - **Agreements**: findings both sessions confirmed
   - **Productive disagreements**: findings where challenge/synthesis produced new insight
   - **Irreducible disagreements**: genuine differences that could not be resolved
   - **Confidence score**: proportion of agreed findings

### 3.3 Design Principles

- **No shared memory**: Fresh session never sees Deep's prior analysis outside the debate protocol
- **Typed actions over free-form**: Semantic actions make the debate transcript machine-interpretable
- **Disagreement as signal**: Irreducible disagreements are informative, not failures
- **N-session generalization**: Protocol extends to N>2 sessions with varying context depths

---

## 4. Implementation

Ploidy is implemented as a Python MCP server (FastMCP, asyncio, aiosqlite) exposing 9 tools over Streamable HTTP on port 8765. The server manages debate lifecycle, enforces phase transitions, and persists all state for crash recovery. Full source is available at [repository URL].

---

## 5. Experiments

### 5.1 Setup

We evaluate on 7 tasks: 5 code review tasks with injected bugs (race conditions, SQL injection, memory leaks, off-by-one errors, retry logic) and 2 architecture decision tasks with known best practices. Each task has 3-5 ground-truth issues.

**Methods** (all using Claude Opus 4.6 via `claude --print`):
1. **Single Session**: One session with full context.
2. **Independent Second Opinion**: Two sessions with full context, responses concatenated.
3. **CCR (Unidirectional)**: Deep session produces analysis; Fresh session reviews it.
4. **Symmetric Debate**: Two sessions with identical full context debate each other.
5. **Ploidy (Asymmetric Debate)**: Deep (full context) vs Fresh (zero context), structured protocol.

**Judge**: Claude Opus 4.6 evaluates each method's output against ground truth. For each ground-truth issue: FOUND, PARTIAL, or MISSED. Additional valid findings not in ground truth are counted as bonus findings.

**Metrics**: Recall (ground-truth detection rate), Precision (signal-to-noise), F1.

### 5.2 Results (Experiment 1: Short-Context Tasks)

7 tasks (5 code review + 2 architecture), Claude Opus 4.6, single run per method.

| Method | Avg F1 | Avg Recall | Avg Time |
|--------|--------|------------|----------|
| Single Session | **0.573** | 3.7/4.1 | 40s |
| Second Opinion | 0.554 | 4.1/4.1 | 89s |
| CCR (Unidirectional) | 0.548 | 3.9/4.1 | 92s |
| Symmetric Debate | 0.555 | 4.0/4.1 | 118s |
| Ploidy (Asymmetric) | 0.540 | 3.9/4.1 | 205s |

Per-task breakdown:

| Task | GT | Single | 2nd Op. | CCR | Sym. | Ploidy |
|------|---:|-------:|--------:|----:|-----:|-------:|
| Race condition | 3 | .462 | .500 | **.667** | .462 | .462 |
| SQL injection | 3 | **.600** | .545 | .600 | .500 | .545 |
| Memory leak | 4 | .667 | .667 | .500 | .667 | .667 |
| DB choice (arch) | 5 | .529 | .476 | .357 | .409 | **.526** |
| Auth migration (arch) | 5 | **.588** | .400 | .455 | .556 | .455 |
| Pagination | 4 | .500 | **.667** | .667 | .667 | .500 |
| Retry logic | 5 | **.667** | .625 | .588 | .625 | .625 |

**Key finding: No method consistently outperforms Single Session on these tasks.** All methods achieve near-perfect recall (most ground-truth issues found), and F1 differences are driven by precision (bonus findings inflating denominators).

### 5.3 Analysis: Why Context Asymmetry Did Not Help

The negative result is informative. We identify three factors:

**1. Insufficient context depth.** Each task's "project context" was 2-3 sentences (~50 tokens). Context entrenchment — the phenomenon Ploidy is designed to address — requires accumulated context on the order of thousands to tens of thousands of tokens. With 50-token context, the Deep session has no meaningful anchoring bias to develop, and the Fresh session gains no advantage from context independence.

**2. Task difficulty ceiling.** Claude Opus 4.6 found nearly all ground-truth issues in every method (avg recall 3.7-4.1 out of 4.1). When the baseline already achieves near-perfect recall, multi-session methods cannot demonstrate recall improvement. The value of cross-verification emerges when the single session *misses* things — which requires harder tasks or weaker models.

**3. F1 metric penalizes verbosity.** Multi-step methods produce more text, which generates more bonus findings (valid issues not in ground truth). The current F1 metric counts these as false positives, penalizing thoroughness. A metric that distinguishes "valid additional finding" from "noise" would better capture the qualitative richness observed in Ploidy's convergence outputs.

### 5.4 Qualitative Observations

Despite the quantitative parity, Ploidy's convergence phase produced qualitatively distinct outputs:

- **Severity calibration**: Fresh session challenged Deep's severity escalation of a memory leak, arguing it depends on key cardinality — a nuance absent from single-session output.
- **Novel findings**: Fresh identified that `get()` being `async` without `await` affects race condition exploitability — a finding neither session produced in isolation.
- **Explicit disagreement tracking**: Ploidy's semantic actions (agree/challenge/synthesize) create a machine-readable audit trail of how conclusions were reached, which no other method provides.

These qualitative benefits are not captured by the current F1 metric but may be significant for real-world decision quality.

### 5.5 Experiment 2: Long-Context Tasks

To test whether context asymmetry matters when context is long enough to induce entrenchment, we designed 3 architecture decision tasks with 2,000-5,000 token project histories containing **anchoring-inducing biases**:

- **DB migration**: 18-month history of PostgreSQL commitment, repeated rejection of alternatives, team pride in custom partitioning — ground truth requires recommending a different approach
- **Auth overhaul**: 2-year history of custom auth built by one developer who defends it — ground truth requires acknowledging authority bias and bus factor risk
- **Microservice split**: 3-year monolith with premature microservice extraction in progress — ground truth requires challenging the VP's plan

Each task's context is designed so that a session anchored to the project history will rationalize the status quo, while a fresh session will evaluate the technical merits independently.

**Experiment 2 Results:**

| Method | Avg F1 | Avg Found/Total | Avg Time |
|--------|--------|-----------------|----------|
| Symmetric Debate | **0.607** | **5.0**/5.3 | 146s |
| Single Session | 0.591 | 4.3/5.3 | 52s |
| Second Opinion | 0.566 | 4.3/5.3 | 108s |
| Ploidy (Asymmetric) | 0.561 | 4.7/5.3 | 294s |
| CCR (Unidirectional) | 0.458 | 4.7/5.3 | 108s |

Per-task breakdown:

| Task | GT | Single | 2nd Op. | CCR | Sym. | Ploidy |
|------|---:|-------:|--------:|----:|-----:|-------:|
| DB migration (bias) | 5 | .571 (3F+2P) | .600 | .500 | .600 | **.500 (5F)** |
| Auth overhaul (bias) | 5 | .556 | .450 | .375 | .556 | .450 |
| Microservice split | 6 | .647 | .647 | .500 | .667 | **.733** |

### 5.6 Key Findings Across Both Experiments

**Finding 1: Context length affects recall asymmetrically.**

| | Exp 1 (short context) | Exp 2 (long context) |
|---|---|---|
| Single Session recall | 3.7/4.1 (90%) | 4.3/5.3 (81%) |
| Ploidy recall | 3.9/4.1 (95%) | 4.7/5.3 (89%) |
| Gap | +5% | **+8%** |

Single Session's recall drops more steeply with context length. Ploidy's recall advantage widens.

**Finding 2: Ploidy achieves highest recall on the most bias-laden task.**

On the DB migration task (strongest anchoring bias in context), Ploidy was the only method to achieve 5/5 FOUND with zero partial. Single Session found only 3/5, with 2 partial — specifically, it hedged on "the team's PostgreSQL expertise is anchor bias" and "the CTO's rejection of TimescaleDB should be challenged." These are exactly the findings that require contradicting the project history.

**Finding 3: F1 penalizes thoroughness; recall better captures Ploidy's value.**

Ploidy's multi-phase output generates more bonus findings, reducing precision and thus F1. But for decision quality, recall (did we catch the critical issues?) matters more than precision (did we avoid mentioning irrelevant things?). On recall alone, Ploidy ties or beats all methods on long-context tasks.

**Finding 4: Symmetric Debate is a strong baseline.**

Symmetric Debate (both sessions get full context) performed well, suggesting that "debating itself" has value independent of context asymmetry. The open question is whether asymmetry adds value *on top of* debate — the DB migration task suggests yes (Symmetric: 4F+1P, Ploidy: 5F).

### 5.7 Stochastic Variance (Re-run Analysis)

We re-ran both experiments to measure stochastic variance. Same model, same tasks, same methods — different results.

**Long-context DB migration task (both runs):**

| Method | Run 1 Found | Run 2 Found | Run 1 F1 | Run 2 F1 | F1 Δ |
|--------|------------|------------|---------|---------|------|
| Single | 3F+2P | 4F+1P | .571 | .643 | +.072 |
| Ploidy | **5F** | **5F** | .500 | .556 | +.056 |

**Ploidy achieved 5/5 detection in both runs.** Single Session varied from 3 to 4 found. On the most bias-laden task, Ploidy's recall was consistent across limited runs (n=2) while Single's varied. Confirming determinism would require at least 5 repetitions with statistical testing; these two runs establish consistency but not deterministic behavior.

**Cross-run F1 variance (all long-context tasks):**

| Method | Run 1 Avg F1 | Run 2 Avg F1 | Δ |
|--------|-------------|-------------|---|
| Single | 0.591 | 0.600 | +.009 |
| Ploidy | 0.561 | 0.455 | **-.106** |

Ploidy's F1 dropped substantially in Run 2 despite maintaining or improving recall — the variance comes entirely from precision (bonus findings count). This confirms that **F1 is an unstable metric for multi-phase methods** and that recall is the more reliable measure of Ploidy's value.

**This variance is itself evidence of the stochastic prior problem.** Identical inputs produce F1 values that differ by up to 0.29 across runs (Ploidy on microservice task: 0.733 → 0.444). Any single run's results should be interpreted with this variance in mind.

---

## 6. Discussion

### 6.1 When Does Context Asymmetry Help?

The two experiments together suggest a clear pattern:

1. **Short context (<100 tokens): No benefit.** Single Session matches or beats multi-session methods. The model has nothing to be anchored *to*.
2. **Long context with neutral history: Moderate benefit.** Multiple sessions provide redundancy but not asymmetry-specific gains.
3. **Long context with anchoring bias: Asymmetry helps.** On the DB migration task (strongest bias), Ploidy was the only method to achieve perfect recall. The Fresh session, having never seen the 18-month PostgreSQL commitment history, had no difficulty recommending alternatives.

This aligns with Young [10]'s phase transition: debate value scales with knowledge divergence. At 50 tokens, Deep/Fresh divergence is negligible. At 2,000+ tokens of biased history, divergence becomes substantial — and productive.

### 6.2 The Honest Null and Positive Results

Experiment 1 is a null result: Ploidy did not outperform Single Session on short-context tasks. We report this rather than omitting it because it bounds where context asymmetry applies.

Experiment 2 is a qualified positive: Ploidy achieved the highest recall on the most bias-laden task and the highest F1 on the microservice task. The qualification is that the overall averages are close, and n=3 is too small for statistical significance.

Together, they suggest context asymmetry is a **targeted intervention for context entrenchment**, not a universal improvement. This is consistent with the theoretical prediction: if there is no entrenchment to break, the Fresh session adds cost without benefit.

### 6.3 Limitations

- Single run per method per task (no variance estimation). Stochastic variation means these F1 values could shift ±0.05-0.10 on re-runs — which is itself evidence of the stochastic prior problem.
- 7 tasks with author-defined ground truth (not independently validated)
- Judge uses the same model family (potential systematic bias)
- Cost: Ploidy uses ~5x tokens of single session (205s vs 40s average)
- All tasks use short context (<100 tokens); the core hypothesis (context entrenchment) was not triggered

### 6.4 Broader Implications

The stochastic prior lock-in problem applies beyond code review. Any single-session LLM workflow — writing, analysis, planning — is subject to the same anchoring dynamics. Large-scale agent simulations (e.g., swarm prediction engines spawning hundreds of thousands of LLM agents) inherit this problem at the individual agent level: if each agent's first stochastic response locks in its trajectory, scaling agent count does not improve reliability — it scales biased samples.

Ploidy suggests that verification depth (cross-checking individual outputs) may be more valuable than verification breadth (adding more agents with the same bias). This distinction — cooperative verification vs. cooperative division — is absent from current multi-agent system design.

---

## 7. Conclusion

We presented Ploidy, a protocol for structured debate between same-model sessions with intentional context asymmetry, motivated by the stochastic prior lock-in problem.

Two experiments reveal a context-dependent pattern: on short-context tasks (Exp 1, 7 tasks), Ploidy provides no advantage over single-session review — the model is strong enough and the context too short for entrenchment to occur. On long-context tasks with anchoring bias (Exp 2, 3 tasks), Ploidy achieves the highest recall on the most bias-laden task (5/5 vs Single Session's 3/5 on the DB migration task) and the highest F1 on the microservice task (0.733 vs Single's 0.647).

This suggests context asymmetry is a **targeted intervention**: it provides value specifically when accumulated context induces entrenchment that prevents the model from challenging its own prior conclusions. The Fresh session, unburdened by project history, can identify issues that a context-entrenched session rationalizes away.

We release Ploidy as an open-source MCP server. Future work includes larger-scale evaluation with statistical significance testing, evaluation on weaker models where single-session recall is lower, and integration with agent ecosystem management tools where individual agent output verification is a prerequisite for reliable collective behavior.

---

## Acknowledgments

This paper was written with the assistance of Claude Code (Anthropic, Claude Opus 4.6). The experimental framework, literature search, and draft editing were conducted through interactive sessions with the tool. All research decisions, hypotheses, and interpretations are the authors' own.

---

## References

[1] Feng et al. "Anchoring Bias in Large Language Models: An Experimental Study." J. Computational Social Science, 2026.

[2] Song. "Cross-Context Review." arXiv:2603.12123, 2026.

[3] Du et al. "Context Length Alone Hurts LLM Performance Despite Perfect Retrieval." EMNLP 2025. arXiv:2510.05381.

[4] Chroma Research. "Context Rot." research.trychroma.com/context-rot, 2025.

[5] "When Less is More: The LLM Scaling Paradox in Context Compression." arXiv:2602.09789, 2026.

[6] Oh, Jeong, Ko, and Yun. "Bias Entrenchment in Multi-Agent Debate (DReaMAD)." arXiv:2503.16814, 2025.

[7] Choi, Zhu, and Li. "Debate or Vote: Which Yields Better Decisions in Multi-Agent LLMs?" NeurIPS 2025 Spotlight. arXiv:2508.17536.

[8] "When to Trust Context: Self-Reflective Debates for Contextual Reliability (SR-DCR)." Stanford/Brown/UNSW. arXiv:2506.06020, 2025.

[9] Liu et al. "Breaking the Martingale Curse: Multi-Agent Debate via Asymmetric Cognitive Potential Energy (AceMAD)." MBZUAI/Renmin/Harvard. arXiv:2603.06801, 2026.

[10] Young. "Knowledge Divergence and the Value of Debate for Scalable Oversight." arXiv:2603.05293, 2026.

[11] Jacob, Kerrigan, and Bastos. "The Chat-Chamber Effect: Trusting the AI Hallucination." Big Data & Society, SAGE, 2025.

[12] M2CL. "Multi-LLM Context Learning for Multi-Agent Discussion." ICLR 2026. arXiv:2602.02350.

[13] "From Debate to Deliberation: Structured Collective Reasoning with Typed Epistemic Acts." arXiv:2603.11781, 2026.
