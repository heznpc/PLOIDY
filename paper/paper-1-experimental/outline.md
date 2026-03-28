# Direction Matters: Why Context Asymmetry Outperforms Model Diversity in Multi-Agent LLM Debate

> Draft outline — 2026-03-28
> Target: AAAI 2027 (7 pages) / NeurIPS 2026 Workshop (4-6 pages)
> 전략: Finding 3 (방향 효과)를 killer result로 전면 배치. 생물학 프레이밍은 동기 부여 수준으로 축소.
> 이론적 프레이밍 전체는 paper-1-position 참조.

---

## Abstract

멀티 에이전트 LLM 디베이트에서 에이전트 수(verification breadth)를 늘리거나
모델 종류(species diversity)를 다양화하는 것은 의사결정 품질을 개선하지 못한다.
본 논문은 context 비대칭(verification depth)이 핵심 변수임을 실험적으로 보인다.
세 가지 관찰을 보고한다:
(1) 동질적 확장과 종 다양성은 실패한다,
(2) context 비대칭이 모델 다양성보다 우월하다,
(3) 비대칭의 방향이 결정적이다 — 강한 모델이 deep + 약한 모델이 fresh일 때
최고 성능(93.9%), 역방향은 최악(60.0%).
이 결과를 Principle of Least Context로 정리한다:
추가 context는 역량이 아니라 편향의 원천이다.

---

## 1. Introduction (~1 page)

### 1.1 The Problem: Context Accumulation as Bias Source

프로그래머의 "새로 시작하면 풀린다" 경험 (2-3문장).
축적된 지식이 혁신을 저해하는 역설 [Kuhn 1962; Christensen 1997].
LLM에서: 동일 모델 동일 질문에 매번 다른 답변.
하나의 세션만 이어가면 첫 응답의 확률적 샘플이 전체 경로를 결정.
같은 context의 N개 에이전트는 같은 편향 분포에서 N번 샘플링할 뿐.

### 1.2 Biological Motivation (1-2 paragraphs, 동기 부여만)

- Planck principle / Azoulay et al. (AER, 2019): 세대 교체가 혁신을 촉진
- SHY (Tononi & Cirelli, 2014): 수면 중 시냅스 부하 선택적 해소
- **이 논문의 기여는 생물학적 매핑이 아님을 명시.**
  "이 유추에서 영감을 받아 LLM context window에서 통제 실험을 설계했다."

### 1.3 LLM Context Window as Controllable Testbed

인간-LLM 매핑 축소 테이블 (3-4행).
핵심 차이: 인류는 세대 교체에 25년, LLM은 즉시 + 통제 가능.
Choi et al. (NeurIPS 2025): 대칭 정보 토론 = martingale.

### 1.4 Our Contribution

- Finding 1: 종 다양성 실패
- Finding 2: Context 비대칭 > 모델 다양성
- Finding 3: 비대칭의 방향이 결정적 (killer result)
- Principle of Least Context

---

## 2. Related Work (~0.75 page)

### 2.1 Multi-Agent LLM Debate

Choi et al. (2025) martingale, AceMAD (Liu et al., 2026) submartingale,
CCR (Song, 2026) fresh session review F1 향상.

### 2.2 Context Degradation and Anchoring

Du et al. (EMNLP 2025), Feng et al. (2026), Chroma (2025).

### 2.3 Agent Scaling Approaches

AgentSociety (2025), MiroFish (2026). 공통 한계: context 축적 편향 미다룸.
Boca et al. (Science Advances, 2025): 집단 편향 출현.

---

## 3. Framework (~1 page)

### 3.1 Formal Definitions

- Definition 1: Context Lifespan L(a) = 세션 시작부터 축적된 context 토큰 수
- Definition 2: Context Entrenchment E(a, L) = 초기 stochastic sample과 일치 확률
- Hypothesis 1: Entrenchment Monotonicity — E(a, L)은 L에 대해 단조 증가
- Hypothesis 2: Asymmetric Advantage — L이 다른 두 에이전트의 디베이트가 동일 L보다 우월

### 3.2 Where the Analogy Holds and Breaks (3-4문장)

Holds: anchoring bias, consistency-seeking, fresh eyes advantage.
Breaks: LLM fresh = 문자 그대로 zero context, 세대 교체 비가역성 차이.

### 3.3 The Principle of Least Context

Least Privilege (Saltzer & Schroeder, 1975)에서 유래.
"에이전트에게는 과업 수행에 필요한 최소한의 context만 제공해야 한다.
추가 context는 역량이 아니라 편향의 원천이다."

---

## 4. Experimental Setup (~1.25 pages)

### 4.1 Task Design

3 long-context tasks (사전 분석이 anchoring bias를 유발하도록 설계).
각 태스크의 ground truth 기준 설명.

### 4.2 Models and Conditions

Claude Opus 4.6 × Gemini 3.1 Pro. 6개 조건:
(a) Single (claude), (b) Single (gemini),
(c) Cross-model symmetric (같은 context, 다른 모델),
(d) Same-model asymmetric (gemini deep → gemini fresh),
(e) Cross-model asymmetric (claude deep → gemini fresh),
(f) Cross-model asymmetric reversed (gemini deep → claude fresh).

### 4.3 Debate Protocol

Structured debate: INDEPENDENT → POSITION → CHALLENGE → CONVERGENCE → COMPLETE.
Deep session: 전체 context 유지. Fresh session: zero context.

### 4.4 Evaluation Metrics

Recall%, Missed items, 통계: Wilcoxon signed-rank, bootstrap CI, Cohen's d.

---

## 5. Results (~1.75 pages, 핵심)

### 5.1 Finding 1: Model Diversity Alone Fails

Cross-model symmetric: 74.4% < Single claude 83.3%.
Choi et al.의 martingale 결과와 일치: 대칭 정보에서 다양성 추가는 무효.

### 5.2 Finding 2: Context Diversity Outperforms Model Diversity

Same-model asymmetric (gemini): 90.0% (gemini single 58.9% 대비 +31pp).
AceMAD의 submartingale 조건과 연결.

### 5.3 Finding 3: Direction Is Critical ★

- claude deep → gemini fresh = **93.9%** (best)
- gemini deep → claude fresh = **60.0%** (worst)
- 33.9pp 차이. 같은 모델 쌍, 같은 비대칭, 방향만 역전.

해석:
- Fresh의 가치는 "무지"가 아니라 "편향 없음"
- 강한 모델(Opus)=deep: 고품질 분석 축적 + 약한 모델(Gemini)=fresh: 편향 없이 도전
- 역방향: 약한 모델의 deep 분석은 저품질 + 강한 모델은 fresh에서도 혼자 잘하므로 디베이트 이점 소멸
- Incumbent trap: 경험 많은 대기업의 매너리즘을 인디 개발자가 깨뜨리는 구조

### 5.4 Summary Table

전체 결과 비교표 + 다양성 유형별 시각화.

---

## 6. Discussion (~0.75 page)

### 6.1 Design Implications

"더 많은 에이전트, 더 긴 컨텍스트" 방향의 한계.
설계 원칙: 소수의 의도적 context depth 차이 > 대규모 동질 집단.

### 6.2 Limitations

3 tasks, 단일 실행, 두 모델 쌍만, author-defined ground truth.
Pilot study임을 명시.

### 6.3 Future Work

30+ tasks, 5회 반복, context length gradient, cross-model judge, human eval.

---

## 7. Conclusion (~0.25 page)

에이전트 수가 아니라 context 비대칭이 핵심. 방향이 결정적.
Principle of Least Context: 추가 context는 편향의 원천.
"Direction matters more than diversity."

---

## 예상 페이지 배분 (7-page)

| 섹션 | 페이지 |
|------|--------|
| Abstract | 0.25 |
| 1. Introduction | 1.0 |
| 2. Related Work | 0.75 |
| 3. Framework | 1.0 |
| 4. Experimental Setup | 1.25 |
| 5. Results | 1.75 |
| 6. Discussion | 0.75 |
| 7. Conclusion | 0.25 |
| **합계** | **7.0** |

Workshop 버전 (4-6p): Related Work 0.5, Framework 0.75, Discussion 0.5 → ~5.5p.

---

## 원본(context-as-lifespan-outline) 대비 CUT 요약

| 원본 섹션 | 처리 |
|-----------|------|
| §3.3 (Memory Consolidation 7개 메커니즘) | **삭제** |
| §3.3.6 (Thermodynamics) | **삭제** |
| §3.4 (Intentional Forgetting) | **삭제** |
| §3.5 (Context as Fine-Tuning) | **삭제** |
| §3.6 (Multi-scale Spectrum) | **삭제** |
| §3.7 (Genetic Diversity) | **삭제** |
| §3.8-3.9 (Cross-species, NL Detour) | **삭제** |
| §3.10 (Principle of Least Context) | §3.3으로 **승격** |
