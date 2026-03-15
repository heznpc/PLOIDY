# Research

Ploidy sits at an unexplored intersection in AI research: **cross-session context asymmetry as a deliberate mechanism for better decision-making**.

## The Research Gap

Multi-agent debate (MAD) is a well-studied area. Researchers have explored different models debating, different prompts, different roles. But the existing literature has a blind spot:

- **Cross-session debate** (sessions with genuinely separate context) is underexplored -- most MAD work uses multi-turn prompting within a single session
- **Context asymmetry as a feature** (deliberately varying context depth) has no dedicated study -- existing work treats knowledge divergence as a problem to solve
- The intersection of these two -- cross-session debate with intentional context asymmetry -- has **zero published papers** as of March 2026

Ploidy is a research prototype designed to fill this gap.

## Key References

### Knowledge Divergence in Multi-Agent Debate

**Chen et al. (2026)** -- [arXiv:2603.05293](https://arxiv.org/abs/2603.05293)

Analyzes how knowledge asymmetry affects debate dynamics between LLM agents. Finds that agents with different knowledge bases produce qualitatively different debate patterns than agents with shared knowledge. This is the closest existing work to Ploidy's thesis, though it focuses on knowledge divergence as an *observed phenomenon* rather than an *engineered feature*.

Ploidy's relationship: We take the observation that knowledge divergence produces different debate dynamics and invert it -- deliberately engineering context asymmetry to produce interpretable disagreements.

### Bias Reinforcement in Multi-Agent Debate

**Li et al. (2025)** -- [arXiv:2503.16814](https://arxiv.org/abs/2503.16814)

Demonstrates that naive multi-agent debate can *amplify* rather than correct biases. When agents share the same training data and similar prompts, debate converges on the shared bias rather than escaping it. Structured protocols with specific roles and challenge mechanisms mitigate this.

Ploidy's relationship: This paper motivates the structured protocol design. Free-form debate between sessions would likely exhibit the same bias reinforcement. Ploidy's semantic actions (`agree`, `challenge`, `propose_alternative`, `synthesize`) and turn-based phases are designed to prevent premature convergence.

### Multi-Modal Context Learning

**M2CL (2026)** -- [arXiv:2602.02350](https://arxiv.org/abs/2602.02350)

Explores how models learn from context provided at different modalities and depths. Relevant to Ploidy's understanding of how context depth affects model reasoning -- a model with rich context reasons differently from the same model with minimal context, and the differences are systematic, not random.

### Heterogeneous Multi-Agent Debate

**A-HMAD** -- Adaptive Heterogeneous Multi-Agent Debate

Proposes heterogeneous agent configurations for debate, where agents differ in roles, capabilities, or knowledge. Ploidy's approach is a specific case of heterogeneous debate where the heterogeneity is precisely controlled: same model, same capabilities, different context depth.

## The Core Research Question

> When N sessions of the same model debate a decision with intentionally asymmetric context, do the resulting disagreements identify genuine blind spots that a single deep session would miss?

### Sub-questions

1. **Chat-chamber effect**: Does a long-running session exhibit measurable confirmation bias compared to a fresh session on the same decision?
2. **Protocol vs. no protocol**: Does the structured debate protocol (semantic actions, phases, convergence) produce better outcomes than simply asking the model twice?
3. **Context depth curve**: Is there an optimal context asymmetry level, or does maximal asymmetry (full context vs. zero context) always produce the most valuable disagreements?
4. **Convergence quality**: Do debates that converge produce better decisions than debates that don't? Or is irreducible disagreement itself informative?

## Paper Status

!!! note "Pre-experimental"

    No experiments have been run yet. The paper is in the design phase, focused on defining the experimental methodology and baselines.

### Experimental Design (Planned)

1. **Task set**: 3 real software architecture decisions with known outcomes
2. **Baseline**: "Independent second opinion" -- same model, same prompt, no debate protocol
3. **Treatment**: Ploidy structured debate with context asymmetry
4. **Metrics**: Decision quality (judged against known outcomes), disagreement interpretability, convergence rate

### Anticipated Reviewer Objections

| Objection | Severity | Planned Mitigation |
|-----------|----------|-------------------|
| "This is just running the model twice" | High | Protocol-vs-no-protocol ablation study |
| "Chen et al. doesn't formally apply" | High | Reframe as motivating analogy, not formal basis |
| "2x compute cost" | Medium | Cost-accuracy Pareto curve analysis |
| "No convergence guarantees" | Medium | Hard `max_rounds` + empirical convergence bounds |

### Target Venues

| Venue | Timeline | Assessment |
|-------|----------|------------|
| NeurIPS 2026 Workshop | May deadline | Recommended first target |
| ICLR 2027 | September deadline | Full paper target |
| AAMAS 2027 | October deadline | Alternative full paper venue |

## How to Cite

If you use Ploidy in your research, please cite:

```bibtex
@software{ploidy2026,
  title = {Ploidy: Cross-Session Multi-Agent Debate with Intentional Context Asymmetry},
  author = {ren},
  year = {2026},
  url = {https://github.com/heznpc/ploidy},
  note = {Pre-alpha software}
}
```
