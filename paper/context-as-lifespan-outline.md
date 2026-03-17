# Context as Lifespan: Generational Innovation through Context-Asymmetric LLM Populations

> Draft outline — 2026-03-17
> Target: AAAI 2027 (AI & Society track) or Computational Social Science
> Format: 8 pages + references

---

## Abstract (Draft)

LLM 에이전트 시뮬레이션은 수만~수십만 에이전트를 생성하여 사회적 현상을 재현하지만,
개별 에이전트의 context 축적이 의사결정 편향을 유발한다는 구조적 문제를 간과한다.
본 논문은 LLM의 context window를 인간의 "수명"에 대응시키는 프레이밍을 제안한다:
context 축적은 경험(지식)인 동시에 앵커링 편향(고착)의 원천이며,
새로운 세션(fresh context)은 세대 교체에 해당한다.
이 프레이밍은 Planck 원리 ("science advances one funeral at a time")의
computational analog를 제공하며, "에이전트 수를 늘리면 정확도가 올라간다"는
직관이 수학적으로 틀림(martingale, Choi et al. 2025)을 사회학적 맥락에서 재해석한다.
Context length gradient 실험과 세대 교체 시뮬레이션을 통해,
context 비대칭의 구조화된 충돌이 동질적 에이전트 확장보다
의사결정 품질을 유의미하게 개선함을 보인다.

---

## 1. Introduction

### 1.1 The Paradox of Accumulated Context

인간 문명의 진보는 지식의 축적 위에 세워진다. 그러나 동시에,
축적된 지식이 혁신을 저해한다는 역설이 반복적으로 관찰된다:

- **Kuhn (1962)**: 정상과학의 패러다임이 이상현상을 무시 → 패러다임 전환은
  기존 과학자가 설득되어서가 아니라 세대가 교체되어서 발생
- **Planck**: "새로운 과학적 진리는 반대자를 설득해서가 아니라,
  반대자가 죽고 새 세대가 익숙해져서 승리한다"
- **Azoulay et al. (AER, 2019)**: 저명 과학자 사망 후 해당 분야
  신규 진입자 증가, 새 방향의 논문 통계적 유의미 증가 — 실증적 확인
- **Christensen (1997)**: Innovator's Dilemma — 기존 기업이 "합리적으로"
  파괴적 혁신을 놓치는 것은 축적된 의사결정 컨텍스트 자체가 편향

### 1.2 The LLM as Controllable Analog

LLM의 context window는 이 현상의 최초의 통제 가능한 실험 환경이다:

| 인간 | LLM |
|------|-----|
| 동일한 종 (Homo sapiens) | 동일한 모델 (e.g., Claude Opus 4.6) |
| 지능 ≈ 세대 내 유사 | Model version = 고정 |
| 수명 = 경험 축적 기간 | Context window = 정보 축적 범위 |
| 경험 = 편향의 원천 | Context = anchoring bias의 원천 |
| 세대 교체 (~25년) | 새 세션 생성 (~즉시) |
| 패러다임 전환 = 세대 간 충돌 | Convergence = 비대칭 디베이트 |

핵심 차이: 인류는 세대 교체에 25년이 걸리지만,
LLM은 새 세션을 **즉시** 생성할 수 있다.
그리고 "세대 간 충돌"을 구조화된 프로토콜로 **통제**할 수 있다.

### 1.3 The Scaling Illusion

현재의 에이전트 시뮬레이션(MiroFish 70만, AgentSociety 1만)은
에이전트 수를 늘려 예측 정확도를 높이려 한다.
그러나 Choi et al. (NeurIPS 2025)은 대칭 정보 하의 토론이
martingale을 유도함을 증명했다 — 기대값이 개선되지 않는다.

이것은 "1000명의 전문가 합의 = 진실"이라는 직관이
수학적으로 틀렸음을 의미한다.
모든 에이전트가 같은 context(= 같은 편향)를 공유하면,
수를 늘리는 것은 편향된 샘플을 스케일링할 뿐이다.

**우리의 주장**: 에이전트 수(verification breadth)가 아니라
context 비대칭(verification depth)이 의사결정 품질의 핵심 변수이다.

---

## 2. Related Work

### 2.1 LLM Agent Social Simulations
- AgentSociety (2025): 10K agents, 5M interactions — 관찰 중심
- Generative Agents / Smallville (Park et al., 2023): 25 agents, 생활 시뮬레이션
- MiroFish (2026): 700K agents, "predict anything" — 검증 미비

**공통 한계**: 개별 에이전트의 context 축적이 편향을 유발한다는 점을 다루지 않음.
에이전트가 "경험"을 쌓을수록 더 편향될 수 있다는 역설이 무시됨.

### 2.2 Emergent Collective Bias
- Boca et al. (Science Advances, 2025): LLM 집단에서 개인 수준 편향 없이도
  집단 편향이 출현. Committed minority가 사회 변화를 주도 가능.
- Echo chamber / information cocoon effects in agent populations

### 2.3 Context Degradation and Anchoring
- Du et al. (EMNLP 2025): Context length가 성능을 떨어뜨림 (아키텍처 문제)
- Chroma (2025): 유효 context 용량 = 광고의 60-70%
- Feng et al. (2026): Prompt 기반 anchoring bias 완화는 통계적으로 무효

### 2.4 Asymmetric Context as Mechanism
- CCR (Song, 2026): Fresh session review, F1=28.6% vs 24.6%
- AceMAD (Liu et al., 2026): 비대칭 인지 잠재력 → submartingale 증명
- SR-DCR (2025): Asymmetric context verification debate

### 2.5 Planck Principle and Generational Dynamics
- Kuhn (1962): Structure of Scientific Revolutions
- Azoulay et al. (AER, 2019): Empirical validation of Planck's principle
- Christensen (1997): Innovator's Dilemma
- **Gap**: 이 현상의 computational simulation이 부재

---

## 3. Framework: Context as Lifespan

### 3.1 The Analogy Formalized

**Definition 1 (Context Lifespan).**
에이전트 a의 context lifespan L(a)는 세션 시작부터 현재까지
축적된 context의 총 토큰 수로 정의한다.

**Definition 2 (Context Entrenchment).**
Context entrenchment E(a, L)은 에이전트 a가 lifespan L에서
자신의 초기 stochastic sample과 일치하는 응답을 생성할 확률이다.
E가 높을수록 에이전트는 자신의 "prior"에 고착되어 있다.

**Hypothesis 1 (Entrenchment Monotonicity).**
E(a, L)은 L에 대해 단조 증가한다. 즉, context가 길어질수록
에이전트는 더 강하게 자신의 초기 판단에 고착된다.

**Hypothesis 2 (Asymmetric Advantage).**
Context lifespan이 다른 두 에이전트 a_deep (L = L_max)과
a_fresh (L = 0)의 구조화된 디베이트는,
동일 lifespan의 두 에이전트(L = L_max)의 디베이트보다
의사결정 품질을 유의미하게 개선한다.
단, L_max가 entrenchment threshold T_e를 초과할 때에만.

**Hypothesis 3 (Generational Innovation).**
N 세대에 걸쳐 context를 누적하는 에이전트 집단에서,
주기적으로 fresh agent를 도입하여 구조화된 충돌을 시키는 전략이
동질적 집단(fresh 도입 없음)보다 장기 의사결정 품질이 높다.

### 3.2 Where the Analogy Holds

- **Anchoring bias**: 인간과 LLM 모두에서 실증적으로 확인됨
- **Consistency-seeking**: 인간의 인지 부조화 회피 ≈ LLM의 sycophancy
- **Fresh eyes advantage**: 인간의 외부 컨설턴트 효과 ≈ Fresh session의 효과
- **Generational succession**: 경험적으로 확인된 Planck 원리 ≈ Session 교체

### 3.3 Where the Analogy Breaks

- LLM의 "fresh"는 문자 그대로 제로 컨텍스트. 인간의 "새 세대"는
  다른 도메인/문화의 지식을 가져옴.
- 인간의 세대 교체는 비가역적(사망). LLM은 Deep session을 유지하면서
  Fresh를 추가할 수 있음 → 비파괴적 세대 교체.
- 인간의 패러다임 전환은 조직적/정치적 요인 포함.
  LLM은 순수하게 정보 처리 수준의 현상.

### 3.4 The Scaling Critique

MiroFish 류의 대규모 시뮬레이션에 대한 체계적 비판:

**Theorem (Choi et al., 2025)**: 대칭 정보 하의 debate는
martingale → E[correctness after debate] = E[correctness before debate].

**Corollary**: 70만 에이전트가 모두 같은 context를 공유하면,
70만 번 투표하는 것과 수학적으로 동등하다.
이것은 individual bias를 줄이지 않는다.

**Our claim**: Martingale을 깨려면 비대칭이 필요하다 (AceMAD).
에이전트 수를 늘리는 것이 아니라, context diversity를 도입해야 한다.

---

## 4. Experiments

### 4.1 Experiment 1: Entrenchment Monotonicity

**목적**: Hypothesis 1 검증 — context 길이에 따른 entrenchment 증가 곡선

**설계**:
- 고정 태스크 (architecture decision with known best practice)
- Context length 변수: 0, 500, 1K, 2K, 5K, 10K, 20K tokens
- 각 길이에서 동일 태스크를 N=20회 실행
- 측정: 초기 응답과의 일관성 비율, ground truth 이탈 확률

**기대 결과**: S-curve — 짧은 context에서는 entrenchment 낮음,
threshold 이후 급격히 증가, 포화.

### 4.2 Experiment 2: Asymmetric vs Symmetric

**목적**: Hypothesis 2 검증 — context 비대칭 디베이트 vs 대칭 디베이트

**설계** (Ploidy 실험 확장):
- 30+ tasks, 각 5회 반복
- Methods: Single, Symmetric Debate, Asymmetric Debate (Ploidy)
- Context length를 체계적으로 변화 (2×2: short/long × bias/neutral)
- 통계 검정: Wilcoxon signed-rank, bootstrap CI

**공유**: 이 실험은 Ploidy 논문 (Paper 2)의 확장 실험과 동일 데이터 사용.

### 4.3 Experiment 3: Generational Simulation

**목적**: Hypothesis 3 검증 — 세대 교체의 장기 효과

**설계**:
- 10-round sequential decision task (각 라운드의 결정이 다음 라운드의 context에 누적)
- 조건 A: 동일 에이전트가 10 라운드 연속 수행 (context 누적)
- 조건 B: 5 라운드마다 fresh agent 도입 (세대 교체)
- 조건 C: 매 라운드 deep + fresh asymmetric debate (Ploidy)
- 측정: 라운드별 의사결정 품질, drift from ground truth, path dependency

**이것이 Paper 1의 독자적 기여**: Ploidy가 단일 의사결정을 다루는 반면,
이 실험은 **시간에 걸친 의사결정 품질의 변화**를 다룬다.

### 4.4 Experiment 4: Population-Level Dynamics

**목적**: 집단 수준에서 context diversity의 효과

**설계**:
- 10-agent population, 공유 의사결정 문제
- 조건 A: 모든 에이전트 동일 context (homogeneous)
- 조건 B: 에이전트별 context length 다양 (heterogeneous)
- 조건 C: 주기적 fresh agent 교체 (generational)
- 비교: MiroFish 스타일 (수 늘리기) vs Ploidy 스타일 (비대칭 충돌)

---

## 5. Expected Contributions

1. **Context as Lifespan 프레이밍**: LLM context window와 인간 수명의
   구조적 동형성을 최초로 형식화
2. **Entrenchment curve**: Context length에 따른 anchoring bias의
   정량적 프로파일 (threshold 식별)
3. **Generational innovation의 computational analog**: Planck 원리를
   통제된 실험 환경에서 재현
4. **Scaling critique**: "에이전트 수 = 정확도"라는 가정에 대한
   이론적 + 실험적 반론
5. **Design implications**: 에이전트 시스템 설계 시 context diversity가
   agent count보다 중요하다는 원칙

---

## 6. Discussion

### 6.1 Implications for Agent System Design

현재의 에이전트 시스템은 "더 많은 에이전트, 더 긴 컨텍스트"를 추구한다.
본 연구는 이 방향이 근본적으로 제한적임을 보인다:
- 더 긴 컨텍스트 = 더 강한 entrenchment
- 더 많은 동질 에이전트 = 편향의 스케일링

대안: **context diversity를 의도적으로 설계하라.**
Fresh perspective를 주기적으로 도입하는 것이
에이전트 수를 10배 늘리는 것보다 의사결정 품질에 기여한다.

### 6.2 Implications for Human Organizations

이 연구는 인간 조직에 대한 역사적 관찰을 재확인한다:
- 다양성이 동질적 전문성보다 혁신에 기여 (Page, 2007)
- 외부 영입이 내부 승진보다 패러다임 전환에 효과적 (Azoulay et al., 2019)
- "경험"과 "편향"은 동일 메커니즘의 양면

### 6.3 Limitations
- LLM의 context entrenchment ≠ 인간의 인지적 고착 (메커니즘 차이)
- 유추의 범위: "같은 구조" ≠ "같은 현상"
- 시뮬레이션 결과의 인간 사회 일반화 한계

---

## References (Preliminary)

- Kuhn, T. (1962). The Structure of Scientific Revolutions.
- Azoulay, P. et al. (2019). "Does Science Advance One Funeral at a Time?" AER.
- Christensen, C. (1997). The Innovator's Dilemma.
- Choi et al. (2025). "Debate or Vote." NeurIPS 2025 Spotlight.
- Liu et al. (2026). "AceMAD: Breaking the Martingale Curse." arXiv:2603.06801.
- Song (2026). "Cross-Context Review." arXiv:2603.12123.
- Park et al. (2023). "Generative Agents." UIST.
- Boca et al. (2025). "Emergent Social Conventions." Science Advances.
- AgentSociety (2025). arXiv:2502.08691.
- Du et al. (2025). "Context Length Alone Hurts." EMNLP.
- Feng et al. (2026). "Anchoring Bias in LLMs."
- Page, S. (2007). The Difference: How the Power of Diversity Creates Better Groups.
