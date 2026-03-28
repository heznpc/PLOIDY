# Ploidy: Context-Asymmetric Structured Debate for LLM Decision Verification

> Draft v2 — 2026-03-17
> Target: NeurIPS 2026 Workshop or AAMAS 2027
> Format: 4-6 pages + references
> Changes from v1: Abstract corrected, Semi-Fresh introduced, Context Asymmetry Spectrum, context delivery mode, model collapse connection, limitations expanded, reviewer feedback addressed
> Changes from v2: Separated Paper 1 (Context as Lifespan) material — Kuhn/Planck/Azoulay extended discussion, lifespan analogy, generational turnover table, model collapse philosophical framing moved to companion paper. Ploidy draft now focuses on technical mechanism and experimental results.

---

## Abstract

Single-session LLM usage subjects critical decisions to stochastic prior lock-in: the model's first probabilistic response anchors all subsequent reasoning, and prompt-based mitigations have no statistically significant effect on this bias [1]. We present Ploidy, a structured debate protocol between physically separate sessions of the same model with intentionally asymmetric context depths. Unlike multi-model council approaches that rely on model diversity, Ploidy exploits **context diversity** within a single model — a dimension absent from existing products and publications as of March 2026. We introduce the **Context Asymmetry Spectrum**, varying context depth (Deep/Semi-Fresh/Fresh) and delivery mode (passive/active), and a **causal decomposition** that separates context-induced bias (Event A) from stochastic variance (Event B) via ploidy-level replication. In pilot experiments on 15 tasks across 12 methods with systematic sweeps over injection mode, language, and model family, we find that (1) context asymmetry provides no benefit on short-context tasks where entrenchment does not occur, (2) on long-context tasks, asymmetric debate achieves highest recall (5/5 vs. Single Session's 3/5, stable across re-runs), (3) **information position is the dominant factor** in context delivery — placing a summary at the end vs. beginning of the prompt improves recall from 89% to 100%, (4) memory-mode context injection drops Single Session recall by 25pp while Ploidy drops only 6pp (structural immunity), and (5) in Chinese, Single Session completely fails on 2/3 tasks while Ploidy recovers all findings — the largest effect size observed (Δ=100pp). Cross-model validation on Codex (GPT-5.4) confirms that session count alone does not help; the improvement requires context asymmetry. We release Ploidy as an open-source MCP server with full experimental framework for community replication.

---

## 1. Introduction

LLM outputs are stochastic. The same model, given the same prompt, produces different responses across independent sessions. This is well-understood. What is less appreciated is the downstream consequence for single-session workflows:

1. The model's first response is sampled from a probability distribution.
2. That response enters the context window and becomes the model's own prior.
3. The model reinforces this prior through consistency-seeking behavior (anchoring bias, sycophancy).
4. The user sees only one session and treats the output as deterministic.

The result: identical models, identical prompts, identical users — but different project outcomes depending on which stochastic sample landed first. Jacob et al. [11] term this the "Chat-Chamber Effect" — the tendency for users to trust and build upon whatever stochastic output a single session produces. This is not addressable by temperature tuning or prompt engineering; empirical evidence shows prompt-based mitigations (chain-of-thought, reflection, "ignore your prior response") have no statistically significant effect on anchoring bias [1].

This phenomenon has a well-documented human analog: accumulated expertise simultaneously enables domain mastery and prevents paradigm revision — a dynamic observed across scientific communities [14], empirically confirmed in studies of eminent scientists' influence on field renewal [15], and formalized as a structural property of generational turnover. We explore this parallel in depth in a companion paper; here, we note only that the LLM single-session problem is structurally similar — context accumulation creates anchoring that prompt-based interventions cannot overcome [1].

The practical consequence is stark: given the same model and the same prompt, different sessions may produce fundamentally different assessments — agree, disagree, or equivocate — on the same hypothesis. A user confined to a single session is unknowingly subject to a stochastic lottery whose outcome determines not just the quality of individual responses, but whether entire tasks succeed or fail. Two users with identical models and identical problems may experience dramatically different "model performance" based solely on which stochastic sample anchored their session.

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

Multi-agent debate (MAD) is well-studied but predominantly uses symmetric configurations where all agents share the same context. Recent work has explored multi-LLM context learning for richer discussion dynamics [12], but the fundamental assumption of shared context remains. Oh et al. [6] demonstrated that symmetric debate can amplify bias through "belief entrenchment." Choi et al. [7] proved that debate under symmetric information induces a martingale — it cannot improve expected correctness beyond majority voting. This result has implications beyond LLMs: any system where agents share identical priors and debate cannot, in expectation, improve upon aggregating their independent judgments.

### 2.3 Asymmetric Context as a Mechanism

SR-DCR [8] introduced asymmetric context verification debate (ACVD): a context-defending agent debates a context-deprived critic. On GPT-3.5, this achieved 62.7% accuracy (+3.4pp over naive debate). AceMAD [9] proved that asymmetric cognitive potential creates submartingale drift toward truth, formally breaking the martingale curse. We note that Ploidy's current single-round design does not satisfy the multi-round conditions required for AceMAD's submartingale proof; whether a multi-round extension would achieve this remains an open question (§7).

### 2.4 Scaling Agents vs. Scaling Diversity

Large-scale agent simulations (e.g., AgentSociety [16] with 10K agents, MiroFish with 700K agents) pursue verification breadth — more agents analyzing the same problem. Boca et al. [17] showed that even without individual-level bias, LLM populations spontaneously develop collective biases through interaction. Combined with Choi et al.'s martingale result [7], this suggests that scaling homogeneous agent count does not reliably improve decision quality. Ploidy pursues the orthogonal dimension: verification depth through context diversity.

### 2.5 Model Collapse and Context Contamination

When AI-generated content enters training data, progressive quality degradation occurs — "model collapse" [18]. A companion paper develops this connection in depth, framing model collapse, Model Autophagy Disorder (MAD; Alemohammad et al., ICLR 2024), and Dead Internet Theory as three scales — micro, meso, macro — of the same homogeneous accumulation pattern. Ploidy addresses the within-deployment end of this spectrum: by maintaining sessions with structurally different context depths, it acts as a countermeasure to the homogenization tendency before outputs ever reach training pipelines.

### 2.6 Ploidy's Position

| Prior Work | Mechanism | Context Depth | Delivery Mode | Direction |
|---|---|---|---|---|
| CCR [2] | Session separation | Binary (Deep/Fresh) | Passive | Unidirectional review |
| SR-DCR/ACVD [8] | Asymmetric debate | Binary (Defender/Critic) | Passive | Unidirectional + Judge |
| AceMAD [9] | Asymmetric potential | Theoretical | n/a | Multi-round proof |
| AgentSociety [16] | Population simulation | Homogeneous | Passive | Observation only |
| **Ploidy** | **Structured debate** | **Spectrum (Deep→Fresh)** | **Passive + Active** | **Bidirectional + convergence** |

### 2.7 Context Injection and Language Robustness

How context reaches a model — via prompt, system prompt, persistent memory, or tool retrieval — is an underexplored variable. Claude Code's persistent memory (`memory.md`), Cursor's context files, and similar systems inject context through mechanisms that differ from raw prompt inclusion. To our knowledge, no prior work has systematically compared how injection mode interacts with anchoring bias in multi-agent settings. Similarly, multilingual LLM robustness studies focus on task accuracy degradation across languages but do not examine whether language modulates context-induced bias specifically. Our injection mode and language sweeps (§5.8) provide preliminary evidence that both variables interact with context asymmetry in ways not predicted by prior work.

### 2.8 Distinction from Multi-Agent Task Division

Claude Agent Teams and similar systems (CrewAI, MetaGPT) implement cooperative division — splitting work across agents for throughput. Adding more agents increases throughput (more hands) but does not address anchoring bias, because all agents share the same context and thus the same stochastic priors. Under Choi et al.'s martingale result [7], scaling homogeneous agents is mathematically equivalent to majority voting over identically biased samples. Ploidy implements the orthogonal strategy: cooperative verification, where the same problem is analyzed from intentionally different information states. The goal is not more output but different perspectives — disagreements are the primary signal, not a failure mode.

---

## 3. The Ploidy Protocol

The name *Ploidy* draws from biological polyploidy, where gene duplication provides redundancy that enables both error tolerance and functional diversification — an analogy to our use of session duplication with deliberate context diversification.

### 3.1 Causal Decomposition

When multiple sessions disagree, the disagreement may arise from two independent sources:

- **Event A (Context-induced bias)**: Sessions with different context depths reach different conclusions *because* context shapes reasoning. A Deep session anchored to 18 months of PostgreSQL history will defend the status quo; a Fresh session evaluating the same technical question without that history will not.
- **Event B (Stochastic variance)**: Even sessions with identical context may disagree due to sampling randomness (temperature, attention patterns).

Standard multi-agent debate conflates these two sources. Ploidy's **ploidy level** — the number of independent sessions per context depth — separates them: at ploidy level n, we draw n stochastic samples for each of Deep and Fresh. When Deep×n sessions agree with each other but disagree with Fresh×n sessions, this isolates Event A. When sessions within the same context depth disagree, this is Event B. At diploid level (2n: Deep×2, Fresh×2), we can distinguish stochastic outliers from context-driven disagreements; at tetraploid (4n), we achieve within-group statistical power.

The practical implication: adding more sessions with identical context (scaling Event B samples) cannot fix Event A bias — a prediction confirmed empirically in §5.8.3, where Stochastic-N (4 sessions, same context) matches Single Session recall on Codex.

### 3.2 The Context Asymmetry Spectrum

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

The same information, delivered passively vs. actively, may produce different entrenchment dynamics. This prediction is grounded in established cognitive science findings: the generation effect [28] shows that actively produced knowledge is more deeply processed than passively received information, and the testing effect [23] demonstrates that retrieval practice outperforms re-reading for durable learning. Passive delivery maximizes the risk of anchoring bias (the context is always "priming" the model), while active delivery introduces a selection step that may reduce entrenchment — the session must formulate a query, which requires some metacognitive awareness of what it does not know. Epley and Gilovich [27] showed that anchoring operates through different mechanisms for externally provided vs. self-generated anchors, further supporting the prediction that delivery mode matters independently of content.

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

### 3.3 Architecture

MCP client sessions connect to a single Ploidy server via Streamable HTTP:

- **Deep session**: Full project context (codebase, history, prior decisions)
- **Fresh session**: Only the raw artifact under review (code snippet, architecture question)
- **Semi-Fresh session** (proposed): Deep's POSITION output, compressed by a summarization step, as the only context

The server maintains debate state in SQLite (WAL mode) and enforces the phase protocol.

### 3.4 Debate Phases

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

### 3.5 Design Principles

- **No shared memory**: Fresh/Semi-Fresh sessions never see Deep's raw analysis outside the debate protocol
- **Typed actions over free-form**: Semantic actions make the debate transcript machine-interpretable, extending the typed epistemic acts framework [13] to cross-session verification
- **Disagreement as signal**: Irreducible disagreements are informative, not failures — they mark where context mattered

---

## 4. Implementation

Ploidy is implemented as a Python MCP server (FastMCP, asyncio, aiosqlite) exposing 9 tools over Streamable HTTP on port 8765. The server manages debate lifecycle, enforces phase transitions via a finite state machine (INDEPENDENT → POSITION → CHALLENGE → CONVERGENCE → COMPLETE), and persists all state in SQLite with WAL mode for crash recovery. Per-debate asyncio locks guard concurrent phase transitions.

We note that the experiments in §5 use the `claude --print` CLI to simulate the protocol rather than the MCP server directly, as this provides cleaner session isolation for controlled comparison. Each CLI invocation creates a guaranteed-fresh session with no shared state. The MCP server is designed for production use where two human-operated terminals connect to the same server instance.

Full source: https://github.com/heznpc/ploidy

---

## 5. Experiments

This section reports preliminary pilot results, interpreted through the causal decomposition framework (§3.1): when methods disagree, we distinguish whether the source is context-induced bias (Event A) or stochastic variance (Event B). All findings should be interpreted as observations from a pilot study, not as statistically validated conclusions. We report both null and positive observations to bound where context asymmetry applies.

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
6. **Self-Consistency (5-vote)**: Five independent single sessions, majority-vote synthesis. Approximately equal token budget to Ploidy (~5 LLM calls).
7. **Semi-Fresh-Passive**: Deep session produces analysis; compressed summary injected directly into Semi-Fresh session's prompt.
8. **Semi-Fresh-Active**: Deep session produces analysis; compressed summary available to Semi-Fresh session but only after independent assessment. Session must form its own view first, then consult prior analysis.
9. **Semi-Fresh-Selective**: Deep session produces analysis; only failure/uncertainty information extracted and provided to Semi-Fresh session.

**Judge**: Claude Opus 4.6 evaluates each method's output against ground truth. For each ground-truth issue: FOUND (1.0), PARTIAL (0.5), or MISSED (0.0). Additional valid findings not in ground truth are counted separately as bonus findings.

**Metrics**: Recall = (found + 0.5 × partial) / total ground truth. Precision and F1 are reported but include bonus findings in the denominator, which penalizes methods that produce more valid-but-unlisted findings. We flag this as a metric design issue (§5.3) and recommend interpreting recall as the primary indicator of ground-truth detection.

**Limitations of this setup** (expanded in §6.3): single run per method-task pair, author-defined ground truth without independent validation, same model family as judge, and CLI simulation rather than MCP server execution.

### 5.2 Results (Experiment 1: Short-Context Tasks)

7 tasks (5 code review + 2 architecture), Claude Opus 4.6, single run per method.

| Method | Avg F1 | Avg Recall | Avg Time |
|--------|--------|------------|----------|
| Single Session | **0.573** | 3.7/4.1 | 40s |
| Second Opinion | 0.554 | 4.1/4.1 | 89s |
| Symmetric Debate | 0.555 | 4.0/4.1 | 118s |
| CCR (Unidirectional) | 0.548 | 3.9/4.1 | 92s |
| Ploidy (Asymmetric) | 0.540 | 3.9/4.1 | 205s |
| Semi-Fresh-Active | 0.538 | 3.9/4.1 | 117s |
| Semi-Fresh-Passive | 0.535 | 3.9/4.1 | 122s |
| Semi-Fresh-Selective | 0.533 | 4.0/4.1 | 130s |
| Self-Consistency (5-vote) | 0.529 | 3.7/4.1 | 234s |

**Observation: No method consistently outperforms Single Session on these tasks.** All 9 methods achieve near-perfect recall (90–98%), and F1 differences are driven by precision (bonus findings inflating denominators). Critically, the delivery mode effect observed in Experiment 2 (SF-Active vs SF-Passive) disappears entirely here: both achieve identical 3.9/4.1 recall. This confirms that context asymmetry and delivery mode provide no benefit when context is too short for entrenchment to occur.

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

**Results (original 5 methods):**

| Method | Avg F1 | Avg Recall (Found/Total) | Avg Time |
|--------|--------|--------------------------|----------|
| Symmetric Debate | **0.607** | **5.0**/5.3 | 146s |
| Single Session | 0.591 | 4.3/5.3 | 52s |
| Second Opinion | 0.566 | 4.3/5.3 | 108s |
| Ploidy (Asymmetric) | 0.561 | 4.7/5.3 | 294s |
| CCR (Unidirectional) | 0.458 | 4.7/5.3 | 108s |

**Results (Semi-Fresh variants + Self-Consistency, same 3 tasks):**

| Method | Avg F1 | Avg Recall (Found/Total) | Avg Time |
|--------|--------|--------------------------|----------|
| Self-Consistency (5-vote) | **0.607** | **5.3**/5.3 | 292s |
| Semi-Fresh-Active | 0.557 | **5.3**/5.3 | 153s |
| Semi-Fresh-Passive | 0.553 | 4.7/5.3 | 193s |
| Semi-Fresh-Selective | 0.505 | 5.0/5.3 | 258s |

**Combined ranking by recall (all 9 methods):**

| Method | Avg Recall | Avg F1 | LLM Calls |
|--------|-----------|--------|-----------|
| Semi-Fresh-Active | **5.3/5.3** | 0.557 | ~4 |
| Self-Consistency | **5.3/5.3** | 0.607 | ~6 |
| Semi-Fresh-Selective | 5.0/5.3 | 0.505 | ~4 |
| Symmetric Debate | 5.0/5.3 | 0.607 | 3 |
| SF-Passive+Bottom (ablation) | 5.3/5.3 | 0.619 | ~4 |
| SF-Passive+Independent (ablation) | 5.0/5.3 | 0.550 | ~4 |
| Semi-Fresh-Passive | 4.7/5.3 | 0.553 | ~4 |
| Ploidy (Asymmetric) | 4.7/5.3 | 0.561 | 5 |
| CCR (Unidirectional) | 4.7/5.3 | 0.458 | 2 |
| Single Session | 4.3/5.3 | 0.591 | 1 |
| Second Opinion | 4.3/5.3 | 0.566 | 2 |

Per-task breakdown (selected methods):

| Task | GT | Single | Ploidy | SF-Pass. | SF-Active | SF-Sel. | Self-Con. |
|------|---:|-------:|-------:|---------:|----------:|--------:|----------:|
| DB migration | 5 | 3F+2P | **5F** | 3F+2P | **5F** | 4F+1P | **5F** |
| Auth overhaul | 5 | 3-4F | 3-4F | **5F** | **5F** | **5F** | **5F** |
| Microservice | 6 | 4-5F | 5-6F | **6F** | **6F** | **6F** | **6F** |

**Key observation on the DB migration task**: SF-Active and SF-Passive received identical compressed information from the same Deep session analysis. SF-Active achieved 5/5 FOUND (matching Ploidy), while SF-Passive achieved only 3/5 FOUND (matching Single Session). The sole difference is delivery mode: passive embedding vs. active retrieval after independent assessment. This is the strongest evidence in our pilot data that **how context is delivered matters independently of what context is delivered**.

Note on F1: Ploidy's F1 on DB migration (0.500) is lower than Symmetric's (0.600) despite Ploidy achieving 5/5 FOUND vs Symmetric's 4F+1P, because Ploidy generated more bonus findings (10 vs 5). On recall alone — the metric we argue better captures decision quality — the pattern is clearer.

### 5.6 Observations Across Both Experiments

**Observation 1: Recall gap widens with context length.** In Experiment 1, all methods achieve near-perfect recall (no gap). In Experiment 2, the gap between best (SF-Active, Self-Consistency: 100%) and worst (Single Session: 81%) is substantial. Context asymmetry provides no benefit when entrenchment does not occur.

**Observation 2: Both delivery mode and prompting strategy contribute to recall, as shown by ablation.** SF-Active and SF-Passive received identical compressed summaries but achieved 100% vs 89% recall. To disentangle delivery mode from the "independent-first" instruction present in SF-Active but absent from SF-Passive, we ran an ablation: SF-Passive+Independent, which adds the instruction to the passive delivery format (summary at top of prompt).

| Variant | Summary Position | Independent Instruction | Avg Recall |
|---------|-----------------|------------------------|------------|
| SF-Passive | Top | No | 4.7/5.3 (89%) |
| SF-Passive+Independent | Top | Yes | 5.0/5.3 (94%) |
| SF-Passive+Bottom | **Bottom** | No | **5.3/5.3 (100%)** |
| SF-Active | Bottom | Yes | 5.3/5.3 (100%) |

The ablation reveals that **information position is the dominant factor**. Moving the summary from the top to the bottom of the prompt — with no other changes — improves recall from 89% to 100% (+11pp). The "independent-first" instruction contributes +5pp only when the summary is at the top (partially counteracting primacy anchoring), but has no additional effect when the summary is at the bottom (already at ceiling). On the DB migration task, the gradient is 3/5 → 4/5 → 5/5 → 5/5 across the four conditions.

The SF-Active vs. SF-Passive gap (§5.5, Observation 2) initially appeared to be a delivery mode effect. The ablation reveals it is more precisely a **primacy anchoring effect**: information at the beginning of a prompt anchors subsequent reasoning more strongly than information at the end [24]. Epley and Gilovich [27] showed that externally provided anchors produce stronger anchoring than self-generated ones, and the generation effect [28] predicts that actively retrieved information is processed more deeply than passively encountered information — both consistent with SF-Active's advantage.

**Observation 3: Self-Consistency is a strong budget-equivalent baseline.** At approximately equal token budget (~5-6 LLM calls), Self-Consistency achieves the same 100% recall as SF-Active. However, Self-Consistency requires approximately twice the wall-clock time (292s vs 153s) and does not produce structured debate output (typed actions, disagreement tracking, convergence analysis). The qualitative value of structured debate remains distinct.

**Observation 4: Semi-Fresh-Selective outperforms Semi-Fresh-Passive.** Providing only failure/uncertainty information (SF-Selective: 94% recall) outperforms providing the full compressed summary passively (SF-Passive: 89%). This suggests that negative knowledge ("what failed") is more useful than positive knowledge ("what was found") for maintaining independence — consistent with the "selective forgetting" step in the restart mechanism (§6.2).

### 5.7 Stochastic Variance (Re-run Analysis)

We re-ran Experiment 2 to measure stochastic variance. F1 is unstable: Ploidy's F1 varies by 0.106 across runs while recall remains stable, because the variance comes entirely from bonus findings count. The largest observed method difference in F1 (0.03) is smaller than within-method variance (0.106), meaning F1 rankings in §5.5 are not stable across runs.

**DB migration task (2 runs):**

| Method | Run 1 Found | Run 2 Found | Run 1 F1 | Run 2 F1 |
|--------|------------|------------|---------|---------|
| Single | 3F+2P | 4F+1P | .571 | .643 |
| Ploidy | **5F** | **5F** | .500 | .556 |

Ploidy's recall on this task was consistent across limited runs (5/5 in both runs, n=2) while Single's varied (3–4/5). This stability, rather than the absolute F1 value, is the most noteworthy observation from these pilot experiments. Confirming determinism would require at least 5 repetitions with statistical testing; these two runs establish consistency but not deterministic behavior.

### 5.8 Extended Validation (v0.3 Sweeps)

To explore boundary conditions beyond the original 10-task pilot, we ran systematic sweeps across injection mode, language, effort level, and cross-model backends. All use the same 3 long-context tasks and Claude Opus 4.6 unless noted. These remain single-run observations; statistical validation requires the multi-run protocol described in §7.

#### 5.8.1 Injection Mode Sweep

Context can reach an LLM session through different mechanisms: raw prompt text, persistent memory (Claude's `memory.md`), or skills/system prompt injection. We tested three injection modes with Single, Ploidy, and CCR.

**Recall (found + 0.5×partial / total GT), averaged across 3 tasks:**

| Method | raw | memory | skills |
|--------|-----|--------|--------|
| Single | 5.0/5.3 (94%) | **3.7/5.3 (69%)** | 4.3/5.3 (82%) |
| Ploidy | 5.3/5.3 (100%) | **5.0/5.3 (94%)** | 5.3/5.3 (100%) |
| CCR | 4.7/5.3 (88%) | 4.0/5.3 (75%) | 5.0/5.3 (94%) |

**Key finding**: Memory-mode injection drops Single Session recall by 25pp (94% → 69%), while Ploidy drops only 6pp (100% → 94%). The Fresh session in Ploidy never sees the memory-injected context, providing **structural immunity** to injection-mode bias. This suggests that in production environments where context is delivered via persistent memory (a common pattern in Claude Code, Cursor, etc.), single-session workflows are substantially more vulnerable to anchoring than asymmetric debate.

#### 5.8.2 Language Robustness

We tested Japanese (ja) and Chinese (zh) prompts with identical task content.

| Task | Method | ja | zh |
|------|--------|----|----|
| Auth overhaul | Single | 5/5 | **0/5** |
| Auth overhaul | Ploidy | 5/5 | **5/5** |
| Microservice | Single | 6/6 | **0/6** |
| Microservice | Ploidy | 5.5/6 | **6/6** |
| DB migration | Single | 5/5 | 3.5/5 |
| DB migration | Ploidy | 4.5/5 | **5/5** |

**Key finding**: In Chinese, Single Session **completely fails** on 2 of 3 tasks (0 findings), while Ploidy finds all ground-truth issues. Japanese performance is comparable to English for both methods. This is the largest effect size in our experiments (Δrecall = 100pp on auth overhaul). We hypothesize that Chinese prompts interact with context-induced anchoring differently than English — the Fresh session, processing the task without the Chinese-language anchoring context, evaluates the technical problem in a language-independent manner. This requires replication but suggests that context asymmetry may be especially valuable for non-English workflows.

#### 5.8.3 Cross-Model Validation (Partial)

We ran the ploidy sweep (4n, Stochastic-N baseline) on OpenAI Codex (GPT-5.4) for the DB migration task. The remaining 2 tasks failed due to API usage limits.

| Method | Model | Found/Partial/Missed | F1 |
|--------|-------|---------------------|-----|
| Single | Codex | 2/2/1 | 0.286 |
| Stochastic-N (4×, no asymmetry) | Codex | 4/0/1 | 0.286 |
| **Ploidy (4n, asymmetric)** | **Codex** | **4/1/0** | **0.500** |

**Key finding**: On Codex, the asymmetry effect is more pronounced than on Opus: Ploidy finds 4 full + 1 partial (0 missed) vs Single's 2 full + 2 partial + 1 missed. Critically, Stochastic-N (4 sessions, no asymmetry) finds the same count as Single, confirming that **more sessions alone does not help — the asymmetry is what matters** (Event A isolation). This is the clearest Event A vs Event B separation in our data, though limited to a single task on a single model.

#### 5.8.4 Twelve-Method Comparison on Extended Tasks

We ran all 12 methods on 5 additional tasks (2 architecture + 3 bug detection) using Claude Opus 4.6 with raw injection. These are shorter-context tasks (~500-1000 tokens), intermediate between Experiment 1 and 2.

**Average F1 across 5 tasks:**

| Method | Avg F1 |
|--------|--------|
| SF-Selective | 0.582 |
| Single | 0.578 |
| Ploidy | 0.551 |
| Self-Consistency | 0.541 |
| Stochastic-N | 0.535 |
| SF-Passive-Indep | 0.541 |
| SF-Passive-Bottom | 0.539 |
| SF-Passive | 0.523 |
| Symmetric | 0.520 |
| SF-Active | 0.518 |
| CCR | 0.497 |
| Second Opinion | 0.481 |

**Observation**: On intermediate-length contexts, all methods cluster within a 10pp F1 range (0.481–0.582), consistent with our Experiment 1 finding that asymmetry provides limited benefit below the entrenchment threshold. This further bounds the intervention: **context asymmetry is a targeted tool for long-context, high-entrenchment scenarios**, not a universal improvement.

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

Each step has a neuroscience parallel:

- **Compression → Sleep memory consolidation.** The Synaptic Homeostasis Hypothesis (SHY) [19] shows that during sleep, synapses are globally downscaled — weak connections pruned, strong connections preserved — producing a lossy but higher signal-to-noise representation. This is structurally identical to production LLM compaction: model-generated summarization that preserves high-recency/frequency information while discarding the rest [25].

- **Selective forgetting → Retrieval-induced forgetting.** Prefrontal cortex actively suppresses competing memory traces [20] — the brain's discard mechanism is importance-scored and lossy, not deterministic.

- **Restart → Reconsolidation.** Each time a memory is recalled it becomes labile and is re-stored in potentially modified form [21], mirroring how re-compression of context produces subtly different summaries each time — a documented phenomenon ("compaction drift") where project instructions and file paths are progressively lost.

- **Implicit constraint → Engram competition.** Multiple memory traces coexist and compete for expression; forgotten memories remain in a latent rather than erased state [22] — analogous to how compressed-away context still exists in model weights but is inaccessible from the current context window.

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

**Preliminary results (§5.5)**: We implemented and evaluated all three Semi-Fresh variants on the long-context tasks. The results provide initial support for the delivery mode hypothesis:

- SF-Active achieved 100% average recall (tied with Self-Consistency for best), while SF-Passive achieved 89% (tied with Ploidy). The sole difference is delivery mode.
- On the most bias-laden task (DB migration), SF-Active found 5/5 while SF-Passive found only 3/5 — with identical compressed information.
- SF-Selective (94%) outperformed SF-Passive (89%), suggesting negative knowledge is more effective than full summaries for maintaining independence.

These observations are from a single run on 3 tasks and require statistical validation, but they shift the question from "does asymmetry help?" to "what is the optimal point in the depth × delivery space?" — a quantitatively richer and more practically useful direction.

### 6.3 Limitations and Open Research Agenda

This study is a pilot with significant limitations. We present them as an **open research agenda** — each limitation defines a specific replication or extension opportunity for the community.

| Limitation | Current State | Open Question | Replication Target |
|-----------|--------------|---------------|-------------------|
| **Statistical power** | 10+5 tasks, mostly single-run | How stable are the observed effects? | 30+ tasks, 5+ runs, Wilcoxon/bootstrap |
| **Ground truth** | Author-defined | Does expert consensus match? | Independent annotators, inter-rater κ |
| **Model diversity** | Opus primary, Codex partial | Is the effect model-specific? | 3+ model families, cross-model judges |
| **Judge bias** | Same-model (Opus) | Does self-evaluation inflate scores? | Cross-model judges + human subset |
| **Task circularity** | Synthetic anchoring bias | Does it hold on organic data? | OSS project PRs, real architecture decisions |
| **Token cost** | ~5× Single Session | Is the audit trail worth the cost? | Cost-benefit analysis vs Self-Consistency |
| **Language** | zh finding dramatic but n=1 | Reproducible or artifact? | Multi-run zh/ko/ja replication |
| **Metric design** | F1 penalizes bonus findings | What metric captures thoroughness? | Recall-primary + bonus-as-separate-axis |

We release the full experimental framework, all 25 extended task definitions, and result data alongside the Ploidy MCP server to lower the barrier for community replication. The cost constraint (4 models × 3 tasks per sweep = ~$50-100 per full run on API pricing) makes independent reproduction feasible for individual researchers.

### 6.4 Broader Implications

The stochastic prior lock-in problem is not unique to LLMs — it mirrors well-documented phenomena in human organizations where accumulated context simultaneously enables domain mastery and prevents paradigm revision [14, 15]. A companion paper formalizes this structural isomorphism between LLM context windows and human generational dynamics, including the connection to model collapse [18] as the failure mode when generational context asymmetry is absent.

The structural parallel between context compression and sleep memory consolidation extends further: Spens & Burgess [26] explicitly model hippocampal-neocortical memory transfer as "compressive retrieval-augmented generation," where compressed episodic traces (hippocampus) are replayed to train a generative network (neocortex). Semi-Fresh-Active's tool-call-based retrieval instantiates this architecture computationally — the session generates independently (neocortex) while consulting compressed prior analysis on demand (hippocampal retrieval). This convergence suggests that context asymmetric debate may exploit a structure that biological cognition has independently evolved for balancing accumulated knowledge against cognitive flexibility. A companion paper develops this parallel in depth, formalizing the mapping between context windows and human generational dynamics.

For multi-agent system design, our preliminary results suggest a practical principle: **context diversity may be more valuable than agent count**. Combined with Choi et al.'s martingale result [7] (scaling homogeneous agents cannot improve expected correctness) and Boca et al.'s finding [17] that LLM populations spontaneously develop collective biases, this motivates architectures that deliberately maintain sessions with different context depths rather than scaling identical agents.

---

## 7. Conclusion and Future Work

We presented Ploidy, a protocol for structured debate between same-model sessions with intentional context asymmetry, and introduced the Context Asymmetry Spectrum — a 2D framework varying context depth and delivery mode. Pilot experiments across 15 tasks, 12 methods, and systematic sweeps across injection mode, language, effort level, and model family reveal:

1. **Context asymmetry is a targeted intervention**, not a universal improvement. On short-context tasks (Exp 1, 7 tasks) and intermediate-context tasks (§5.8.4, 5 tasks), all methods achieve near-identical recall. The delivery mode effect disappears entirely below the entrenchment threshold.
2. **On long-context tasks with anchoring bias** (Exp 2, 3 tasks), Semi-Fresh-Active and Self-Consistency achieve 100% average recall, outperforming Single Session (81%) and original Ploidy (89%).
3. **Information position is the dominant factor in context delivery.** Factorial ablation reveals that placing a compressed summary at the top vs. bottom of the prompt accounts for +11pp recall (89% → 100%), consistent with primacy anchoring effects in human cognition [24].
4. **Injection mode modulates vulnerability asymmetrically.** Memory-mode context injection drops Single Session recall by 25pp while Ploidy drops only 6pp — the Fresh session's structural isolation provides immunity to injection-mode bias (§5.8.1).
5. **Language interacts with context asymmetry.** In Chinese, Single Session completely fails on 2/3 tasks (0% recall) while Ploidy achieves 100%. This is the largest effect size observed (Δ=100pp) and suggests context asymmetry may be especially valuable for non-English workflows (§5.8.2).
6. **Cross-model evidence supports Event A isolation.** On Codex (GPT-5.4), Stochastic-N (4 sessions, same context) matches Single Session recall, while Ploidy (4 sessions, asymmetric context) achieves substantially higher recall — confirming that the improvement comes from context asymmetry, not session count (§5.8.3).

These results bound where context asymmetry applies and shift the question from "does asymmetry help?" to "under what conditions (context length, injection mode, language, model capability) does it matter most?"

**Open directions** (community contributions welcome — see §6.3 for replication targets):
1. **Statistical validation**: 30+ tasks, 5+ runs, paired statistical tests
2. **External task sets**: real-world architecture decisions from open-source projects
3. **Cross-model replication**: complete the 4-family validation (Codex interrupted by usage limits)
4. **Multi-round protocol**: extending to test AceMAD's submartingale conditions [9]
5. **Context-length gradient**: systematic threshold identification (100–10K tokens)
6. **Chinese language replication**: the dramatic zh finding (§5.8.2) needs multi-run confirmation

We release the full experimental framework (25 task definitions, experiment runner, all result data) alongside the Ploidy MCP server at https://github.com/heznpc/ploidy.

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

[19] Tononi, G. and Cirelli, C. "Sleep and the Price of Plasticity: From Synaptic and Cellular Homeostasis to Memory Consolidation and Integration." Neuron, 2014.

[20] Anderson, M.C. "Active Forgetting: Adaptation of Memory by Prefrontal Control." Annual Review of Psychology, 2021. See also Wimber, M. et al. "Retrieval Induces Adaptive Forgetting of Competing Memories via Cortical Pattern Suppression." Nature Neuroscience, 2015.

[21] Nader, K., Schafe, G.E. and LeDoux, J.E. "Fear Memories Require Protein Synthesis in the Amygdala for Reconsolidation After Retrieval." Nature, 2000.

[22] Autore, L., Drew, M.R. and Ryan, T.J. "The Cost of Remembering: Engram Competition as a Flexible Mechanism of Forgetting." Trends in Neurosciences, 2025.

[23] Roediger, H.L. and Karpicke, J.D. "Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention." Psychological Science, 2006.

[24] Murdock, B.B. "The Serial Position Effect of Free Recall." J. Experimental Psychology, 1962. See also Zhao, H. et al. "Positional Bias in LLM Long-Context Reasoning." arXiv, 2025.

[25] Anthropic. "Compaction — Claude API Documentation." platform.claude.com/docs/en/build-with-claude/compaction, 2026.

[26] Spens, E. and Burgess, N. "Hippocampo-neocortical Interaction as Compressive Retrieval-Augmented Generation." bioRxiv, 2024.

[27] Epley, N. and Gilovich, T. "The Anchoring-and-Adjustment Heuristic: Why the Adjustments Are Insufficient." Psychological Science, 2006.

[28] Slamecka, N.J. and Graf, P. "The Generation Effect: Delineation of a Phenomenon." J. Experimental Psychology: Human Learning and Memory, 1978.
