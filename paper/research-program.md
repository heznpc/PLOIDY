# Research Program: Context Asymmetry as Innovation Mechanism

> 2026-03-17 / heznpc
> Three papers, one thesis: accumulated context is simultaneously knowledge and bias.

---

## Thesis

인류의 혁신은 지식의 축적이 아니라 **지식 비대칭의 구조화된 충돌**에서 발생한다.
LLM의 context window는 이 과정의 최초의 통제 가능한 실험 환경이다.

---

## Three Papers

```
[Paper 1: Context as Lifespan]     ← 이론 (왜?)
    "컨텍스트 축적 = 수명, 세대 교체 = 새 세션"
    "Planck 원리의 computational analog"
              ↓
[Paper 2: Ploidy]                  ← 메커니즘 (어떻게?)
    "컨텍스트 비대칭 디베이트 프로토콜"
    "같은 모델, 다른 세션, 구조화된 충돌 → 편향 해소"
              ↓
[Paper 3: Villagent]               ← 인터페이스 (누가, 어디서?)
    "인간 = 지적설계자, 에이전트 = 자율적 존재"
    "창발은 허용하되 시스템을 거스를 수 없는 생태계"
```

---

## Dependency Map

| | Paper 1 (Theory) | Paper 2 (Mechanism) | Paper 3 (Interface) |
|---|---|---|---|
| **Paper 1 필요** | — | ✓ (이론적 동기) | ✓ (설계 철학 근거) |
| **Paper 2 필요** | ✗ | — | ✓ (검증 메커니즘) |
| **Paper 3 필요** | ✗ | ✗ | — |

**출력 순서**: Paper 1 → Paper 2 → Paper 3
**작업은 병렬**: 공유 실험 인프라, 공유 문헌 조사

---

## Paper 1: Context as Lifespan

**제목 (Working)**: "Context as Lifespan: Modeling Generational Innovation through Context-Asymmetric LLM Agent Populations"

**핵심 주장**:
- Context window ≈ 수명 (지식 축적의 시간적 범위)
- Context entrenchment ≈ 패러다임 고착 (Kuhn의 정상과학)
- Session termination ≈ 세대 교체 (Planck 원리의 "funeral")
- Context asymmetry ≈ 세대 간 지식 비대칭 (혁신의 원천)

**차별점** (2026-03 기준 빈 자리):
- AgentSociety: 사회 시뮬레이션하지만 context를 수명으로 보지 않음
- Emergent Social Conventions: 편향 출현 관찰하지만 깨는 메커니즘 없음
- Lifelong Agents: 수명을 늘리려 하지만 수명 자체가 편향 원천이라는 역설 미다룸
- MiroFish: 에이전트 수 스케일링, 검증 없음, verification breadth만 추구

**필요한 실험**:
1. Context length gradient 실험 (0, 1K, 5K, 10K, 50K tokens)
   → context 축적에 따른 anchoring bias 증가 곡선
2. "세대 교체" 시뮬레이션
   → N 세대에 걸쳐 context를 누적/초기화하며 의사결정 품질 추적
3. Asymmetric population 실험
   → Deep/Fresh 비율을 변화시키며 집단 의사결정 품질 측정

**타겟 학회**: AAAI (AI & Society), Computational Social Science, AAMAS

**상태**: 아이디어 단계 → 아웃라인 작성 필요

---

## Paper 2: Ploidy (Revision)

**제목**: "Ploidy: Cross-Session Structured Debate with Intentional Context Asymmetry"

**교수진 리뷰 기반 필수 수정**:

### 즉시 수정 (논문 텍스트)
- [ ] Abstract "higher precision" 삭제 — 데이터 미지지
- [ ] "Preliminary pilot study"로 명시적 위치 설정
- [ ] Finding 표현 약화 ("observed in this pilot")
- [ ] Limitations 대폭 확장 (순환적 태스크 설계, SNR, judge 편향)
- [ ] AceMAD submartingale 인용 정리 (삭제 또는 조건 명시)
- [ ] Introduction에 Planck 원리 / Innovator's Dilemma 1-2문장 추가

### 실험 확장 (공유 인프라 — Paper 1과 겹침)
- [ ] 30+ tasks (15 short + 15 long-context with varying bias)
- [ ] 각 method-task 조합 5회 반복 실행
- [ ] 2×2 설계: context length × bias presence
- [ ] Self-consistency / majority voting 베이스라인 추가
- [ ] 토큰 예산 통제 비교
- [ ] 프로토콜 ablation (typed actions vs free-form, single vs multi-round)
- [ ] Cross-model judge (GPT-4, Gemini) + human eval subset
- [ ] 약한 모델 실험 (Sonnet, Haiku)으로 ceiling effect 회피
- [ ] Context length parameterized study (100, 500, 1K, 5K, 10K tokens)
  → **이 실험이 Paper 1의 "context as lifespan" 곡선 데이터가 됨**

### 통계적 보강
- [ ] Wilcoxon signed-rank test / bootstrap CI
- [ ] Cohen's d 효과 크기
- [ ] Primary metric 사전 등록 (pre-registration)
- [ ] Bonus findings를 F1에서 분리

**타겟 학회**: NeurIPS 2026 Workshop (단기), AAMAS 2027 (장기)

**상태**: Draft v1 완료, 교수진 리뷰 완료 → v2 작업 필요

---

## Paper 3: Villagent

**제목 (Working)**: "The Intelligent Designer Paradigm: Ecosystem Design for Human-Agent Collaboration"

**핵심 주장**:
- Commander(명령) / Observer(관찰) 패러다임은 실패한다
- Designer(설계) 패러다임: 인간이 규칙/구조/제약을 설계, 에이전트는 그 안에서 자율 행동
- Free Will Slider: 자율성의 연속적 제어 (결정론 ↔ 창발)
- Build/Live mode 분리: 게임 디자인 패턴의 에이전트 관리 최초 적용

**Paper 1, 2 의존성**:
- Paper 1이 "왜 Fresh perspective가 필요한가"를 이론적으로 뒷받침
- Paper 2의 Ploidy가 Villagent 내 에이전트 자기교정 메커니즘 제공
- Villagent의 실험은 사용자 연구 (user study) → Paper 1, 2 완료 후 설계 가능

**MiroFish 대비 포지셔닝**:
- MiroFish = 무신론적 (설계자 없음, 에이전트 방치, 검증 없음)
- Villagent = 유신론적 (설계자 참여, 창발 허용, 제약 내)
- "Scaling agents without verification scales bias, not intelligence"

**타겟 학회**: CHI 2027, UIST 2027, CSCW

**상태**: 설계 문서 완료 (10,500줄), 프로토타입 존재, 학술 포지셔닝 필요

---

## Shared Infrastructure

### 실험 프레임워크 (Paper 1 & 2 공유)
```
experiments/
├── run_experiment.py          # 기존 (Paper 2)
├── tasks_longcontext.py       # 기존 (Paper 2)
├── tasks_extended.py          # 신규: 30+ tasks (Paper 2 확장)
├── tasks_context_gradient.py  # 신규: context length gradient (Paper 1)
├── tasks_generational.py      # 신규: 세대 교체 시뮬레이션 (Paper 1)
├── analysis/
│   ├── statistical_tests.py   # Wilcoxon, bootstrap CI, Cohen's d
│   └── visualization.py       # Pareto curves, bias gradient plots
└── results/
    └── {timestamp}/
```

### 문헌 조사 (3편 공유)
- Kuhn (1962), Planck/Azoulay et al. (2019) — Paper 1
- CCR, AceMAD, SR-DCR, DReaMAD, Choi et al. — Paper 2
- Endsley SA, Norman affordances, Will Wright — Paper 3
- AgentSociety, Emergent Social Conventions, MiroFish — Paper 1 & 3

---

## Timeline (Tentative)

| 시기 | Paper 1 (Theory) | Paper 2 (Ploidy) | Paper 3 (Villagent) |
|------|-----------------|-------------------|---------------------|
| 3월 | 아웃라인 작성 | v2 텍스트 수정 | — |
| 4월 | 실험 설계 + context gradient 실험 | 30+ tasks 설계 + 반복 실험 | — |
| 5월 | 세대 교체 시뮬레이션 | 통계 분석 + ablation | 학술 포지셔닝 |
| 6월 | Draft 완성 | NeurIPS Workshop 투고 | 사용자 연구 설계 |
| 7월 | 학회 투고 | — | 프로토타입 확장 |
| 8-9월 | — | AAMAS 2027 준비 | CHI 2027 투고 준비 |

---

## Key Insight (이 연구 프로그램의 한 문장 요약)

> **"많으면 맞겠지"는 수학적으로 틀렸다 (Choi et al., martingale).
> 에이전트를 늘리는 것이 아니라, 서로 다른 깊이의 컨텍스트를 충돌시키는 것이
> 편향을 깨는 유일한 메커니즘이며, 이것은 인류가 세대 교체를 통해
> 25년 주기로 해온 것의 computational analog이다.**
