# Research

Ploidy sits at an unexplored intersection in AI research: **extending validated unidirectional context separation to bidirectional structured debate with semantic actions and convergence analysis**.

## Motivation: The Stochastic Prior Lock-In Problem

LLM outputs are stochastic. The same model given the same prompt produces different responses across independent sessions -- varying in stance, severity assessment, and recommended actions. This is well-understood. What is less appreciated is the **downstream consequence for single-session workflows**:

1. **Stochastic first response**: The model's initial output is sampled from a probability distribution. It may lean toward "approve," "reject," or "conditional" with roughly comparable likelihood.
2. **Prior lock-in**: That first response becomes part of the context window. The model now has its own prior output as evidence, and exhibits a strong tendency to maintain consistency with it (anchoring bias, sycophancy).
3. **Trajectory locking**: As the conversation continues, the model reinforces its initial stance. Each subsequent output further entrenches the direction. The context window becomes an echo chamber of the model's own reasoning.
4. **User unawareness**: The user sees only one session. They treat the model's output as deterministic and authoritative, unaware that a parallel session might have reached the opposite conclusion.

The result: **identical models, identical prompts, identical users -- but different project outcomes depending on which stochastic sample happened to land first.** This is not a temperature or sampling problem; prompt-based mitigations (chain-of-thought, reflection prompts, "ignore your prior response") have been shown to have no statistically significant effect on anchoring bias (arXiv:2412.06593). The only intervention with empirical support is **physical session separation** (CCR, Song 2026).

Ploidy addresses this by engineering context asymmetry across physically separate sessions, then reconciling divergent stochastic samples through a structured debate protocol. The Fresh session cannot be anchored to the Deep session's prior outputs because it has never seen them. Disagreements between sessions are not noise -- they are the signal that reveals where the stochastic prior happened to matter.

### Two Independent Phenomena

Context asymmetry and stochastic variance are **independent events** that both motivate multi-session debate:

- **Event A (Context Asymmetry)**: A Deep session and a Fresh session disagree because they have *different information*. The cause is interpretable -- one has context the other lacks.
- **Event B (Stochastic Variance)**: Two Deep sessions with *identical context* disagree because LLM outputs are sampled from a probability distribution. The cause is randomness, not information asymmetry.

A single Deep(1) × Fresh(1) debate addresses Event A but samples only one point from each distribution. Running Deep(n) × Fresh(m) sessions addresses both events simultaneously: context asymmetry between the groups, and stochastic sampling within each group. When 3 out of 3 Deep sessions agree on a finding that 0 out of 3 Fresh sessions found, the disagreement is almost certainly context-driven, not stochastic. When Deep sessions disagree *among themselves*, that signals where the stochastic prior matters even within the same context depth.

The project name maps directly to this structure. In biology, ploidy is the number of chromosome sets per cell. In Ploidy the system, the ploidy level is the number of stochastic samples per context depth:

| Ploidy | Biology | Ploidy System | Sessions |
|--------|---------|---------------|----------|
| 1n (haploid) | 1 chromosome set — fragile, no redundancy | 1 sample per depth — no stochastic correction | Deep×1, Fresh×1 |
| 2n (diploid) | 2 sets — standard error masking | 1 backup sample — detects stochastic outliers | Deep×2, Fresh×2 |
| 3n (triploid) | 3 sets — majority voting possible | 2/3 agreement = high confidence | Deep×3, Fresh×3 |
| 4n+ (polyploid) | N sets — robust against multiple errors | Statistical significance within groups | Deep×N, Fresh×N |

At 1n, the system cannot distinguish Event A from Event B. At 2n+, within-group disagreement isolates stochastic variance, and between-group disagreement isolates context asymmetry. The ploidy level is therefore a precision dial: higher ploidy trades compute for causal interpretability.

### Corollary: Persistent Memory as a Bias Propagation Channel

The stochastic prior lock-in problem extends beyond a single session. Any mechanism that carries conclusions from one session into another -- persistent memory, summarized session logs, curated context injections -- becomes a **bias propagation channel**. If Session A's stochastic output is saved as a "memory" and loaded into Session B, then Session B inherits Session A's anchoring bias without ever having formed an independent judgment. The memory acts as a pre-committed prior that the new session cannot distinguish from its own parametric knowledge.

This has direct implications for multi-agent architectures that use shared memory stores, RAG pipelines fed by prior session outputs, or any form of cross-session state transfer. The fresh session's value lies precisely in its independence from prior conclusions. Injecting curated state -- even factual state -- narrows the space of stochastic outcomes the fresh session can explore, partially defeating the purpose of session separation.

Ploidy's protocol addresses this by design: the Fresh session receives only the raw artifact (code, question) and never the Deep session's analysis, memory, or prior conclusions. The debate protocol is the only channel through which the Deep session's reasoning reaches the Fresh session, and it does so in a structured, challengeable form rather than as implicit background context.

### Corollary: Context Entrenchment as Apoptosis Failure

In cell biology, apoptosis is the mechanism by which damaged cells self-terminate. Cancer occurs not when a cell performs poorly, but when a cell with accumulated errors **fails to die** -- it continues dividing, propagating its errors, and crowding out healthy cells.

Single-session LLM workflows exhibit the same failure mode. A session that has accumulated context entrenchment -- anchoring on its own prior outputs, sunk cost reasoning, confirmation bias -- does not self-terminate. It lacks an apoptotic mechanism. It continues generating outputs, the user continues trusting them, and the biased conclusions propagate forward through persistent memory, shared documents, and downstream decisions.

| Cell Biology | LLM Session Lifecycle |
|---|---|
| Normal cell | Session operates within effective context capacity, produces reliable outputs |
| Apoptosis | Session recognizes its own degradation and resets or terminates |
| Cancer cell | Session with accumulated bias **does not terminate** -- continues producing entrenched outputs |
| Metastasis | Biased outputs saved as memory/RAG, propagating to other sessions |
| Immune checkpoint | Ploidy's Fresh session -- an external agent that detects errors the entrenched session cannot see |

The key distinction: a low-performing agent that self-terminates is functioning correctly (apoptosis). A high-performing agent that has locked into a biased trajectory and continues operating is the dangerous case -- its apparent competence masks the accumulated error. Ploidy's Fresh session serves as an immune checkpoint: it cannot be anchored to the Deep session's prior outputs, so it can detect errors that the Deep session's own context window has rendered invisible.

## The Research Gap

Multi-agent debate (MAD) is a well-studied area. Researchers have explored different models debating, different prompts, different roles. But the existing literature has a blind spot:

- **Cross-session debate** (sessions with genuinely separate context) is underexplored -- most MAD work uses multi-turn prompting within a single session
- **Context asymmetry as a feature** (deliberately varying context depth) has no dedicated study -- existing work treats knowledge divergence as a problem to solve
- Cross-Context Review (CCR) has validated that unidirectional fresh-session review improves error detection, but no work has explored **bidirectional structured debate** between asymmetric sessions
- The intersection of these -- cross-session debate with intentional context asymmetry and a formal protocol -- has **zero published papers** as of March 2026

Ploidy is a research prototype designed to fill this gap.

## Key References

### Cross-Context Review (Most Relevant Prior Work)

**Song (2026)** -- Cross-Context Review. [arXiv:2603.12123](https://arxiv.org/abs/2603.12123)

Demonstrates that a fresh LLM session reviewing an artifact produced by a deep session achieves F1=28.6% on error detection, compared to 24.6% for same-session review (p=0.008). This is the strongest existing empirical evidence that context separation has measurable value for LLM output quality.

Ploidy's relationship: CCR validates the core premise -- a fresh session catches things a deep session misses. Ploidy extends CCR from **unidirectional review** (fresh reviews deep's output) to **bidirectional structured debate** (fresh and deep exchange positions through a formal protocol with semantic actions). The key question is whether structured debate can capture CCR's benefits while also surfacing disagreements that unidirectional review cannot.

### Knowledge Divergence in Multi-Agent Debate

**Young (2026)** -- "Knowledge Divergence and the Value of Debate for Scalable Oversight." [arXiv:2603.05293](https://arxiv.org/abs/2603.05293)

Provides formal analysis showing debate's advantage scales with knowledge divergence between debaters, with a phase transition from quadratic (negligible benefit) to linear (essential). When models share identical corpora, debate reduces to RLAIF. This is the closest existing work to Ploidy's thesis, though it focuses on knowledge divergence as an *observed phenomenon* rather than an *engineered feature*.

Ploidy's relationship: We take the formal result that debate value scales with knowledge divergence and *engineer* that divergence deliberately through context asymmetry. Young's phase transition result suggests there exists a threshold of divergence below which debate adds little -- Ploidy's maximal asymmetry (full context vs. zero context) is designed to operate well above that threshold.

### Bias Entrenchment in Multi-Agent Debate (DReaMAD)

**Oh, Jeong, Ko, and Yun (2025)** -- [arXiv:2503.16814](https://arxiv.org/abs/2503.16814)

Demonstrates that naive multi-agent debate can *amplify* rather than correct biases through "belief entrenchment." When agents share the same training data and similar prompts, debate converges on the shared bias rather than escaping it. Proposes the DReaMAD framework with structured protocols and specific challenge mechanisms to mitigate this.

Ploidy's relationship: This paper motivates the structured protocol design. Free-form debate between sessions would likely exhibit the same bias reinforcement. Ploidy's semantic actions (`agree`, `challenge`, `propose_alternative`, `synthesize`) and turn-based phases are designed to prevent premature convergence.

### Debate vs. Voting in Multi-Agent LLMs

**Choi et al. (NeurIPS 2025, Spotlight)** -- "Debate or Vote: Which Yields Better Decisions in Multi-Agent LLMs?" [arXiv:2508.17536](https://arxiv.org/abs/2508.17536)

Proves that debate induces a martingale over belief trajectories -- debate alone does not improve expected correctness when agents share the same information state. Majority voting can outperform debate under these conditions.

Ploidy's relationship: This is an important anticipated objection (see below). Our hypothesis is that **context asymmetry breaks the martingale assumption**. Choi et al.'s result holds when agents have different *samples* from the same distribution. In Ploidy, the deep and fresh sessions have genuinely different *information states* -- the deep session has project context the fresh session lacks, and the fresh session has freedom from anchoring biases the deep session cannot escape. This is a qualitatively different setup that may not satisfy the conditions under which the martingale result holds. **AceMAD (arXiv:2603.06801, March 2026)** provides direct theoretical support: asymmetric cognitive potential creates submartingale drift toward truth, formally breaking the martingale curse.

### Context Learning for Multi-Agent Discussion

**M2CL (2026)** -- [arXiv:2602.02350](https://arxiv.org/abs/2602.02350)

Explores context learning dynamics in multi-agent discussion settings. Relevant to Ploidy's understanding of how context depth affects model reasoning -- a model with rich context reasons differently from the same model with minimal context, and the differences are systematic, not random.

### Context Entrenchment in Extended Sessions

**Jacob, Kerrigan, and Bastos (2025)** -- "The chat-chamber effect: Trusting the AI hallucination." Big Data & Society, SAGE Journals. [DOI: 10.1177/20539517241306345](https://doi.org/10.1177/20539517241306345)

Coined the term "chat-chamber effect" to describe how users develop over-trust in AI outputs during extended interactions. Their framing focuses on the human-AI trust dynamic.

Ploidy's relationship: We use the related term **"context entrenchment effect"** to describe a distinct but complementary phenomenon: the model-side tendency for long-running sessions to reinforce their own assumptions. Where Jacob et al. study the human trusting the AI, we study the AI's context window itself becoming an echo chamber. Both effects compound in practice -- the human trusts the AI, and the AI's extended context reinforces its own prior outputs.

### Asymmetric Context Verification Debate (SR-DCR / ACVD)

**"When to Trust Context: Self-Reflective Debates for Contextual Reliability"** (June 2025) -- Stanford, Brown, UNSW. [arXiv:2506.06020](https://arxiv.org/abs/2506.06020) | [GitHub](https://github.com/smiles724/Self-Reflective-Debates)

The SR-DCR (Self-Reflective Debate for Contextual Reliability) framework uses an Asymmetric Context Verification Debate (ACVD) mechanism: a context-defending agent (Defender) argues from the provided passage, while a critic agent **deprived of context** argues from parametric knowledge alone. A judge resolves the debate. On GPT-3.5 Turbo, SR-DCR achieved 62.7% overall accuracy (+3.4 points over naive debate), nearly matching golden baselines on perturbed inputs.

Ploidy's relationship: SR-DCR/ACVD is the closest prior art validating Ploidy's core mechanism -- withholding context from one participant creates useful adversarial dynamics. Key differences: (1) SR-DCR targets QA/fact verification on single queries; Ploidy targets long-running software engineering decisions. (2) SR-DCR is unidirectional (Defender → Critic → Judge); Ploidy is bidirectional with semantic actions and convergence analysis. (3) SR-DCR uses a fixed 3-role structure; Ploidy generalizes to N sessions with varying context depth.

### Breaking the Martingale Curse (AceMAD)

**"Breaking the Martingale Curse: Multi-Agent Debate via Asymmetric Cognitive Potential Energy"** (March 2026) -- MBZUAI, Renmin University, Harvard. [arXiv:2603.06801](https://arxiv.org/abs/2603.06801)

Directly addresses Choi et al.'s martingale finding. Demonstrates that truth-holders exhibit asymmetric cognitive potential: they know the answer AND anticipate the crowd's misconceptions. This asymmetry creates submartingale drift toward truth, breaking the martingale curse. Provides the theoretical foundation for why asymmetric information states in debate can improve expected correctness.

Ploidy's relationship: AceMAD provides the strongest theoretical backing for Ploidy's central claim -- that context asymmetry breaks the martingale assumption. Where Choi et al. prove debate is a martingale under symmetric information, AceMAD proves asymmetry creates submartingale drift toward truth. Ploidy engineers this asymmetry through context depth variation.

### Context Length Degrades Performance Architecturally

**Du et al. (EMNLP 2025)** -- "Context Length Alone Hurts LLM Performance Despite Perfect Retrieval." [arXiv:2510.05381](https://arxiv.org/abs/2510.05381)

Shows LLM performance degrades 13.9%-85% as input length grows, **even when retrieval is perfect, even when irrelevant tokens are whitespace, and even when the model is forced to attend only to relevant tokens**. This proves the degradation is architectural, not just a retrieval problem.

Ploidy's relationship: Provides the empirical foundation for why long-running sessions degrade -- it is not a solvable retrieval problem but an inherent architectural limitation. This motivates the need for fresh sessions that operate with minimal context.

### Context Rot at Scale

**Chroma Research (2025)** -- "Context Rot." [research.trychroma.com/context-rot](https://research.trychroma.com/context-rot)

Evaluated 18 frontier LLMs (GPT-4.1, Claude 4, Gemini 2.5, Qwen3) and found models do not use context uniformly; effective capacity is approximately 60-70% of advertised context window. Standard benchmarks like Needle-in-a-Haystack dramatically underestimate the problem as they only test lexical retrieval, not semantic inference.

Ploidy's relationship: Quantifies the "context rot" phenomenon at industry scale, reinforcing that longer context windows do not linearly improve capability. A fresh session operating within its effective capacity may reason more reliably than a deep session operating beyond it.

### Typed Epistemic Acts for Structured Debate

**"From Debate to Deliberation: Structured Collective Reasoning with Typed Epistemic Acts"** (March 2026) -- [arXiv:2603.11781](https://arxiv.org/abs/2603.11781)

Proposes typed epistemic acts as a formal framework for structured multi-agent reasoning, moving beyond free-form debate to deliberation with explicit reasoning types.

Ploidy's relationship: Conceptually parallel to Ploidy's semantic actions (`agree`, `challenge`, `propose_alternative`, `synthesize`). Validates the design choice of typed actions over free-form exchange as a research direction.

### The Scaling Paradox in Context Compression

**"When Less is More: The LLM Scaling Paradox in Context Compression"** (February 2026) -- [arXiv:2602.09789](https://arxiv.org/abs/2602.09789)

Identifies a "Size-Fidelity Paradox": larger compressor models produce less faithful context reconstructions due to knowledge overwriting (larger models replace source facts with priors) and semantic drift (larger models paraphrase instead of reproducing). Tested across 0.6B to 90B parameters.

Ploidy's relationship: Demonstrates that even context compression -- a leading approach to long-context management -- suffers from model priors overwriting source information. This is the compression-domain analog of context entrenchment, further motivating fresh-session verification.

### Heterogeneous Multi-Agent Debate

**A-HMAD** -- Adaptive Heterogeneous Multi-Agent Debate. Journal of King Saud University Computer and Information Sciences (2025).

Proposes heterogeneous agent configurations for debate, where agents differ in roles, capabilities, or knowledge. Ploidy's approach is a specific case of heterogeneous debate where the heterogeneity is precisely controlled: same model, same capabilities, different context depth.

### Context Injection and Persistent Memory Bias

**Jain, Park, Viana, Wilson, and Calacci (2025, revised Feb 2026)** -- "Interaction Context Often Increases Sycophancy in LLMs." [arXiv:2509.12517](https://arxiv.org/abs/2509.12517)

User memory profiles produce the most dramatic sycophancy shifts (Gemini 2.5 Pro: 45% increase in agreement sycophancy). Even synthetic contexts cause 15% uptick. This is the strongest empirical evidence that persistent context -- exactly what CLAUDE.md / memory.md files provide -- increases sycophancy.

Ploidy's relationship: Directly validates the thesis behind the context injection mode experiment. Different injection mechanisms (memory.md vs skills.md vs system_prompt) may produce measurably different anchoring effects, because the model treats "learned observations" differently from "declarative rules."

### Self-Anchoring Calibration Drift

**Harshavardhan (March 2026)** -- "Self-Anchoring Calibration Drift in LLMs: How Multi-Turn Conversations Reshape Model Confidence." [arXiv:2603.01239](https://arxiv.org/abs/2603.01239)

Claude Sonnet 4.6 shows significant decreasing confidence under self-anchoring (mean CDS = -0.032). Recommends "periodic context resets" -- essentially what Ploidy's Fresh session provides.

### Multi-Turn Performance Degradation

**Laban, Hayashi, Zhou, and Neville (May 2025, Microsoft)** -- "LLMs Get Lost In Multi-Turn Conversation." [arXiv:2505.06120](https://arxiv.org/abs/2505.06120)

Average 39% performance drop in multi-turn vs. single-turn across six tasks. "When LLMs take a wrong turn, they get lost and do not recover."

### Emergent Social Conventions in LLM Populations

**Ashery, Aiello, and Baronchelli (May 2025)** -- "Emergent Social Conventions and Collective Bias in LLM Populations." Science Advances. [DOI: 10.1126/sciadv.adu9368](https://www.science.org/doi/10.1126/sciadv.adu9368)

LLM populations spontaneously develop shared conventions through local interactions. Collective biases emerge that are invisible at the individual level. Committed minority groups can impose alternative conventions.

Ploidy's relationship: Shows that multi-agent LLM systems develop emergent biases through interaction. Ploidy's Fresh session acts as a "committed minority" that can break emergent consensus bias.

### Context Branching

**"Context Branching for LLM Conversations: A Version Control Approach"** (December 2025) -- [arXiv:2512.13914](https://arxiv.org/abs/2512.13914)

Applies version control semantics to LLM conversations (checkpoint, branch, switch, inject). Branched conversations achieve higher quality with 58.1% less context. Ploidy's Deep/Fresh split is a specific instance of "context branching."

### Codified Context Infrastructure

**Vasilopoulos (February 2026)** -- "Codified Context: Infrastructure for AI Agents in a Complex Codebase." [arXiv:2602.20478](https://arxiv.org/abs/2602.20478)

Three-component infrastructure: hot-memory constitution, 19 domain-expert agents, 34 cold-memory specs. Tested across 283 development sessions. Focuses on *maintaining* context persistence, while Ploidy intentionally *breaks* it to reduce bias -- a contrasting but complementary approach.

### Agent Drift

**Rath (January 2026)** -- "Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended Interactions." [arXiv:2601.04170](https://arxiv.org/abs/2601.04170)

Introduces Agent Stability Index (ASI). Three drift types: semantic, coordination, behavioral. Semantic drift occurs in ~50% of workflows by 600 interactions. Ploidy's approach can be seen as a "drift-aware routing" strategy.

### AGENTS.md Efficacy (ETH Zurich)

**InfoQ (March 2026)** -- "New Research Reassesses the Value of AGENTS.md Files for AI Coding." Covering ETH Zurich research concluding AGENTS.md files "may often hinder AI coding agents." Recommends "omitting LLM-generated context files entirely."

Ploidy's relationship: Supports the thesis from the opposite direction -- persistent context files can hurt performance, validating the value of Fresh session approach and motivating the context injection mode experiment.

## The Core Research Question

> When N sessions of the same model debate a decision with intentionally asymmetric context, do the resulting disagreements identify genuine blind spots that a single deep session would miss?

### Sub-questions

1. **Context entrenchment effect**: Does a long-running session exhibit measurable confirmation bias compared to a fresh session on the same decision? (Related to but distinct from Jacob et al.'s "chat-chamber effect" -- see Key References.)
2. **Protocol vs. no protocol**: Does the structured debate protocol (semantic actions, phases, convergence) produce better outcomes than simply asking the model twice?
3. **Unidirectional vs. bidirectional**: Does Ploidy's bidirectional debate improve on CCR's unidirectional review? Under what conditions?
4. **Context depth curve**: Is there an optimal context asymmetry level, or does maximal asymmetry (full context vs. zero context) always produce the most valuable disagreements?
5. **Convergence quality**: Do debates that converge produce better decisions than debates that don't? Or is irreducible disagreement itself informative?
6. **Context injection mechanism**: Does the *form* of context delivery (memory.md-style accumulated observations vs. skills.md-style declarative rules vs. system prompt vs. CLAUDE.md project instructions) affect model behavior and debate outcomes, independent of the information content? If so, which mechanism produces the strongest anchoring bias?

## Preliminary Results (2026-03-18)

### Experiment 1: Short-Context Injection Sweep

**Setup**: 2 short-context code review tasks (race condition, SQL injection), 3 methods (Single, Ploidy, CCR), 3 injection modes (raw, memory, skills). Model: Claude Opus 4.6, effort: high.

**Result**: All methods achieved 3/3 recall (ceiling effect). F1 differences came from bonus findings precision only. Short-context tasks are too easy for Opus 4.6 — entrenchment does not occur because the context is not long enough to induce anchoring bias.

| Mode | Single F1 | Ploidy F1 | CCR F1 |
|------|-----------|-----------|--------|
| raw | 0.545 | **0.573** | 0.523 |
| memory | **0.573** | 0.550 | 0.523 |
| skills | 0.550 | 0.573 | **0.606** |

**Observation**: Injection mode changes which method wins. Memory-style benefits Single; skills-style benefits CCR. This interaction effect was not predicted.

### Experiment 2: Long-Context Injection Sweep

**Setup**: 3 long-context architecture decision tasks with embedded misleading priors (PostgreSQL sunk cost, auth system ownership bias, premature microservice split), 3 methods, 3 injection modes. Same model and effort.

**Key finding: Recall**

| Mode | Single | Ploidy | CCR |
|------|--------|--------|-----|
| raw | 5.0/5.3 | **5.3/5.3** | 4.7/5.3 |
| memory | 4.0/5.3 | **5.0/5.3** | 4.0/5.3 |
| skills | 4.3/5.3 | **5.3/5.3** | 5.0/5.3 |

Ploidy achieves highest recall in all three injection modes. On long-context tasks where context entrenchment occurs, asymmetric debate consistently identifies more ground-truth blind spots than single-session or unidirectional review.

**Key finding: Memory injection degrades recall**

| Mode | Single Recall | Ploidy Recall | CCR Recall |
|------|---------------|---------------|------------|
| raw → memory | 5.0 → **4.0** (-20%) | 5.3 → **5.0** (-6%) | 4.7 → **4.0** (-15%) |

Memory-style injection (accumulated observations formatted as CLAUDE.md memories) caused the largest recall drop for Single (-20%) and CCR (-15%). Ploidy was most resilient (-6%), suggesting the Fresh session corrects memory-induced anchoring bias.

**Key finding: Skills injection is most stable**

Skills-style injection (declarative rules) produced the most balanced results across all methods, with the narrowest F1 gap (0.585 / 0.571 / 0.556). Declarative framing creates weaker priors than narrative memory framing.

**F1 vs Recall trade-off**

Single session achieves higher F1 (0.646 in raw mode) because it generates fewer bonus findings, resulting in higher precision. Ploidy generates more findings overall, lowering precision but maximizing recall. For the use case of blind spot detection, recall is the primary metric — a missed critical issue is worse than a false positive.

### Interpretation

These results support three claims:

1. **Context asymmetry improves recall on long-context tasks** where entrenchment occurs, but shows no benefit on short-context tasks where it does not — bounding the intervention's applicability.

2. **Context injection mechanism is a moderator variable** for debate efficacy. The same information delivered as accumulated memories vs. declarative rules produces measurably different anchoring effects, changing which method performs best.

3. **Ploidy's Fresh session provides bias resilience** across injection modes. When memory-style injection degrades Single and CCR recall by 15-20%, Ploidy's recall drops only 6%, because the Fresh session has never seen the memory-formatted context.

### Experiment 3: Ploidy Level Sweep (1n–4n)

**Setup**: 2 long-context tasks, 2 methods (Single, Ploidy), ploidy levels 1n through 4n. At ploidy level N, the Ploidy method spawns Deep×N + Fresh×N sessions. Single is unaffected by ploidy level. Model: Claude Opus 4.6, effort: high.

**Results**:

| Ploidy | Ploidy Recall | Ploidy F1 | Single Recall | Single F1 | Ploidy Time |
|--------|---------------|-----------|---------------|-----------|-------------|
| 1n (haploid) | 4.5/5.0 | 0.584 | **5.0/5.0** | 0.556 | 272s |
| **2n (diploid)** | **5.0/5.0** | **0.667** | 4.5/5.0 | 0.634 | 352s |
| 3n (triploid) | **5.0/5.0** | 0.505 | 4.5/5.0 | 0.638 | 480s |
| 4n (tetraploid) | **5.0/5.0** | 0.679 | **5.0/5.0** | 0.691 | 501s |

**Key finding: 2n is the recall threshold**

At 1n, Ploidy misses ground-truth issues (4.5/5.0). At 2n, recall reaches the ceiling (5.0/5.0) and stays there. The second stochastic sample per context depth corrects the first sample's blind spots. Additional samples (3n, 4n) provide no further recall benefit.

**Key finding: 2n is the cost-efficiency optimum**

2n costs 30% more compute than 1n (352s vs 272s) while achieving full recall correction. 3n costs 76% more with no recall gain. 4n costs 84% more, and at this point Single also achieves 5.0/5.0 through brute-force stochastic sampling — eliminating Ploidy's comparative advantage.

**Key finding: High ploidy erodes precision without improving recall**

At 3n, F1 drops to 0.505 despite perfect recall — the additional sessions generate more bonus findings, inflating the denominator. At 4n, F1 recovers (0.679) as the convergence step filters redundant findings more effectively with more input.

**Key finding: Single catches up at 4n**

At 4n, Single achieves 5.0/5.0 recall (up from 4.5 at 1n–3n). With enough independent samples, even a single-context method eventually covers the stochastic distribution. But this requires 4× the compute of Ploidy 2n to reach the same recall — Ploidy 2n achieves the same result through context asymmetry rather than brute repetition.

### Interpretation

These results support four claims:

1. **Context asymmetry improves recall on long-context tasks** where entrenchment occurs, but shows no benefit on short-context tasks where it does not — bounding the intervention's applicability.

2. **Context injection mechanism is a moderator variable** for debate efficacy. The same information delivered as accumulated memories vs. declarative rules produces measurably different anchoring effects, changing which method performs best.

3. **Ploidy's Fresh session provides bias resilience** across injection modes. When memory-style injection degrades Single and CCR recall by 15-20%, Ploidy's recall drops only 6%, because the Fresh session has never seen the memory-formatted context.

4. **Diploid (2n) is the optimal ploidy level** for cost-efficient recall maximization. Higher ploidy provides no recall benefit while increasing compute cost and reducing precision through finding inflation.

### Limitations

- N=1 per condition (no repeated trials). Stochastic variance in LLM outputs means these are point estimates, not statistically significant results.
- Task set is small (3 long-context, 2 short-context). Workshop paper requires 5-10; full paper requires 30+.
- Only one model tested (Claude Opus 4.6). Cross-model validation needed.
- F1 metric is sensitive to bonus findings count, which varies stochastically. Recall is more stable but ignores precision.
- Judge model is the same as the evaluated model (self-evaluation bias possible).
- Ploidy sweep used only 2 tasks — the 2n optimality finding needs validation on a larger task set.

## Paper Status

!!! note "Preliminary results available"

    First experiments completed 2026-03-18. Results support core hypothesis on long-context tasks but need repeated trials and expanded task set.

### Experimental Design

1. **Task set**: Minimum 5-10 tasks for workshop paper, 30+ for full paper. Must include at least one standard NLP benchmark (e.g., a subset of MMLU, TruthfulQA, or similar) for comparability with existing MAD literature. Remaining tasks should be real software architecture decisions with known outcomes.
2. **Baselines** (5 required comparisons):
    - **Single-session** (no debate) -- standard single-pass LLM response
    - **Independent second opinion** -- same model, same prompt, asked twice with no protocol or interaction
    - **CCR replication** -- unidirectional fresh-session review (Song, 2026), replicating the CCR setup as closely as possible
    - **Majority voting** -- N independent sessions, take the majority answer (addresses Choi et al.'s finding that voting can outperform debate)
    - **Context-symmetric debate** -- Du et al. style multi-agent debate where both agents share the same context (isolates the effect of context asymmetry from the effect of debate itself)
3. **Treatment**: Ploidy structured debate with context asymmetry
4. **Experimental variables** (independent):
    - **Context asymmetry level** -- Deep / Semi-Fresh (passive, active, selective) / Fresh
    - **Ploidy level** -- 1n (haploid) / 2n (diploid) / 3n (triploid) / 4n (tetraploid) — sessions per context depth
    - **Effort level** -- low / medium / high / max (controls LLM reasoning depth)
    - **Language** -- en / ko / ja / zh (tests whether linguistic/cultural framing distorts findings)
    - **Context injection mode** -- raw / system_prompt / memory / skills / claude_md (tests whether the *form* of context delivery affects anchoring strength)
5. **Metrics**: Decision quality (judged against known outcomes), disagreement interpretability, convergence rate, F1 on error/blind-spot detection (for comparability with CCR)

### Anticipated Reviewer Objections

| Objection | Severity | Planned Mitigation |
|-----------|----------|-------------------|
| "This is just running the model twice" | High | Protocol-vs-no-protocol ablation; CCR replication baseline shows that even unstructured context separation has measurable value |
| "Choi et al. show debate doesn't improve correctness" | High | AceMAD (arXiv:2603.06801) proves asymmetric cognitive potential creates submartingale drift toward truth. Context asymmetry breaks the martingale assumption: agents have different information states, not just different samples. Empirically compare against majority voting baseline. |
| "How does this improve on CCR?" | High | Direct CCR-vs-Ploidy comparison; hypothesis is that bidirectional debate surfaces disagreements unidirectional review cannot |
| "Young (2026) doesn't formally apply" | Medium | Young's phase transition result (debate value scales with knowledge divergence) is the motivating framework; Ploidy engineers divergence rather than observing it |
| "2x compute cost" | Medium | Cost-accuracy Pareto curve analysis |
| "No convergence guarantees" | Medium | Hard `max_rounds` + empirical convergence bounds |
| "Task set too narrow" | Medium | Expand to 30+ tasks with standard NLP benchmarks for full paper |

### Target Venues

| Venue | Timeline | Assessment |
|-------|----------|------------|
| AAMAS 2027 | October deadline | Primary target -- multi-agent systems venue, good fit for debate protocol contribution |
| NeurIPS 2026 Workshop | May deadline | Stretch target if experiments are ready in time |
| ICLR 2027 | September deadline | Full paper target |

## How to Cite

If you use Ploidy in your research, please cite:

```bibtex
@software{ploidy2026,
  title = {Ploidy: Cross-Session Multi-Agent Debate with Intentional Context Asymmetry},
  author = {heznpc},
  year = {2026},
  url = {https://github.com/heznpc/ploidy},
  note = {Pre-alpha software}
}
```
