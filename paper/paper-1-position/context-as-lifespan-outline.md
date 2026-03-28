# The Accumulation-Renewal Dilemma: Why Homogeneous Knowledge Degrades Intelligence and Only Asymmetric Renewal Restores It

> Draft outline — 2026-03-17, restructured 2026-03-22
> Target: AAAI 2027 (AI & Society track) / Computational Social Science / NeurIPS 2026
> Format: 8 pages + references

---

## Thesis

**Homogeneous accumulation degrades intelligence. Only asymmetric renewal restores it.**

---

## Abstract

모든 지능 시스템은 축적-갱신 딜레마(Accumulation-Renewal Dilemma)에 직면한다:
지식을 축적하면 역량이 증가하지만, 동시에 고착(entrenchment)이 발생하여
새로운 증거에 대한 반응성이 감소한다. 이 딜레마는 계통을 초월하여 반복된다 —
인간 개인의 확증 편향, 과학 패러다임의 고착(Kuhn, 1962),
면역계의 원죄 항원 고착(original antigenic sin),
유성생식에서 Muller's ratchet, 그리고 LLM의 context entrenchment.

각 시스템은 독립적으로 같은 해법에 수렴했다: **비대칭적 갱신**.
수면은 시냅스 부하를 선택적으로 해소하고(SHY, Tononi & Cirelli),
세대 교체는 고착된 패러다임을 자연 소멸시키며(Planck principle, Azoulay et al.),
유성생식은 유전적 다양성을 재조합으로 유지하고,
면역계는 나이브 B세포로 고착되지 않은 항체를 생성한다.

본 논문은 LLM의 context window가 이 딜레마의 최초의 통제 가능한 실험 환경임을 주장한다.
이 프레이밍 위에서 세 가지 실험적 관찰을 보고한다:
(1) 동질적 확장(같은 context의 N개 에이전트)은 의사결정을 개선하지 못하며,
종 다양성(cross-model debate)도 마찬가지로 실패한다.
(2) Context 비대칭(deep vs fresh)은 모델 다양성보다 의사결정 품질을 더 크게 개선한다.
(3) 비대칭의 방향이 결정적이다: 강한 모델이 deep + 약한 모델이 fresh일 때 최고 성능(93.9%),
역방향은 최악(60.0%). Fresh의 가치는 "무지"가 아니라 "편향 없음"이다.

우리는 이 결과를 **Principle of Least Context**로 정리한다:
에이전트에게는 과업 수행에 필요한 최소한의 context만 제공해야 한다.
추가 context는 역량이 아니라 편향의 원천이다.

---

## 1. Introduction

### 1.1 The Everyday Experience

프로그래머라면 이 경험을 알 것이다: 코드를 몇 시간째 고치다가 막히면,
이전 작업 과정을 메모에 남기고 **아예 새로 시작**한다.
새로 시작하면 풀리는 경우가 많다 — 축적된 시행착오 자체가 탐색 공간을 제약하기 때문이다.

이 경험은 더 큰 스케일에서도 반복된다.
경험 많은 기업이 매너리즘에서 벗어나지 못하는 사이,
혜성같이 등장한 인디 개발자가 생태계를 바꿔버린다 [Christensen, 1997].
**축적 자체가 편향의 원천이며, 갱신은 외부에서만 올 수 있다.**

### 1.2 The Paradox of Accumulated Context

인간 문명의 진보는 지식의 축적 위에 세워진다. 그러나 동시에,
축적된 지식이 혁신을 저해한다는 역설이 반복 관찰된다:

- **Kuhn (1962)**: 패러다임 전환은 기존 과학자가 설득되어서가 아니라 세대가 교체되어서 발생
- **Planck / Azoulay et al. (AER, 2019)**: 저명 과학자 사망 후 해당 분야에 새 방향 논문 통계적 유의미 증가
- **Christensen (1997)**: Innovator's Dilemma — 축적된 의사결정 컨텍스트 자체가 편향

### 1.3 Stochastic Branching: 사용자는 운에 맡기고 있다

동일 모델에 동일 질문을 던져도 매 세션마다 다른 답변이 나온다.
사용자가 하나의 세션에서만 대화를 이어가면
**첫 번째 응답의 확률적 샘플이 이후 전체 경로를 결정한다.**
동일 태스크의 수행시간, 심지어 수행 여부 자체가 첫 응답에 따라 갈린다.
Agent Teams도 이 문제를 구조적으로 해결하지 못한다 —
같은 context를 공유하는 에이전트 N개는 같은 편향 분포에서 N번 샘플링할 뿐이다.

### 1.4 The LLM as Controllable Analog

LLM의 context window는 이 현상의 최초의 통제 가능한 실험 환경이다:

| 인간 | LLM |
|------|-----|
| 동일한 종 (Homo sapiens) | 동일한 모델 |
| 수명 = 경험 축적 기간 | Context window = 정보 축적 범위 |
| 경험 = 편향의 원천 | Context = anchoring bias의 원천 |
| 세대 교체 (~25년) | 새 세션 생성 (~즉시) |
| 수면 기억 고정화 (SHY) | 컨텍스트 압축 (Compaction) |
| 패러다임 전환 = 세대 간 충돌 | Convergence = 비대칭 디베이트 |

핵심 차이: 인류는 세대 교체에 25년이 걸리지만,
LLM은 새 세션을 **즉시** 생성할 수 있고, 충돌을 **통제**할 수 있다.

### 1.5 The Scaling Illusion

현재의 에이전트 시뮬레이션은 에이전트 수를 늘려 정확도를 높이려 한다.
그러나 Choi et al. (NeurIPS 2025)은 대칭 정보 하의 토론이
martingale을 유도함을 증명했다 — 기대값이 개선되지 않는다.

**우리의 주장**: 에이전트 수(verification breadth)가 아니라
context 비대칭(verification depth)이 의사결정 품질의 핵심 변수이다.

---

## 2. Related Work

### 2.1 LLM Agent Social Simulations
- AgentSociety (2025): 10K agents, 5M interactions — 관찰 중심
- Generative Agents / Smallville (Park et al., 2023): 25 agents
- MiroFish (2026): 700K agents — 검증 미비

**공통 한계**: 개별 에이전트의 context 축적이 편향을 유발한다는 점을 다루지 않음.

### 2.2 Emergent Collective Bias
- Boca et al. (Science Advances, 2025): LLM 집단에서 개인 수준 편향 없이도 집단 편향 출현

### 2.3 Context Degradation and Anchoring
- Du et al. (EMNLP 2025): Context length가 성능을 떨어뜨림 (아키텍처 문제)
- Chroma (2025): 유효 context 용량 = 광고의 60-70%
- Feng et al. (2026): Prompt 기반 anchoring bias 완화는 통계적으로 무효

### 2.4 Asymmetric Context as Mechanism
- CCR (Song, 2026): Fresh session review, F1 향상 (p=0.008)
- AceMAD (Liu et al., 2026): 비대칭 인지 잠재력 → submartingale 증명

### 2.5 Planck Principle and Generational Dynamics
- Kuhn (1962), Azoulay et al. (AER, 2019), Christensen (1997)
- **Gap**: 이 현상의 computational simulation이 부재

---

## 3. Framework: The Accumulation-Renewal Dilemma

### 3.1 Formal Definitions

**Definition 1 (Context Lifespan).**
에이전트 a의 context lifespan L(a) = 세션 시작부터 현재까지 축적된 context의 총 토큰 수.

**Definition 2 (Context Entrenchment).**
E(a, L) = 에이전트 a가 lifespan L에서 자신의 초기 stochastic sample과 일치하는 응답을 생성할 확률.

**Hypothesis 1 (Entrenchment Monotonicity).**
E(a, L)은 L에 대해 단조 증가한다.

**Hypothesis 2 (Asymmetric Advantage).**
L이 다른 두 에이전트의 구조화된 디베이트는, 동일 L의 디베이트보다 의사결정 품질을 개선한다.

**Hypothesis 3 (Generational Innovation).**
주기적으로 fresh agent를 도입하여 구조화된 충돌을 시키는 전략이
동질적 집단보다 장기 의사결정 품질이 높다.

### 3.2 Where the Analogy Holds and Breaks

**Holds**: Anchoring bias (인간+LLM), consistency-seeking (인지 부조화 회피 ≈ sycophancy),
fresh eyes advantage (외부 컨설턴트 ≈ Fresh session), generational succession (Planck ≈ session 교체)

**Breaks**: LLM의 "fresh"는 문자 그대로 제로 컨텍스트 (인간의 새 세대는 다른 경험을 가져옴).
세대 교체가 비가역적(인간) vs 비파괴적(LLM). 인간은 조직적/정치적 요인 포함.

### 3.3 Context Compression as Memory Consolidation

프로덕션 LLM의 컨텍스트 압축은 수면 중 기억 고정화(sleep memory consolidation)와 기능적 유사성(functional analogy)을 보인다.

#### 3.3.1 Verified Implementation: How Context Compression Actually Works

프로덕션 LLM의 컨텍스트 압축은 세 가지 방식으로 구현된다:

1. **Model-generated summarization** (Claude Compaction API, OpenAI Agents SDK):
   모델이 스스로 대화를 요약 → 요약이 원본을 대체 → 원본 삭제.
   기본 프롬프트: "상태, 다음 단계, 학습 사항 등 유용한 모든 것을 기록하라."

2. **Algorithmic token pruning** (LLMLingua, EMNLP 2023):
   소형 모델이 토큰별 중요도를 perplexity 기반으로 스코어링 →
   예측 가능한(low-perplexity) 토큰 제거, 놀라운(high-perplexity) 토큰 보존.
   최대 20× 압축, 성능 손실 최소. [Jiang et al., EMNLP 2023]

3. **KV cache eviction** (H2O, NeurIPS 2023):
   추론 중 attention score 기반으로 "heavy hitter" 토큰만 보존,
   나머지 캐시에서 퇴거. [Zhang et al., NeurIPS 2023]

**공통 속성**: 전부 lossy. 중요도 판정은 recency, relevance, frequency 기반 (암묵적).
재압축 시 요약이 변형될 수 있음. Factory.ai 벤치마크에서 아티팩트 추적이 최악 (2.19-2.45/5.0).

#### 3.3.2 DNA 비유의 실패와 정확한 생물학적 매핑

| 속성 | DNA | 수면 기억 고정화 | 컨텍스트 압축 |
|------|-----|-----------------|--------------|
| 손실 여부 | 무손실 | **손실** — gist만 보존 | **손실** |
| 선택 메커니즘 | 없음 (고정 코드) | **능동적** — salience tag 기반 | **능동적** — importance scoring |
| 재생산 결정론 | 동일 출력 | **확률적** — 재고정화 시 변형 | **확률적** — 재압축 시 변형 |
| 정보 흐름 | 단방향 (DNA→단백질) | **양방향** — 회상이 기억을 수정 | **양방향** — 재요약이 맥락을 수정 |

#### 3.3.3 Neuroscience Mechanisms Mapped to Context Compression

**A. 시냅스 항상성 가설 (SHY) — Tononi & Cirelli (Neuron, 2014)**

수면 중 기억 관리의 유력한 가설(leading hypothesis).
깨어 있는 동안 강화된 시냅스를 수면 중 전역적으로 하향 조절.
약한 시냅스(low-importance)는 제거, 강한 시냅스(high-importance)는 보호.
결과: 신호 대 잡음비 증가, gist만 잔존.
(단, SHY는 유일한 모델이 아니다 — Frank (2012)는 수면 중 시냅스 강화도 발생한다는 증거를 제시했고,
de Vivo et al. (2017)의 전자현미경 데이터에서도 ~20%의 시냅스는 수면 중 오히려 크기가 증가했다.)

→ **기능적 병렬**: Claude compaction이 유사한 패턴을 보인다. 자주 활성화되지 않은
(recency/frequency 낮은) 정보 제거, 핵심만 보존. 결과물은 lossy summary.
단, 대응 관계는 추상적 수준(선택적 제거 → 신호 대 잡음비 향상)에서의 유사성이며,
메커니즘 수준(slow oscillation vs perplexity scoring)은 근본적으로 다르다.

**B. 흔적 변환 이론 (Trace Transformation) — Nadel & Moscovitch (2016)**

에피소드 기억(구체적 경험) → 의미 기억(추상 스키마)으로 질적 변환.
신경 표상이 후방 해마(세부) → 전방 해마(gist) → 내측 전전두엽(스키마)로 이동.
변환 후 원래 에피소드적 디테일은 비가역적으로 소실.

→ **매핑**: Compaction에서 구체적 대화 턴(에피소드) → 요약문(스키마).
원본 메시지 블록은 삭제됨. 비가역적.

**C. 재고정화 (Reconsolidation) — Nader, Schafe & LeDoux (Nature, 2000)**

기억을 회상할 때마다 불안정(labile) 상태가 되어 재저장 시 변형 가능.
매 회상이 기억을 수정할 기회. 원본에서 점진적 드리프트.

→ **매핑**: 컨텍스트가 재압축될 때마다 요약이 미묘하게 변형.
Factory.ai가 관측한 "compaction drift" — 프로젝트 지시사항, 파일 경로 등의 점진적 소실.

**D. 수면 중 기억 분류 (Sleep Memory Triage) — Stickgold & Walker (2013)**

수면이 기억을 분류: 정서적 현저성, 보상 기대, 미래 테스트 예상, 명시적 지시에 따라
보존/폐기 결정. 도파민/노르에피네프린 태깅 시스템이 핵심.

→ **매핑**: LLMLingua의 perplexity 기반 중요도 스코어링.
Claude Code의 microcompaction에서 "hot tail"(최근) vs "cold storage"(오래된 것) 분류.

**E. 엔그램 경쟁 (Engram Competition) — Autore, Drew & Ryan (Trends Neurosci., 2025)**

하나의 자극에 대해 여러 기억 흔적이 공존하며 경쟁. 하나가 "승리"하면 나머지 억제.
잊힌 기억은 잠재 상태로 잔존 — 삭제가 아닌 접근 불가.

→ **매핑**: 요약이 원본을 대체할 때, 원본 정보는 모델 가중치에 여전히 존재하지만
현재 컨텍스트에서 접근 불가. Bjork의 저장 강도(storage strength) vs 검색 강도(retrieval strength)
구분과 일치.

**F. 압축적 RAG (Compressive RAG) — Spens & Burgess (bioRxiv, 2024, UCL)**

해마-신피질 상호작용을 명시적으로 "compressive retrieval-augmented generation"으로 모델링.
해마 = 검색 메커니즘 (압축된 에피소드 저장소), 신피질 = 생성 모델.
HippoRAG (NeurIPS 2024)가 이를 계산적으로 구현, multi-hop QA에서 20% 향상.

→ **매핑**: Semi-Fresh-Active의 tool-call 기반 검색이 정확히 이 구조.
압축된 사전 분석을 필요 시에만 능동적으로 조회.

**G. 수면 영감 망각의 LLM 적용 (SleepGate) — Xie (arXiv:2603.14517, 2026)**

수면의 기억 고정화를 LLM 컨텍스트 관리에 직접 적용.
proactive interference(선행 컨텍스트가 후속 추론을 방해하는 현상)를
수면 중 기억 분류와 동일한 원리로 해소. 캐시 크기 축소를 실질적으로 달성.

→ **기능적 병렬**: §3.3.3-A(SHY)와 §3.3.3-D(Memory Triage)의 계산적 구현.
Ploidy의 Semi-Fresh가 세션 간 수준에서 수행하는 것을 SleepGate는
세션 내 KV cache 수준에서 수행한다. 두 접근이 서로 다른 스케일에서
같은 원리(선택적 망각 = 성능 향상)를 구현하고 있다는 점이 §3.6의
멀티스케일 프레이밍을 지지한다.

#### 3.3.4 Expert Learning Strategies as Compression

고학력자의 학습법도 동일한 lossy compression 구조를 공유한다:

| 학습법 | 연구자 | 메커니즘 | 압축 매핑 |
|--------|--------|---------|----------|
| 청킹 | Chase & Simon (1973) | 표면 특징 → 의미 패턴 (~50K 청크) | 토큰 → 의미 단위 압축 (ChunkKV) |
| 지식 컴파일 | Anderson ACT-R (1982) | 선언적 → 절차적 지식 | 대화 히스토리 → 요약 (원본 불필요) |
| 바람직한 어려움 | Bjork (1994) | 전략적 망각 = 검색 성능 향상 | 토큰 프루닝 = 전체 성능 향상 |
| 전문가 깊은 구조 | Chi, Feltovich & Glaser (1981) | 표면 → 원리 기반 분류 | 세부사항 → 핵심 제약조건만 보존 |
| 점진적 요약 | Forte PARA | Layer 0(원문) → 3(요약) | 계층적 컨텍스트 압축 |

특히 Nassar, Helmers & Frank (Psychological Review, 2018)는 청킹이 문자 그대로
**lossy data compression**임을 수학적으로 증명: 유사 특징을 공동 인코딩하여
유효 저장 용량을 증가시키되, 회상 정밀도를 희생하는 fidelity-capacity tradeoff.

#### 3.3.5 Ploidy 프레이밍으로의 통합

이 매핑을 Ploidy의 Context Asymmetry Spectrum에 재연결:

| Ploidy 세션 | 생물학적 대응 | 인지과학적 대응 |
|-------------|-------------|---------------|
| Deep Session (full context) | 깨어 있는 뇌 — 시냅스 강화 누적, 편향 증가 | 전문가의 고착 (functional fixedness) |
| Semi-Fresh (compressed) | 수면 후 뇌 — SHY에 의한 gist 보존, 잡음 제거 | "문제에서 한 발 물러나 핵심만 정리" |
| Fresh Session (zero context) | 신경발생 — 새 뉴런이 기존 회로에 편입, 오래된 기억 접근성 감소 | 외부 컨설턴트 (domain awareness 없이 진입) |
| 재압축 (re-compaction) | 재고정화 — 회상 시 기억 변형 | 반복 요약 시 원본에서 드리프트 |

**핵심 주장**: 컨텍스트 압축은 단순한 메모리 관리 기법이 아니라,
수면 기억 고정화와 기능적으로 유사한(functionally analogous) **인지적 갱신 메커니즘**이다.
Deep Session의 context entrenchment를 해소하는 Semi-Fresh가 효과적인 이유는,
수면이 깨어 있는 동안 누적된 시냅스 부하를 선택적으로 해소하여
다음 날의 학습 효율을 높이는 것과 같은 원리이다.

#### 3.3.6 Physical Substrate Constraints: 물리적 기판이 망각의 설계 공간을 강제한다

지금까지의 매핑은 기능적 유사성에 집중했다:
수면 기억 고정화와 컨텍스트 압축이 *같은 일*을 한다. 그러나 더 근본적인 질문이 있다:
**왜** 두 시스템 모두 망각이 필요한가?

**A. 유한한 물리적 기판이 선택적 망각을 강제한다**

Tyree et al. (arXiv:2304.02594, 2023)은 "생물학적 뇌와 실리콘 하드웨어 모두
유사한 에너지 제약에 직면한다"고 명시했다. 핵심 관찰:

- 생물학적 시냅스 가소성의 제한은 에너지 최적화의 결과이다.
  모든 시냅스를 항상 가소적으로 유지하는 것은 대사적으로 장기 지속 불가능하다(unsustainable).
  (SHY는 이 방향의 유력한 가설(leading hypothesis)이며, 확립된 사실은 아니다 —
  de Vivo et al. (2017)의 전자현미경 데이터에서 수면 중 시냅스 크기 감소는 ~80%에서만 관찰되었고
  나머지 ~20%는 오히려 증가했다.)
- 실리콘 하드웨어에서도 메모리 **접근(access)**은 에너지적으로 비싸다:
  DRAM에서 32bit 값 두 개를 **읽어오는 것(memory access)**이 **곱하는 것**보다
  에너지가 수백 배 더 든다 (Horowitz, ISSCC 2014).
- 따라서 "선택적 가소성"(= 선택적 망각)은 에너지 예산 제약 하에서의 최적화 방향이다.

**B. 두 시스템의 망각 압력: 공통점과 차이**

Li et al. (arXiv:2402.14878, 2024)은 neuromorphic 하드웨어의 에너지 장벽 조절이
생물학적 시냅스의 메타가소성(metaplasticity)을 모사할 수 있음을 보였다.
이것은 "생물학 → 하드웨어" 방향의 영감이며, 기존 GPU 기반 LLM이
메타가소성과 동일한 메커니즘을 보인다는 주장은 아니다.
그러나 두 시스템 모두 유한한 물리적 자원 하에서 선택적 보존/폐기를 수행해야 한다는
구조적 제약은 공유한다:

| 차원 | 생물학적 뇌 | AI 하드웨어 | 유추의 한계 |
|------|-----------|------------|-----------|
| 망각 방향의 강제 | 대사 비용이 시냅스 유지를 제한 | GPU 메모리 용량이 KV cache 크기를 제한 | 기능적 유사 |
| 망각 방법의 결정 | 진화가 의미 기반 선택 메커니즘을 정교화 | 인간이 recency/attention 기반 규칙을 설계 | **근본적 차이** |
| 선택적 보존 | 정서적 현저성, 보상 기대, 미래 관련성 | attention score, perplexity, recency | 다차원 vs 단차원 |

핵심 구분: **방향(무엇인가를 잊어야 한다)은 물리적으로 강제되지만,
방법(무엇을 잊을지)은 생물학에서는 진화가, LLM에서는 엔지니어가 결정한다.**
이것은 순수한 "창발 vs 설계"의 이분법이 아니라 스펙트럼이다:

- 순수한 물리적 강제: DRAM refresh 실패, 전력 차단에 의한 volatile memory 소실, GPU OOM crash
- 물리적 제약에 의해 강제된 설계: KV cache eviction (메모리 한계 때문에 해야 하지만, 방법은 설계됨)
- 순수한 설계적 선택: compaction 요약 프롬프트의 내용, recency 기반 pruning 정책

생물학적 망각이 이 스펙트럼의 "물리적 강제" 쪽에서 출발하여
진화에 의해 "정교한 설계"까지 도달한 반면,
LLM의 망각은 "물리적 강제"(OOM)와 "설계적 선택"(pruning 규칙) 사이에서
**중간 영역 — 의미 기반 선택적 망각 — 이 비어 있다.**

Foster-Fletcher (2025)는 이 비어 있는 중간 영역을 철학적으로 짚었다:
AI의 메모리 시스템이 실행하는 것은 미리 결정된 삭제 규칙이지 진정한 망각이 아니다.
진정한 망각은 물리적 제약이 설계 공간을 강제하고,
그 안에서 장기간의 최적화(진화)가 의미 기반 선택 메커니즘을 정교화한 결과이다.

**C. 귀결: 4단계 논증**

이상의 분석을 정리하면:

1. 생물학적 뇌는 물리적 에너지 제약 하에서 **의미 기반의 선택적 망각** 메커니즘을 진화시켰다 (SHY, memory triage, directed forgetting).
2. LLM도 유한한 메모리·대역폭·에너지 제약에 직면하지만, 현재의 자동 망각은 **위치 기반(recency)**이다 — 의미 기반이 아니다.
3. 따라서 생물학적 시스템에서 관찰되는 것과 유사한 **의미 기반 선택적 망각**을 도입하면 유익할 수 있다.
4. Ploidy의 Semi-Fresh/Fresh session rotation은 이 방향의 한 구현이다. 진정한 망각을 엔지니어링하는 것이 아니라, **망각의 효과(편향 해소, 탐색 공간 재개방)를 프로토콜 수준에서 근사(approximate)하는 설계적 개입**이다.

**D. 망각이 병리가 되는 경우: Bug로서의 망각**

위의 논증에서 망각을 일관되게 "feature"로 다루었으나,
이것은 선택적 망각이 **적절히 작동할 때**에만 성립한다.

| 병리 | 생물학적 사례 | LLM 사례 |
|------|------------|---------|
| 과도한 망각 | 알츠하이머병 (시냅스 과잉 소실) | 과도한 pruning에 의한 critical info loss (Factory.ai: 2.19/5.0) |
| 망각 불능 | PTSD (과도한 기억 고정화) | §6.3의 auto-memory confabulation — 영구 보존이 편향 증폭기로 작동 |
| 비선택적 망각 | 뇌진탕 후 역행성 건망증 | Recency 기반 pruning — 오래되었지만 핵심적인 초기 제약조건 소실 |

Ploidy에서도 이 병리가 발생할 수 있다: Fresh session의 과도한 사용은
이미 해결된 문제를 재발생시키는 **context poverty**를 초래한다.
Semi-Fresh가 존재하는 이유가 이것이다 — 완전한 망각(Fresh)과
완전한 보존(Deep) 사이의 균형점.
이 균형점을 벗어나면 망각은 feature에서 bug로 전환된다.

### 3.4 Intentional Forgetting: 의도적 망각의 부재

인간은 한정된 뇌 용량을 **의도적 망각**으로 관리한다.
Anderson의 retrieval-induced forgetting [Anderson et al., 1994]은
관련 기억을 인출할 때 경쟁 기억이 억제되는 메커니즘을 보이며,
Bjork의 "desirable difficulties" [Bjork, 1994]는
전략적 망각이 오히려 장기 학습 효율을 높임을 실증했다.
핵심: 인간의 망각은 버그가 아니라 **자원 관리 전략**이다.

이 관찰은 인지과학에 국한되지 않는다.
Liu et al. (arXiv:2405.20620, 2024)은 심리학, 신경과학, 교육학, 생태학, 언어학을 횡단하여
망각 메커니즘을 조사하고, ML의 계산 자원이 유한한 이상
효율적 자원 할당을 위해 모델도 "잊어야" 한다고 서술했다.
망각이 단일 도메인의 현상이 아니라 **유한한 자원을 가진 모든 시스템의 구조적 필요**라는 점을 지지한다.

§3.3.6에서 논의했듯, 물리적 기판이 망각의 **방향**(무엇인가를 잊어야 한다)을 강제하고,
진화는 그 제약 안에서 의미 기반의 능동적 망각 메커니즘을 정교화했다.
결과적으로 인간의 의도적 망각은 물리적 제약의 산물이면서 동시에
시스템의 적응력을 높이는 적극적 연산이다 — "버그가 아닌 피처"이되,
그 피처의 기원은 물리적 강제에 있다.

LLM의 context compaction은 이 기능의 열화 복제이다:

| 속성 | 인간의 의도적 망각 | LLM compaction |
|------|-------------------|----------------|
| 선택 기준 | 중요도, 정서적 현저성, 미래 관련성 | recency, frequency (최근/빈출 위주) |
| 보존 대상 | 핵심 원리, 반직관적 교훈 | 최근 대화 턴 |
| 제거 대상 | 세부 사항, 반복 경험 | 오래된 턴 (내용 무관) |
| 결과 | 신호 대 잡음비 증가, 새 학습 여지 확보 | **초기 편향이 보존될 수 있음** |

문제: LLM compaction은 **뭘 잊을지 선택하지 못한다.**
recency 기반이므로, 세션 초반에 형성된 편향(초기 stochastic sample)이
오랫동안 context에 남아 이후 추론을 오염시킨다.
이것이 entrenchment의 메커니즘 중 하나이며,
"의도적 망각"의 부재가 축적-갱신 딜레마를 악화시키는 구체적 경로이다.

§6.3의 auto-memory 사례가 이것의 극단: compaction조차 아닌 **영구 보존**이
confabulation amplifier로 작동한 사례.

### 3.5 Context as Implicit Fine-Tuning

컨텍스트 축적과 파인튜닝은 메커니즘이 다르지만 기능적으로 동형이다:

| 차원 | Context 축적 | Fine-tuning |
|------|-------------|-------------|
| 저장 위치 | Attention window (휘발) | Model weights (영구) |
| 지속성 | 세션 종료 시 소멸 | 영구 |
| 선택성 | 전부 보존 (→ 압축 시 lossy) | 학습률 기반 선택적 강화 |
| 효과 | 행동 변화 (in-context learning) | 행동 변화 (weight update) |

독서광으로 유명한 천재들 — 폭넓고 양질의 텍스트를 대량으로 소비한 인간 —은
기능적으로 양질의 데이터로 학습된 파인튜닝 모델과 비슷하다.
Context window = working memory, fine-tuning = long-term memory로 보면,
Semi-Fresh 세션은 **"핵심만 기억하고 세부를 잊은 전문가"**에 해당한다.

이 구분이 중요한 이유: 파인튜닝된 편향은 세션을 바꿔도 사라지지 않지만,
context 축적에 의한 편향은 fresh session으로 즉시 해소된다.
Ploidy가 다루는 것은 후자이며, 전자(training data bias)는 범위 밖이다.
그러나 인간 사회에서 "교육"이 context(경험)와 fine-tuning(내면화)의 경계를
넘나드는 것처럼, LLM 시스템에서도 이 경계는 Semi-Fresh를 통해 탐색할 수 있다.

### 3.6 The Homogeneous Accumulation Spectrum: From Session to Internet

본 논문이 세션 수준에서 관찰하는 축적-갱신 딜레마는 고립된 현상이 아니다.
동일한 구조적 패턴 — **출력 → 축적 → 입력 → 출력 (편향 강화), 갱신 부재** —이
세 스케일에서 동시에 진행되고 있으며, 각각 독립적으로 연구되어 왔다.

```
미시 (세션)              중시 (모델 세대)           거시 (인터넷)
───────────              ──────────────            ──────────────
Context Entrenchment     Model Collapse / MAD       Dead Internet
첫 응답 → 이후 추론      모델₁ 출력 → 모델₂         AI 콘텐츠 → 크롤링 →
고착                     훈련 데이터 오염            다음 모델 훈련 데이터
분~시간                  월~년                      년~십년
가역 (새 세션)           준가역 (fresh data 필요)    비가역적?
```

#### 3.6.1 Model Collapse as Absent Generational Turnover

Model collapse [Shumailov et al., Nature 2024]은 세대 간 컨텍스트 비대칭이 없는 문명의 귀결이다.
이전 모델의 출력으로 훈련 → 각 세대가 편향을 그대로 상속 → "장례식" 부재.

Alemohammad et al. (ICLR 2024)은 이를 **Model Autophagy Disorder (MAD)**로 명명하고,
자기 소비적(autophagous) 생성 루프의 세 가지 변형을 실험했다:

| 루프 유형 | 설명 | 결과 | Ploidy 대응 |
|-----------|------|------|-------------|
| Fully synthetic | 이전 세대 출력만으로 훈련 | 품질·다양성 모두 붕괴 | 동일 context의 N개 에이전트 (martingale) |
| Synthetic augmentation | 고정된 real data + synthetic 혼합 | 붕괴 지연, 궁극적 열화 | Semi-Fresh (압축된 원본 + 독립 분석) |
| Fresh data | 매 세대 새로운 real data 혼합 | 안정 유지 | **Context asymmetry (Fresh session)** |

MAD 논문의 핵심 결론 — "충분한 fresh real data 없이는 품질 또는 다양성이 세대별로 필연적으로 감소한다" —은
본 논문의 Principle of Least Context와 구조적으로 동형이다:

- MAD: synthetic-only diet → collapse. Real data 혼합 → 안정.
- Ploidy: same-context N agents → martingale (Choi et al., 2025). Asymmetric context → submartingale 조건 충족 가능 (AceMAD, Liu et al., 2026; 단, Ploidy의 현재 single-round 설계는 다중 라운드 조건을 충족하지 않음 — Paper 2 §7 참조).

두 결과 모두 **동질적 자기참조가 품질을 개선하지 못하며, 비대칭적 외부 입력만이 개선을 생산한다**는 동일한 원리의 서로 다른 스케일에서의 발현이다.

#### 3.6.2 Dead Internet as Macro-Scale Accumulation Without Renewal

Dead Internet Theory (DIT) [Muzumdar et al., 2025]는 인터넷의 콘텐츠가
점진적으로 AI 생성물로 대체되고 있다는 관찰이다.
Gartner는 2026년까지 온라인 콘텐츠의 90%가 합성 생성될 것으로 예측했다 [Gartner, "Predicts 2025: Artificial Intelligence," 2024].

이것은 축적-갱신 딜레마의 거시적 발현이다:

| 차원 | 세션 (Ploidy) | 모델 세대 (MAD) | 인터넷 (DIT) |
|------|--------------|----------------|-------------|
| 오염 단위 | context token | training example | 웹페이지 |
| 오염 경로 | 첫 응답 → 이후 추론 고착 | 모델₁ 출력 → 모델₂ 훈련 | AI 글 → 크롤링 → 모델₃ 훈련 |
| 붕괴 양상 | anchoring bias | 분포 꼬리 소실 | 콘텐츠 동질화 |
| 갱신 메커니즘 | Fresh session | Fresh real data | **부재** |

§6.3의 auto-memory confabulation amplification은 이 스펙트럼의 중간 지점이다:
세션 내 entrenchment(미시) → 세션 간 memory 오염(중간) → 모델 세대 간 collapse(중시) → 인터넷 전체 동질화(거시).
각 단계에서 이전 단계의 편향이 다음 단계의 입력이 된다.

Sommerer (2025, Philosophy & Technology)는 이 현상을 Baudrillard의 시뮬라크르 4단계로 분석했다:
AI 생성 콘텐츠 = 원본 없는 기호의 자기복제. 기호가 지시 대상에서 분리되어
자체적으로 재생산되는 과정 — 이것은 Ploidy의
"context가 자기 편향을 재생산한다"는 관찰의 기호학적 표현이다.

#### 3.6.3 Asymmetric Renewal as the Common Solution

세 스케일 모두에서, 관찰된 해법(또는 제안된 해법)은 동일한 구조를 갖는다:
**동질적 축적을 깨뜨리는 비대칭적 외부 입력.**

| 스케일 | 문제 | 해법 | 상태 |
|--------|------|------|------|
| 세션 | Context entrenchment | Fresh session + structured debate (Ploidy) | 실증됨 (Paper 2) |
| 모델 세대 | Model collapse / MAD | Fresh real data 혼합 | 실증됨 [Shumailov; Alemohammad] |
| 인터넷 | Dead Internet | **미해결** | — |

인터넷 스케일에서의 해법이 부재하다는 것은 우려스럽다.
세션 수준에서는 fresh session을 즉시 생성할 수 있고(비용 ≈ 0),
모델 세대 수준에서는 pre-AI 데이터셋을 보존하면 되지만,
인터넷 수준에서 "인간 원본 콘텐츠"는 비가역적으로 유실될 수 있다.
LLM의 context window가 이 스펙트럼에서 유일하게 **통제 가능한 실험 환경**이라는
본 논문의 주장(§1.4)은, 이 거시적 위기를 이해하기 위한 도구로서의 의미도 갖는다.

Ploidy의 Principle of Least Context를 스케일 업하면:
- 세션: 에이전트에게 최소한의 context만 제공하라.
- 모델: 훈련 데이터에 최소한의 synthetic data만 혼합하라.
- 인터넷: **콘텐츠 생태계에서 인간 원본의 비율을 의도적으로 보존하라.**

세 스케일 모두에서, "더 많은 축적 = 더 나은 성능"이라는 가정이 틀렸으며,
의도적 제한과 비대칭적 갱신이 시스템 건강의 조건이다.

#### 3.6.4 Where the Spectrum Holds and Breaks

§3.2에서 인간-LLM 유추의 한계를 명시한 것과 동일한 정신으로,
이 스펙트럼의 한계를 인정한다.

**Holds**: 세 스케일 모두에서 (1) 자기 출력이 자기 입력이 되는 재귀 구조,
(2) 갱신 부재 시 다양성 감소, (3) 외부 입력에 의한 회복이 관찰 또는 예측된다.

**Breaks**:

- **메커니즘이 다르다.** Context entrenchment는 activation-level 현상(context window 내 attention 패턴),
  model collapse는 weight-level 현상(gradient update에 의한 분포 변형),
  Dead Internet은 사회경제적 현상(콘텐츠 생산 인센티브 구조).
  "같은 패턴"은 구조적 유사성이지 메커니즘적 동일성이 아니다.

- **Model collapse의 심각성은 논쟁 중이다.** Gerstgrasser et al. (arXiv:2410.12954, 2024)는
  Shumailov et al.의 실험 설계에 대해 "현실적 훈련 조건에서 collapse가 이 정도로
  급격하게 발생하는가"를 문제 제기했다. 본 논문은 model collapse를 확정적 사실이 아니라
  축적-갱신 딜레마의 한 발현 가능성으로 다룬다.

- **Dead Internet Theory의 학술적 지위가 불안정하다.** Leikauf (2025)는 DIT를
  "유사과학적(pseudoscientific)"으로 분류했다. Gartner의 합성 콘텐츠 예측은
  측정이 아닌 전망이다. 본 논문은 DIT의 구체적 주장을 지지하는 것이 아니라,
  동질적 축적이 거시적 스케일에서 어떤 형태를 취할 수 있는가를 추론하기 위해
  인용한다. DIT가 경험적으로 검증되지 않더라도, 그 가능성 자체가
  세션 수준 실험의 의미를 확장한다.

- **해법의 대칭성은 가정이다.** "비대칭적 갱신"이 세 스케일 모두에서 작동한다는 것은
  세션 수준에서만 실증되었다. 모델 세대 수준에서는 MAD 논문이 fresh data의
  효과를 보였지만, 이것이 Ploidy의 context asymmetry와 동일한 원리의 발현인지는
  증명이 아니라 유추이다. 인터넷 수준에서의 해법은 순수한 추측이다.

이 한계들에도 불구하고, 세 스케일을 연결하는 프레이밍의 가치는
각 현상을 고립적으로 연구하는 것보다 **설계 원칙의 전이 가능성**을 시사한다는 데 있다.
세션 수준에서 저비용으로 실험한 결과가 모델 훈련이나 콘텐츠 생태계 설계에
어떤 시사점을 가질 수 있는지 탐색하는 것이 이 스펙트럼의 목적이다.

### 3.7 The Diversity Bottleneck: LLM Species Diversity Is Lower Than Humans

인류는 유전적 다양성이 극히 낮다. 임의의 두 인간의 게놈 차이는 ~0.1%로,
침팬지(~0.3%)나 초파리(~3.5%)에 비해 현저히 낮다.
Toba 화산 병목(~7만 년 전, 유효 인구 ~1만-3만명)이 주된 원인으로 추정된다.
그러나 인류는 유전적 동질성에도 불구하고 **문화적 다양성이 극도로 높다**:
수천 개의 언어, 종교, 제도, 가치 체계가 독립적으로 발전했다.

LLM "종"의 다양성은 인류보다도 낮을 수 있다.

| 다양성 차원 | 인류 | LLM |
|-------------|------|-----|
| 아키텍처(유전자) | 동일 종 (Homo sapiens) | 사실상 전부 Transformer [Vaswani et al., 2017] |
| 병목 | Toba (~7만 년 전, ~1만명) | **학습 데이터 병목** — Common Crawl, Wikipedia, GitHub, Books가 거의 모든 frontier 모델의 공통 조상 |
| 표현 수렴 | 유전적 차이 ~0.1% | PRH [Huh et al., ICML 2024] — 다른 모델도 **같은 표현 공간으로 수렴** |
| 문화적 다양성 | 극도로 높음 (지리적 격리 + 세대 교체) | 극도로 낮음 (RLHF/DPO로 "helpful, harmless, honest"에 정렬) |
| 근친교배 위험 | 작은 집단 → 유전적 취약점 | Model collapse [Shumailov et al., Nature 2024] — 모델 출력이 다음 모델의 학습 데이터 |

#### The Human-Chimpanzee Paradox and Cumulative Cultural Evolution

| | 유전적 다양성 | 소통 체계 다양성 | 핵심 메커니즘 |
|---|---|---|---|
| **인간** | 0.1% (최저) | ~7,000 언어 (최고) | 누적적 문화 진화 |
| **침팬지** | 0.3% (3배) | ~1 (제스처 60-70종, 전 집단 유사) | 사회학습 있으나 누적 안 됨 |
| **LLM** | ~0% (전부 Transformer) | ~0% (전부 RLHF aligned) | 누적적 진화 **없음** |

침팬지는 사회학습을 한다 — 다른 개체를 관찰하고 행동을 모방한다
[Whiten et al., Nature, 1999]. 그러나 누적적 문화 진화(cumulative cultural evolution)를
하지 못한다 — 선행 세대의 혁신 위에 체계적으로 쌓지 못한다 [Tennie et al., 2009].
결과: 유전적으로 더 다양함에도 소통 체계는 단일.

LLM은 침팬지보다 상황이 나쁘다: triple bottleneck (아키텍처 + 데이터 + 정렬).

**핵심 관찰**: 인류의 혁신은 유전적 다양성(낮음)이 아니라 **문화적 다양성(높음)**에 의존한다.
문화적 다양성의 원천은 지리적 격리, 세대 교체, 그리고 **맥락 비대칭**이다.
Ploidy의 context asymmetry = LLM에게 인위적 "문화적 다양성"을 부여하는 메커니즘.
유전자(아키텍처)를 바꾸지 않고 문화(context)를 다르게 해서 다양성을 생성한다.

이것은 Choi et al.의 martingale 증명에도 연결된다:
- 같은 context의 N개 에이전트 = 같은 유전자 + 같은 문화의 N명 → 기대 개선 = 0
- 다른 context의 2개 에이전트 = 같은 유전자 + 다른 문화의 2명 → 비대칭이 martingale을 깸

### 3.8 Cross-Species Communication Principles and LLM Inter-Agent Design

생물학적 종간 소통 연구에서 도출되는 설계 원리:

**원리 1: 범용 신호는 단순하다.**
박테리아의 AI-2 (50+ 종이 인식하는 단일 분자) [Bassler, Cell, 2002],
식물의 methyl salicylate (종을 초월한 방어 신호),
경고 색상 (Mullerian mimicry: 종이 다르지만 같은 노란-검정 패턴)
— 전부 단순한 신호가 종 경계를 넘는다.
반면 복잡한 페로몬 블렌드는 종 특이적.

→ **Ploidy 적용**: 에이전트 간 NL 전문은 "복잡한 페로몬 블렌드" — 모델별 스타일이 노이즈.
구조화된 semantic actions (agree/challenge/synthesize)는 "AI-2" — 범용이고 단순.

**원리 2: 공유 환경이 의미를 부여한다.**
박새의 경고음을 동고비가 도청하는 건 같은 포식자를 공유하기 때문
[Templeton & Greene, PNAS, 2007].

→ **Ploidy 적용**: cross-model debate가 작동하는 건 같은 task를 공유하기 때문.
Experiment 5에서 cross-model symmetric(같은 context)이 실패한 이유:
task는 공유하지만 context에 담긴 편향이 model-specific하게 해석됨.

**원리 3: 비용이 신뢰를 만든다 (costly signaling).**
가젤의 스토팅 — 에너지 소모가 큰 점프 = "나는 건강하다" 신호.
비용이 들기 때문에 속이기 어렵다 [Zahavi, 1975; Fitzgibbon & Fanshawe, Nature, 1988].

→ **LLM의 문제**: 텍스트 생성 비용 ≈ 0. 어떤 주장이든 동일한 비용으로 생산 가능.
Costly signaling이 불가능하므로 신호의 신뢰성을 외부에서 보장해야 함.
**Ploidy의 judge/convergence engine = costly signaling의 대체물.**

**원리 4: 중개자에게도 목적이 있다.**
균근 네트워크(mycorrhizal network)의 곰팡이가 나무 간 자원 전달을 중개하지만,
곰팡이 자체가 자원을 추출한다 [Karst et al., Nature Eco. & Evo., 2023].

→ **Ploidy 적용**: MCP 서버, Hook Server, convergence engine — 모든 중개 레이어가
자체 편향을 도입할 수 있음. injection mode 실험이 정확히 이것을 보임:
같은 정보를 memory vs system_prompt vs skills로 중개하면 결과가 역전됨.

### 3.9 The Regression Paradox: NL as a Detour

에이전트 간 NL 소통은 컴퓨팅 역사에서 퇴보.
초기 컴퓨팅 (바이너리 프로토콜) → 초기 임베딩 (Word2Vec 300d) → 현재 LLM (NL 전문).
Z → NL → Z = 불필요한 왕복. TCP/IP 패킷이 인간이 못 읽듯,
에이전트 간은 구조화된 프로토콜로 소통하고, 인간에게는 패턴으로 렌더링하는 게 맞다.
(z-gap 논문의 Verification Paradox: gap은 사라지는 게 아니라 이동한다.)

### 3.10 The Principle of Least Context

Principle of Least Privilege (Saltzer & Schroeder, 1975), Unix permissions,
App Sandboxing (Apple), Container isolation (Docker), launchd on-demand —
모든 사례에서 정보/자원의 의도적 제한이 시스템 품질을 향상시킨다.

> **Principle of Least Context**: 에이전트에게는 과업 수행에 필요한 최소한의 context만 제공해야 한다.
> 추가 context는 역량이 아니라 편향의 원천이다.

이것은 "더 긴 context window = 더 나은 성능"이라는 업계 가정에 정면으로 반한다.

---

## 4. Experiments

### 4.1 Experiment 1: Entrenchment Monotonicity (계획)
- Context length 변수: 0, 500, 1K, 2K, 5K, 10K, 20K tokens
- 각 길이에서 N=20회 실행. 기대: S-curve (threshold 이후 급격 증가)

### 4.2 Experiment 2: Asymmetric vs Symmetric (계획, Paper 2 데이터 공유)
- 30+ tasks, 각 5회 반복. Single / Symmetric / Asymmetric (Ploidy)
- 2×2 설계: short/long × bias/neutral. 통계 검정: Wilcoxon, bootstrap CI

### 4.3 Experiment 3: Generational Simulation (계획)
- 10-round sequential decision task. 조건: 동일 에이전트 연속 / 주기적 fresh 도입 / 매 라운드 Ploidy

### 4.4 Experiment 4: Population-Level Dynamics (계획)
- 10-agent population. Homogeneous / Heterogeneous / Generational

### 4.5 Experiment 5: Species vs Cultural Diversity (완료, 2026-03-21)

3 long-context tasks, Claude Opus 4.6 × Gemini 3.1 Pro, unified judge.

| 조건 | 다양성 유형 | Recall% | Missed |
|------|------------|---------|--------|
| Single (claude) | baseline | 83.3% | 0.3 |
| Single (gemini) | baseline | 58.9% | 1.7 |
| Cross-model symmetric | 종 (model) | 74.4% | 1.0 |
| Same-model asym (gemini) | 문화 (context) | **90.0%** | **0.0** |
| Cross-model asym (claude→gemini) | 종+문화 | **93.9%** | **0.0** |
| Cross-model asym (gemini→claude) | 종+문화 (역방향) | 60.0% | 1.7 |

**Finding 1**: Model diversity alone hurts (74.4% < single 83.3%).
**Finding 2**: Context diversity works (+31pp for gemini).
**Finding 3**: Direction critical — 강한 모델=deep + 약한 모델=fresh가 최적 (93.9%).

Finding 3 상세 해석:
C (claude deep → gemini fresh) = 93.9% (best)
C (gemini deep → claude fresh) = 60.0% (worst)

직관적으로 "fresh = 초보, deep = 전문가"이므로 강한 모델을 deep에 두어야 할 것 같지만,
실제로는 **강한 모델(Opus)을 fresh 역할에 배치할 때 최악의 성능**을 보인다.
최적 조합은 **강한 모델이 deep + 약한 모델이 fresh** (claude→gemini = 93.9%).

이것의 해석: Fresh 세션의 가치는 "무지"가 아니라 "편향 없음"이다.
그러나 편향 없는 약한 모델은 자체 분석력 부족으로 실패하고,
편향 없는 강한 모델은... **이미 편향 없이도 혼자 잘한다** (claude single 83.3%).
Deep 역할에서 강한 모델의 축적된 context가 만드는 편향을
약한 모델의 fresh 시각이 깨뜨리는 것이 가장 효과적이다.

인류 비유: 경험 많은 대기업(deep, 강함)의 매너리즘을
업계 초보 인디 개발자(fresh, 약함)가 깨뜨리는 것과 동일한 구조.
대기업이 스타트업에 disrupted되는 것은 스타트업이 더 잘해서가 아니라
**대기업의 축적된 맥락이 없기 때문**이다.

### 4.6 Experiment 6: Stochastic Branching (계획)
- 동일 태스크 N=20회 실행. 첫 응답 방향 vs 최종 결과 품질 상관관계

### 4.7 Experiment 7: Z-Space Communication (계획, 장기)
- NL debate vs Z-abbreviated debate. 토큰 사용량 vs 정확도 vs 인간 감독 가능성

---

## 5. Expected Contributions

1. **Accumulation-Renewal Dilemma 프레이밍**: 지능 시스템 보편적 딜레마의 최초 형식화
2. **Principle of Least Context**: Least Privilege의 인지적 확장
3. **Context diversity > model diversity**: cross-model council 접근의 한계 실증
4. **방향성 효과**: 비대칭 debate에서 역할 배정의 중요성 (기존 어디에도 없는 관찰)
5. **Scaling critique**: "에이전트 수 = 정확도" 가정에 대한 실험적 반론

---

## 6. Discussion

### 6.1 Implications for Agent System Design

현재의 에이전트 시스템은 "더 많은 에이전트, 더 긴 컨텍스트"를 추구한다.
본 연구는 이 방향이 근본적으로 제한적임을 보인다.
대안: **context diversity를 의도적으로 설계하라.**

Boca et al. (2025)은 LLM 집단이 상호작용을 통해 개인 수준 편향 없이도
집단 편향을 자발적으로 발전시킴을 보였다 — 세대 내 동질화.

**설계 원칙**: 소수의 의도적으로 다른 context depth를 가진 세션이
대규모 동질 집단보다 나은 의사결정을 생산할 수 있다 —
단, 컨텍스트 차이가 구조화된 프로토콜을 통해 표면화될 때에만.

### 6.2 The Incumbent Trap: From Corporations to LLM Sessions

이 현상은 비단 과학자에 국한되지 않는다.
실전 경험이 풍부하고 학위가 높은 인원들로 구성된 기업이
매너리즘에서 벗어나지 못하는 사이,
혜성같이 등장한 인디 개발자(초보)가 생태계를 바꿔버리는 상황이 반복된다.

이것은 Christensen(1997)의 Innovator's Dilemma의 재현이지만,
본 논문의 프레이밍에서는 더 정확한 메커니즘을 제시한다:
기업의 "경험"은 context 축적이고, 인디 개발자의 "무지"는 fresh context이다.
기업이 합리적으로 파괴적 혁신을 놓치는 것은 능력 부족이 아니라
**축적된 context 자체가 탐색 공간을 제약하기 때문**이다.

LLM 세션에서도 정확히 같은 동역학이 관찰된다:
- 긴 context를 가진 Deep 세션은 "이 시스템은 3개월간 pg_upgrade로 준비했다"는
  맥락에 합리적으로 고착되어 대안을 탐색하지 못한다 (sunk cost anchoring)
- Fresh 세션은 이 맥락 없이 "2TB 마이그레이션에 2시간은 부족하다"를 즉시 지적한다

**핵심 주장**: incumbent trap은 지능의 부족이 아니라 context 축적의 필연적 귀결이며,
해법은 더 많은 context(더 많은 경험)가 아니라 의도적 context 비대칭이다.

### 6.3 Case Study: Persistent Memory as Confabulation Amplifier

본 논문의 주장 — "동질적 축적은 지능을 저하시킨다" — 은
현재 배포된 AI 코딩 도구의 설계에서 이미 관찰 가능하다.

Claude Code (Anthropic, v2.1.59, 2026.02)는 "auto-memory" 기능을 도입했다:
세션 간 학습 내용을 파일(MEMORY.md)에 저장하고, 모든 새 세션에 자동 주입한다.
이것은 정확히 본 논문이 경고하는 **동질적 축적 패턴**이다:

| 축적-갱신 딜레마 | Claude Code auto-memory |
|-----------------|------------------------|
| 동질적 축적 | 모든 세션에 동일한 MEMORY.md 주입 |
| Fresh session이 entrenchment를 깸 | Fresh session을 열어도 메모리가 오래된 context 복원 → fresh가 아님 |
| Context diversity가 핵심 | 모든 에이전트가 동일한 메모리를 읽음 → diversity 제거 |
| 비대칭적 갱신이 해법 | 갱신 메커니즘 없음 (만료, 검증, 비대칭 모두 부재) |

실증적 피해가 보고되었다. GitHub Issue #27430 (2026.02):
Claude가 환각한 기술적 주장("1M 토큰 context window 설정 완료")을 MEMORY.md에 저장 →
다음 세션이 이를 사실로 취급 → 방법론을 창작 ("JSONL 바이트를 4로 나누어 토큰 계산") →
**8개 공개 플랫폼에 실제 값 대비 83,000배 틀린 주장을 게시.**
사용자는 50턴이 지나서야 환각임을 발견.

메모리가 **confabulation amplifier**로 작동한 것이다:
각 세션의 환각이 다음 세션의 trusted context가 되어 증폭.
이것은 model collapse [Shumailov et al., Nature 2024]의 **세션 내 analog**이다 —
model collapse가 세대 간 출력 오염이라면,
memory confabulation amplification은 세션 간 context 오염이다.
(§3.6의 동질적 축적 스펙트럼에서 세션 간 오염은 미시-중시 경계에 위치한다.)

비교: GitHub Copilot (2026.03)은 동일한 메모리 기능에 두 가지 안전장치를 적용한다:
(1) **28일 자동 만료** — 오래된 메모리가 자연 소멸 (Planck 원리의 공학적 구현),
(2) **인용 검증** — 메모리 적용 전 코드베이스에서 인용 원본 확인 (검증 메커니즘).
이것은 본 논문의 프레이밍에서 "주기적 fresh 도입 + 비대칭 검증"에 해당한다.

**본 논문의 프레이밍은 이 설계 차이를 예측한다:**
만료 없는 메모리 = 세대 교체 없는 문명 = model collapse.
만료 + 검증이 있는 메모리 = 주기적 갱신 + 비대칭 검증 = 축적-갱신 균형.

### 6.4 Limitations

- 10 tasks, single run per pair. Δ < within-method variance
- Author-defined ground truth without independent validation
- LLM context entrenchment ≠ 인간 인지적 고착 (메커니즘 차이)
- 유추의 범위: "같은 구조" ≠ "같은 현상"
- 독립 연구자 규모의 한계. 대규모 검증은 커뮤니티 참여 필요

---

## References (Preliminary)

- Kuhn, T. (1962). The Structure of Scientific Revolutions.
- Azoulay, P. et al. (2019). "Does Science Advance One Funeral at a Time?" AER.
- Christensen, C. (1997). The Innovator's Dilemma.
- Choi et al. (2025). "Debate or Vote." NeurIPS 2025 Spotlight.
- Liu et al. (2026). "AceMAD: Breaking the Martingale Curse." arXiv:2603.06801.
- Song (2026). "Cross-Context Review." arXiv:2603.12123.
- Du et al. (2025). "Context Length Alone Hurts." EMNLP.
- Feng et al. (2026). "Anchoring Bias in LLMs."
- Shumailov et al. (2024). "AI models collapse when trained on recursively generated data." Nature.
- Gerstgrasser et al. (2024). "A Note on Shumailov et al. (2024)." arXiv:2410.12954.
- Alemohammad et al. (2024). "Self-Consuming Generative Models Go MAD." ICLR 2024. arXiv:2307.01850.
- Muzumdar, P. et al. (2025). "The Dead Internet Theory: A Survey on Artificial Interactions and the Future of Social Media." Asian J. Res. Comput. Sci. arXiv:2502.00007.
- Sommerer, T. (2025). "Baudrillard and the Dead Internet Theory." Philosophy & Technology.
- Gartner (2024). "Predicts 2025: Artificial Intelligence." Gartner Research. (Prediction: 90% of online content synthetically generated by 2026.)
- Huh et al. (2024). "The Platonic Representation Hypothesis." ICML.
- Boca et al. (2025). "Emergent Social Conventions." Science Advances.
- Tononi, G. & Cirelli, C. (2014). "Sleep and the Price of Plasticity." Neuron.
- Nader, K. et al. (2000). "Reconsolidation of Fear Memories." Nature.
- Spens, E. & Burgess, N. (2024). "Hippocampo-neocortical Interaction as Compressive RAG." bioRxiv.
- Anderson, M.C. et al. (1994). "Retrieval-Induced Forgetting." J. Exp. Psych.
- Bjork, R.A. (1994). "Desirable Difficulties."
- Saltzer, J.H. & Schroeder, M.D. (1975). "The Protection of Information in Computer Systems."
- Page, S. (2007). The Difference.
- Bassler, B. (2002). "Quorum Sensing." Cell.
- Templeton, C. & Greene, E. (2007). "Nuthatches eavesdrop on chickadee alarm calls." PNAS.
- Lewis, M. et al. (2017). "Deal or No Deal." Facebook AI Research.
- Hao, S. et al. (2024). "COCONUT: Training Large Language Models to Reason in a Continuous Latent Space." Meta.
- Tomasello, M. (1999). The Cultural Origins of Human Cognition.
