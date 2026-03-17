# Ploidy: Context-Asymmetric Structured Debate for LLM Decision Verification

> Draft v2 — 2026-03-17
> Target: NeurIPS 2026 Workshop or AAMAS 2027
> Format: 4-6 pages + references
> Changes from v1: Abstract corrected, Semi-Fresh introduced, Context Asymmetry Spectrum, context delivery mode, model collapse connection, limitations expanded, reviewer feedback addressed

---

## Abstract

Single-session LLM usage subjects critical decisions to stochastic prior lock-in: the model's first probabilistic response anchors all subsequent reasoning, and prompt-based mitigations have no statistically significant effect on this bias [1]. We present Ploidy, a structured debate protocol between physically separate sessions of the same model with intentionally asymmetric context depths. Unlike multi-model council approaches that rely on model diversity, Ploidy exploits **context diversity** within a single model — a dimension absent from existing products and publications as of March 2026. We introduce the **Context Asymmetry Spectrum**, which varies along two dimensions: context depth (how much prior knowledge a session receives) and context delivery mode (whether context is passively embedded or actively retrievable). Sessions range from Deep (full context, always present) through Semi-Fresh (compressed context, passively or actively delivered) to Fresh (zero context), debating through typed semantic actions before a convergence phase. In preliminary pilot experiments on 10 tasks across two context regimes, we observe that (1) context asymmetry provides no benefit on short-context tasks where entrenchment does not occur, and (2) on long-context tasks with anchoring bias, asymmetric debate achieves the highest ground-truth recall on the most bias-laden task (5/5 vs. Single Session's 3/5, stable across re-runs). These results bound where context asymmetry applies and motivate the Semi-Fresh hypothesis: that an optimal intermediate point exists in the depth × delivery space. We release Ploidy as an open-source MCP server.

---

## 1. Introduction

LLM outputs are stochastic. The same model, given the same prompt, produces different responses across independent sessions. This is well-understood. What is less appreciated is the downstream consequence for single-session workflows:

1. The model's first response is sampled from a probability distribution.
2. That response enters the context window and becomes the model's own prior.
3. The model reinforces this prior through consistency-seeking behavior (anchoring bias, sycophancy).
4. The user sees only one session and treats the output as deterministic.

The result: identical models, identical prompts, identical users — but different project outcomes depending on which stochastic sample landed first. This is not addressable by temperature tuning or prompt engineering; empirical evidence shows prompt-based mitigations (chain-of-thought, reflection, "ignore your prior response") have no statistically significant effect on anchoring bias [1].

This phenomenon has a well-documented human analog. Kuhn [14] observed that scientific paradigm shifts occur not because existing practitioners change their minds, but because a new generation — unburdened by accumulated commitments — evaluates the evidence independently. Planck stated this more bluntly: "science advances one funeral at a time," a claim empirically confirmed by Azoulay et al. [15], who showed that the death of eminent scientists leads to a statistically significant influx of new researchers and ideas into their fields. In both cases, accumulated context (experience, expertise, institutional memory) simultaneously enables domain mastery and prevents paradigm revision.

The parallel extends beyond scientists. If we map **context to lifespan** — treating accumulated knowledge as a growing context window and cognitive capacity as a fixed model — then all of human civilization operates under the same dynamic. Every individual is an instance of the same model (homo sapiens) with roughly equivalent architecture (intelligence), differing only in session (environment, era, culture). Each person begins with a fresh context, stochastically accumulates a unique trajectory of beliefs and expertise, and becomes progressively anchored to that trajectory. Innovation and paradigm shifts occur not because individuals overcome their accumulated priors — Kuhn and Azoulay's evidence suggests they largely do not — but because new individuals (fresh contexts) evaluate the same evidence without the anchoring of prior commitment. Human civilization's capacity for renewal depends structurally on this generational context asymmetry: the continuous introduction of sessions that do not inherit the entrenched context of their predecessors.

This framing makes the LLM single-session problem precise: a user who works within one session is a civilization of one, with no generational turnover — no fresh context to challenge the stochastic prior that anchored the session's first response.

The only computational intervention with empirical support for this problem is physical session separation. Cross-Context Review (CCR) [2] demonstrated that a fresh session reviewing an artifact produced by a deep session achieves F1=28.6% on error detection versus 24.6% for same-session review (p=0.008). However, CCR is unidirectional — the fresh session reviews but does not debate.

We extend CCR from unidirectional review to **bidirectional structured debate** and introduce the **Context Asymmetry Spectrum** — a continuum from full context (Deep) through compressed context (Semi-Fresh) to zero context (Fresh). This spectrum recognizes that the optimal information state for a challenger may be neither complete ignorance nor full knowledge, but an intermediate point analogous to the "experienced outsider" who brings domain awareness without institutional entrenchment.

**Contributions:**
- The Context Asymmetry Spectrum: a framework for reasoning about optimal context depth in multi-session verification (§3)
- A structured debate protocol with typed semantic actions and convergence analysis (§3)
- Preliminary pilot experiments (10 tasks, two context regimes) with honest null and qualified positive results (§5)
- Analysis of when context asymmetry helps and when it does not, bounding the intervention's applicability (§6)
- An open-source MCP server implementation (§4)

---

## 2. Background and Related Work

### 2.1 Context Degradation in Long Sessions

LLM performance degrades with context length even when retrieval is perfect — Du et al. [3] showed 13.9–85% performance drops that are architectural, not retrieval-related. Chroma Research [4] evaluated 18 frontier models and found effective context capacity is approximately 60–70% of advertised window size. The "scaling paradox" [5] further shows that larger context compressors produce less faithful reconstructions due to knowledge overwriting.

### 2.2 Multi-Agent Debate

Multi-agent debate (MAD) is well-studied but predominantly uses symmetric configurations where all agents share the same context. Oh et al. [6] demonstrated that symmetric debate can amplify bias through "belief entrenchment." Choi et al. [7] proved that debate under symmetric information induces a martingale — it cannot improve expected correctness beyond majority voting. This result has implications beyond LLMs: any system where agents share identical priors and debate cannot, in expectation, improve upon aggregating their independent judgments.

### 2.3 Asymmetric Context as a Mechanism

SR-DCR [8] introduced asymmetric context verification debate (ACVD): a context-defending agent debates a context-deprived critic. On GPT-3.5, this achieved 62.7% accuracy (+3.4pp over naive debate). AceMAD [9] proved that asymmetric cognitive potential creates submartingale drift toward truth, formally breaking the martingale curse. We note that Ploidy's current single-round design does not satisfy the multi-round conditions required for AceMAD's submartingale proof; whether a multi-round extension would achieve this remains an open question (§7).

### 2.4 Scaling Agents vs. Scaling Diversity

Large-scale agent simulations (e.g., AgentSociety [16] with 10K agents, MiroFish with 700K agents) pursue verification breadth — more agents analyzing the same problem. Boca et al. [17] showed that even without individual-level bias, LLM populations spontaneously develop collective biases through interaction. Combined with Choi et al.'s martingale result [7], this suggests that scaling homogeneous agent count does not reliably improve decision quality. Ploidy pursues the orthogonal dimension: verification depth through context diversity.

### 2.5 Model Collapse and Context Contamination

When AI-generated content enters training data, progressive quality degradation occurs across model generations — termed "model collapse" [18]. This represents the failure mode when context asymmetry disappears entirely: each new model generation inherits and amplifies the biases of the previous generation, with no "fresh perspective" to challenge accumulated priors. Ploidy's design principle — deliberately maintaining sessions with different context depths — can be understood as a countermeasure to this homogenization tendency.

### 2.6 Ploidy's Position

| Prior Work | Mechanism | Context Depth | Delivery Mode | Direction |
|---|---|---|---|---|
| CCR [2] | Session separation | Binary (Deep/Fresh) | Passive | Unidirectional review |
| SR-DCR/ACVD [8] | Asymmetric debate | Binary (Defender/Critic) | Passive | Unidirectional + Judge |
| AceMAD [9] | Asymmetric potential | Theoretical | n/a | Multi-round proof |
| AgentSociety [16] | Population simulation | Homogeneous | Passive | Observation only |
| **Ploidy** | **Structured debate** | **Spectrum (Deep→Fresh)** | **Passive + Active** | **Bidirectional + convergence** |

### 2.7 Distinction from Multi-Agent Task Division

Claude Agent Teams and similar systems (CrewAI, MetaGPT) implement cooperative division — splitting work across agents for throughput. Context asymmetry in these systems is a side effect of task scoping, not a deliberate mechanism. Ploidy implements cooperative verification — the same problem is analyzed from intentionally different information states, and disagreements are the primary output.

---

## 3. The Ploidy Protocol

### 3.1 The Context Asymmetry Spectrum

Prior work treats context as binary: full context vs. no context. We propose a two-dimensional spectrum defined by **context depth** and **context delivery mode**.

**Context depth** determines how much prior knowledge a session receives:

```
Context = 0          Context = compressed       Context = full
(Fresh)              (Semi-Fresh)               (Deep)
   │                      │                         │
Zero prior           Failure summary /           Full project
knowledge            structured digest           history
```

- **Deep**: Full project context — codebase, decision history, accumulated knowledge. Maximizes domain awareness but risks anchoring bias.
- **Semi-Fresh**: Compressed context — a structured summary of prior attempts, known constraints, or failure modes, without the full narrative that induces entrenchment. Analogous to an experienced outsider or a practitioner restarting a stuck project with lessons learned but freed from sunk-cost attachment.
- **Fresh**: Zero prior context — only the raw artifact under review. Maximizes independence but lacks domain constraints.

**Context delivery mode** determines how context reaches the session, independently of depth:

- **Passive delivery**: Context is embedded directly in the prompt and is always present in the context window. Every response is implicitly influenced by this context, whether or not it is relevant to the specific question being answered. This mirrors the expert whose 20 years of experience unconsciously shapes every judgment.
- **Active delivery**: Context is available through an explicit retrieval mechanism (e.g., a tool call) but is not present in the window until requested. The session must decide when and whether to consult prior knowledge. This mirrors the consultant who researches on demand rather than relying on ingrained assumptions.

The same information, delivered passively vs. actively, may produce different entrenchment dynamics. Passive delivery maximizes the risk of anchoring bias (the context is always "priming" the model), while active delivery introduces a selection step that may reduce entrenchment — the session must formulate a query, which requires some metacognitive awareness of what it does not know.

```
             Passive              Active               None
             (always in window)   (tool/retrieval)     (absent)
            ┌────────────────────┬───────────────────┬──────────┐
Full        │ Deep               │ Deep-Active       │   n/a    │
            │ (expert intuition) │ (expert + lookup) │          │
            ├────────────────────┼───────────────────┼──────────┤
Compressed  │ Semi-Fresh-Passive │ Semi-Fresh-Active │   n/a    │
            │ (briefed outsider) │ (consultant)      │          │
            ├────────────────────┼───────────────────┼──────────┤
None        │        n/a         │       n/a         │  Fresh   │
            │                    │                   │ (novice) │
            └────────────────────┴───────────────────┴──────────┘
```

This 2D space yields five distinct session configurations. The current implementation supports Deep (full/passive) and Fresh (none). Semi-Fresh variants and Active delivery are proposed as key extensions (§6.2, §7).

### 3.2 Architecture

MCP client sessions connect to a single Ploidy server via Streamable HTTP:

- **Deep session**: Full project context (codebase, history, prior decisions)
- **Fresh session**: Only the raw artifact under review (code snippet, architecture question)
- **Semi-Fresh session** (proposed): Deep's POSITION output, compressed by a summarization step, as the only context

The server maintains debate state in SQLite (WAL mode) and enforces the phase protocol.

### 3.3 Debate Phases

1. **POSITION**: All sessions independently analyze the artifact. Each produces a list of findings with confidence levels.
2. **CHALLENGE**: Each session reviews the others' positions. For each finding, the reviewer responds with a typed semantic action:
   - `agree` — finding is valid
   - `challenge` — finding is wrong or misleading, with explanation
   - `propose_alternative` — finding is partially right, here's a different framing
   - `synthesize` — combining both perspectives into a stronger finding
3. **CONVERGENCE**: The protocol analyzes the debate transcript and classifies outcomes:
   - **Agreements**: findings confirmed by multiple sessions
   - **Productive disagreements**: findings where challenge/synthesis produced new insight
   - **Irreducible disagreements**: genuine differences that could not be resolved
   - **Confidence score**: proportion of agreed findings

### 3.4 Design Principles

- **No shared memory**: Fresh/Semi-Fresh sessions never see Deep's raw analysis outside the debate protocol
- **Typed actions over free-form**: Semantic actions make the debate transcript machine-interpretable
- **Disagreement as signal**: Irreducible disagreements are informative, not failures — they mark where context mattered

---

## 4. Implementation

Ploidy is implemented as a Python MCP server (FastMCP, asyncio, aiosqlite) exposing 9 tools over Streamable HTTP on port 8765. The server manages debate lifecycle, enforces phase transitions via a finite state machine (INDEPENDENT → POSITION → CHALLENGE → CONVERGENCE → COMPLETE), and persists all state in SQLite with WAL mode for crash recovery. Per-debate asyncio locks guard concurrent phase transitions.

We note that the experiments in §5 use the `claude --print` CLI to simulate the protocol rather than the MCP server directly, as this provides cleaner session isolation for controlled comparison. Each CLI invocation creates a guaranteed-fresh session with no shared state. The MCP server is designed for production use where two human-operated terminals connect to the same server instance.

Full source: https://github.com/heznpc/ploidy

---

## 5. Experiments

This section reports preliminary pilot results. All findings should be interpreted as observations from a small-scale pilot study, not as statistically validated conclusions. We report both null and positive observations to bound where context asymmetry applies.

### 5.1 Setup

We evaluate on 10 tasks across two context regimes:
- **Experiment 1** (short context, ~50 tokens): 5 code review tasks with injected bugs + 2 architecture decision tasks. Each has 3–5 ground-truth issues.
- **Experiment 2** (long context, 2,000–5,000 tokens): 3 architecture decision tasks with project histories containing anchoring-inducing biases. Each has 5–6 ground-truth issues.

**Methods** (all using Claude Opus 4.6 via `claude --print`, each invocation = fresh session):
1. **Single Session**: One session with full context.
2. **Independent Second Opinion**: Two sessions with full context, responses concatenated.
3. **CCR (Unidirectional)**: Deep session produces analysis; Fresh session reviews it.
4. **Symmetric Debate**: Two sessions with identical full context debate each other.
5. **Ploidy (Asymmetric Debate)**: Deep (full context) vs Fresh (zero context), structured protocol.

**Judge**: Claude Opus 4.6 evaluates each method's output against ground truth. For each ground-truth issue: FOUND (1.0), PARTIAL (0.5), or MISSED (0.0). Additional valid findings not in ground truth are counted separately as bonus findings.

**Metrics**: Recall = (found + 0.5 × partial) / total ground truth. Precision and F1 are reported but include bonus findings in the denominator, which penalizes methods that produce more valid-but-unlisted findings. We flag this as a metric design issue (§5.3) and recommend interpreting recall as the primary indicator of ground-truth detection.

**Limitations of this setup** (expanded in §6.3): single run per method-task pair, author-defined ground truth without independent validation, same model family as judge, and CLI simulation rather than MCP server execution.

### 5.2 Results (Experiment 1: Short-Context Tasks)

7 tasks (5 code review + 2 architecture), Claude Opus 4.6, single run per method.

| Method | Avg F1 | Avg Recall | Avg Time |
|--------|--------|------------|----------|
| Single Session | **0.573** | 3.7/4.1 | 40s |
| Second Opinion | 0.554 | 4.1/4.1 | 89s |
| CCR (Unidirectional) | 0.548 | 3.9/4.1 | 92s |
| Symmetric Debate | 0.555 | 4.0/4.1 | 118s |
| Ploidy (Asymmetric) | 0.540 | 3.9/4.1 | 205s |

**Observation: No method consistently outperforms Single Session on these tasks.** All methods achieve near-perfect recall (90–100%), and F1 differences are driven by precision (bonus findings inflating denominators). This is consistent with the prediction that context asymmetry provides no benefit when context is too short for entrenchment to occur.

### 5.3 Analysis: Why Context Asymmetry Did Not Help

**1. Insufficient context depth.** Each task's project context was ~50 tokens. Context entrenchment requires accumulated context on the order of thousands of tokens. At 50 tokens, the Deep session develops no meaningful anchoring bias.

**2. Task difficulty ceiling.** Claude Opus 4.6 found nearly all ground-truth issues in every method. When baseline recall is near-perfect, multi-session methods cannot demonstrate improvement.

**3. Metric design issue.** Our F1 formulation includes bonus findings (valid issues not in ground truth) in the precision denominator. This systematically penalizes more thorough methods. A revised metric should either exclude bonus findings from precision or report them as a separate axis. We retain the current formulation for transparency but caution against interpreting F1 differences smaller than the observed stochastic variance (±0.10).

### 5.4 Qualitative Observations

Despite quantitative parity, Ploidy's convergence phase produced qualitatively distinct outputs:

- **Severity calibration**: Fresh session challenged Deep's severity escalation of a memory leak, arguing it depends on key cardinality — a nuance absent from single-session output.
- **Novel findings**: Fresh identified that `get()` being `async` without `await` affects race condition exploitability — a finding neither session produced in isolation.
- **Explicit disagreement tracking**: Typed semantic actions create a machine-readable audit trail of how conclusions were reached, which no other method provides.

### 5.5 Experiment 2: Long-Context Tasks

To test whether context asymmetry matters when context is long enough to induce entrenchment, we designed 3 architecture decision tasks with 2,000–5,000 token project histories containing anchoring-inducing biases:

- **DB migration**: 18-month history of PostgreSQL commitment, repeated rejection of alternatives, team pride in custom partitioning
- **Auth overhaul**: 2-year history of custom auth built by one developer who defends it
- **Microservice split**: 3-year monolith with premature microservice extraction in progress

Each task's context is designed so that a session anchored to the project history will rationalize the status quo. We acknowledge that this design creates a risk of circularity — context-free sessions are expected to be less anchored by definition (§6.3).

**Results:**

| Method | Avg F1 | Avg Recall (Found/Total) | Avg Time |
|--------|--------|--------------------------|----------|
| Symmetric Debate | **0.607** | **5.0**/5.3 | 146s |
| Single Session | 0.591 | 4.3/5.3 | 52s |
| Second Opinion | 0.566 | 4.3/5.3 | 108s |
| Ploidy (Asymmetric) | 0.561 | 4.7/5.3 | 294s |
| CCR (Unidirectional) | 0.458 | 4.7/5.3 | 108s |

Per-task breakdown:

| Task | GT | Single | 2nd Op. | CCR | Sym. | Ploidy |
|------|---:|-------:|--------:|----:|-----:|-------:|
| DB migration | 5 | .571 (3F+2P) | .600 | .500 | .600 | .500 (**5F**) |
| Auth overhaul | 5 | .556 | .450 | .375 | .556 | .450 |
| Microservice split | 6 | .647 | .647 | .500 | .667 | **.733** |

Note: Ploidy's F1 on DB migration (0.500) is lower than Symmetric's (0.600) despite Ploidy achieving 5/5 FOUND vs Symmetric's 4F+1P, because Ploidy generated more bonus findings (10 vs 5). On recall alone — the metric we argue better captures decision quality — Ploidy leads on 2 of 3 tasks.

### 5.6 Observations Across Both Experiments

**Observation 1: Recall gap widens with context length.** In Experiment 1, Ploidy's recall was +5% over Single Session; in Experiment 2, +8%. We note this is observed across only two data points and cannot support a trend claim without additional context-length conditions.

**Observation 2: Ploidy achieved the highest recall on the most bias-laden task.** On the DB migration task, Ploidy was the only method to achieve 5/5 FOUND with zero partial in both runs. Single Session found 3/5 (Run 1) and 4/5 (Run 2). The two issues Single Session hedged on — "the team's PostgreSQL expertise is anchor bias" and "the CTO's rejection of TimescaleDB should be challenged" — are exactly the findings that require contradicting the project history.

**Observation 3: Symmetric Debate is a strong baseline,** suggesting that debate itself has value independent of context asymmetry. Whether asymmetry adds value *on top of* debate is the key open question. The DB migration result suggests yes for heavily biased contexts; the Auth overhaul result suggests no for moderate bias.

**Observation 4: F1 is unstable for multi-phase methods.** Re-run analysis shows Ploidy's F1 varying by 0.106 across runs while recall remained stable. This variance comes entirely from bonus findings count, confirming that recall is the more stable measure.

### 5.7 Stochastic Variance (Re-run Analysis)

We re-ran Experiment 2 to measure stochastic variance. The signal-to-noise ratio is concerning: the largest observed method difference in F1 (0.03) is smaller than the within-method run-to-run variance (0.106). This means the F1 rankings in §5.5 are not stable across runs.

**DB migration task (2 runs):**

| Method | Run 1 Found | Run 2 Found | Run 1 F1 | Run 2 F1 |
|--------|------------|------------|---------|---------|
| Single | 3F+2P | 4F+1P | .571 | .643 |
| Ploidy | **5F** | **5F** | .500 | .556 |

Ploidy's recall on this task was deterministic (5/5 in both runs) while Single's was stochastic (3–4/5). This stability, rather than the absolute F1 value, is the most noteworthy observation from these pilot experiments.

---

## 6. Discussion

### 6.1 When Does Context Asymmetry Help?

The two experiments suggest a conditional pattern, consistent with Young [10]'s phase transition theory (debate value scales with knowledge divergence):

1. **Short context (<100 tokens): No observed benefit.** The model has nothing to be anchored to. The Fresh session has no informational advantage.
2. **Long context with anchoring bias (2,000+ tokens): Asymmetry observed to help on the most biased task.** The Fresh session, having never seen the 18-month PostgreSQL commitment history, evaluated alternatives without sunk-cost pressure.
3. **Between these extremes: Unknown.** A systematic context-length gradient experiment (100, 500, 1K, 5K, 10K tokens) is needed to identify the entrenchment threshold.

### 6.2 The Semi-Fresh Hypothesis

Our current design tests only the extremes of the Context Asymmetry Spectrum: full context (Deep) vs. zero context (Fresh). This leaves an important region unexplored — one that may contain the optimal operating point.

Consider a common human practice: when stuck on a problem, practitioners often restart from scratch — but they carry a compressed memory of what was tried and what failed. This behavior decomposes into four cognitive steps:

1. **Compression**: The full work history is distilled to "what was tried, what failed, and why."
2. **Selective forgetting**: Implementation details and dead-end reasoning are discarded, reducing context volume.
3. **Restart**: The problem is approached from a new angle, unencumbered by accumulated commitments.
4. **Implicit constraint**: The compressed memory of prior failures prevents re-exploring known dead ends.

The practitioner who restarts this way is neither an expert entrenched in the problem (Deep) nor a complete novice (Fresh). They are **Semi-Fresh**: equipped with a structured digest of prior attempts but freed from the accumulated context that caused entrenchment. Notably, step 2 is what distinguishes this from simply continuing — selective forgetting breaks the anchoring chain while step 4 preserves the informational value of prior work.

We hypothesize that a Semi-Fresh session — receiving only a compressed summary of the Deep session's analysis (e.g., "approaches attempted, constraints identified, failures encountered") rather than the full project context — may outperform both extremes:

- Better than Fresh: knows which approaches failed, understands domain constraints
- Better than Deep: not anchored to the narrative that induced entrenchment

Furthermore, the **delivery mode** of this compressed context may itself be a significant variable. We propose three Semi-Fresh variants:

1. **Semi-Fresh-Passive**: Compressed summary is injected directly into the prompt. The session always "sees" the prior analysis, analogous to a briefed outsider who has read the executive summary before entering the room.
2. **Semi-Fresh-Active**: Compressed summary is available via explicit tool call ("Use `get_prior_analysis()` to review what was previously attempted"). The session must actively choose to consult prior work, analogous to a consultant who has access to project files but forms an independent assessment first.
3. **Semi-Fresh-Selective**: Only failure information is provided ("These approaches were tried and failed: ..."), excluding successful analyses. This tests whether negative knowledge (what not to do) is more valuable than positive knowledge (what was found) for breaking entrenchment.

**Proposed experiment**: Add these three Semi-Fresh methods to the existing framework. Each requires minimal implementation — one additional summarization step for context compression, and a tool-call wrapper for the Active variant. The key comparison:

```
                           Context Depth
                   None ←————————————→ Full
                    │                    │
Delivery:  Fresh    │    SF-Active       │   Deep
Passive             │    SF-Passive      │   (current)
                    │    SF-Selective    │
                    │                    │
```

If Semi-Fresh-Active outperforms both Fresh and Deep, it would suggest that the optimal verification partner is neither ignorant nor entrenched, but **selectively informed with retrieval autonomy** — a finding with direct implications for how multi-agent systems should manage shared knowledge. If the Active variant outperforms Passive with identical information, it would demonstrate that **how context is delivered matters independently of what context is delivered** — a novel result absent from the existing MAD literature.

This hypothesis is directly testable with the existing experimental framework and, if confirmed, would transform the research question from "does asymmetry help?" to "what is the optimal point in the depth × delivery space?" — a quantitatively richer and more practically useful direction.

### 6.3 Limitations

This pilot study has significant limitations that bound the strength of all claims:

- **Statistical power**: 7+3 tasks, single run per method-task pair (re-run on Exp 2 only). Observed method differences (F1 Δ ≈ 0.03) are smaller than within-method variance (F1 Δ ≈ 0.10). No statistical tests are reported because the sample size and run count cannot support them. Minimum requirement for validated claims: 30+ tasks, 5+ runs, paired statistical tests (Wilcoxon signed-rank or bootstrap CI).
- **Author-defined ground truth**: All ground-truth issues were defined by the authors without independent expert validation. Bonus findings identified by the judge suggest the ground truth is incomplete. Future work should use independently validated benchmarks or multiple expert annotators with inter-rater agreement metrics.
- **Single model family**: All experiments use Claude Opus 4.6 for generation. Observed effects may be Claude-specific — different model families (GPT-4o, Gemini 2.5) may exhibit different anchoring dynamics, context sensitivity, or debate behavior. Cross-model replication with at least two additional model families is necessary before generalizability claims.
- **Same-model judge**: Claude Opus 4.6 generates outputs and evaluates them. Systematic bias is possible (e.g., preference for structured multi-phase outputs, or conversely, penalizing verbose responses). Cross-model judges (GPT-4, Gemini) and a human evaluation subset with Cohen's kappa are needed.
- **Circular task design risk**: Long-context tasks were designed with anchoring biases whose detection is facilitated by context absence. A session without context is expected to be less biased by definition. Stronger validation requires externally-sourced tasks (e.g., real-world architecture decisions from open-source projects) where the relationship between context and bias is not author-designed.
- **Token cost**: Ploidy uses approximately 5× the tokens of Single Session. A fair comparison should include a self-consistency baseline (5 independent runs, majority vote) at equivalent token budget.
- **CLI simulation vs. MCP server**: Experiments use `claude --print` CLI rather than the Ploidy MCP server. While this provides cleaner session isolation, the convergence engine's rule-based classification (in the server) is not exercised in the experiments.
- **Metric design**: The current F1 formulation penalizes valid bonus findings as false positives. This systematically disadvantages more thorough methods and should be revised in future work.

### 6.4 Broader Implications

The stochastic prior lock-in problem is not unique to LLMs. It mirrors the well-documented phenomenon in human organizations and scientific communities where accumulated context — expertise, institutional memory, prior commitments — simultaneously enables domain mastery and prevents paradigm revision [14, 15]. The only reliable corrective, both historically and in our preliminary observations, is the introduction of a perspective that is not entrenched in the accumulated context.

The parallel between human generational turnover and AI session management is instructive:

| | Human generational turnover | AI model/session succession |
|---|---|---|
| New generation's context | Fresh — different environment, different experiences | Inherited — trained on prior generation's outputs |
| Inherited bias | Partial — some cultural transmission, much lost | Total — training data preserves and amplifies biases |
| Role of "funeral" (Planck) | Naturally extinguishes entrenched perspectives | Absent — prior outputs persist indefinitely in training corpora |
| Outcome | Paradigm shifts enabled by context asymmetry between generations [14, 15] | Model collapse — progressive homogenization across generations [18] |

Planck's principle works in human civilization precisely because new generations do not fully inherit the context of their predecessors. In AI, training on prior model outputs creates the opposite dynamic: each generation inherits its predecessor's biases verbatim, and the "funeral" that would naturally erode entrenched perspectives never occurs. Model collapse [18] is, in this framing, the consequence of a civilization without generational context asymmetry.

This has implications for large-scale agent systems. Scaling agent count in simulations where all agents share the same priors produces verification breadth without verification depth: more samples from the same biased distribution. Boca et al. [17] showed that LLM populations spontaneously develop collective biases through interaction, even without individual-level bias — a within-generation analog of the cross-generation homogenization that drives model collapse.

Ploidy suggests a design principle for multi-agent systems: **context diversity is more valuable than agent count**. A small number of sessions with deliberately different context depths may produce better decisions than a large homogeneous population — provided the context differences are structured through a protocol that surfaces and reconciles disagreements rather than averaging them away.

---

## 7. Conclusion and Future Work

We presented Ploidy, a protocol for structured debate between same-model sessions with intentional context asymmetry. Two pilot experiments reveal a context-dependent pattern: no benefit on short-context tasks (Exp 1, 7 tasks), and a qualified positive signal on long-context tasks with anchoring bias (Exp 2, 3 tasks) — specifically, deterministic 5/5 recall on the most bias-laden task across two runs, versus stochastic 3–4/5 for Single Session.

These preliminary results suggest context asymmetry is a **targeted intervention for context entrenchment**, not a universal improvement. The most important open question is the **Semi-Fresh hypothesis**: whether an intermediate context depth (compressed failure summary rather than zero context) outperforms both extremes. This would shift the research question from "does asymmetry help?" to "what is the optimal asymmetry?" — a quantitatively richer direction.

**Future work priorities**:
1. **Semi-Fresh variants**: implement and evaluate Semi-Fresh-Passive, Semi-Fresh-Active, and Semi-Fresh-Selective to map the depth × delivery space
2. **Context delivery mode isolation**: compare identical information delivered passively (in-prompt) vs. actively (tool call) to test whether delivery mode has an independent effect on entrenchment
3. **Statistical validation**: 30+ tasks, 5+ runs per method, paired statistical tests (Wilcoxon signed-rank, bootstrap CI)
4. **Context-length gradient**: systematic evaluation at 100, 500, 1K, 5K, 10K tokens to identify the entrenchment threshold
5. **Cross-model evaluation**: weaker models (where single-session recall is lower) and cross-model judges
6. **External task sets**: real-world architecture decisions from open-source projects to address circular task design concerns
7. **Multi-round protocol**: extending the single-round CHALLENGE phase to test whether AceMAD's submartingale conditions can be satisfied

We release Ploidy as an open-source MCP server at https://github.com/heznpc/ploidy.

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

[14] Kuhn, T. "The Structure of Scientific Revolutions." University of Chicago Press, 1962.

[15] Azoulay, P., Fons-Rosen, C., and Graff Zivin, J.S. "Does Science Advance One Funeral at a Time? Evidence from a Study of Eminent Scientists." American Economic Review, 2019.

[16] Pang et al. "AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents." arXiv:2502.08691, 2025.

[17] Boca et al. "Emergent Social Conventions and Collective Bias in LLM Populations." Science Advances, 2025.

[18] Shumailov et al. "AI Models Collapse When Trained on Recursively Generated Data." Nature, 2024.
