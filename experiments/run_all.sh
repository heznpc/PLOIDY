#!/bin/bash
# run_all.sh — Ploidy 논문 실험 전체 실행기
#
# 재설계: 2026-03-19
# 이전 run_all.sh는 single/ploidy/ccr 3개 메서드만 돌려서
# 논문의 핵심 변수(Semi-Fresh, effort, language, ploidy level)가 전부 누락됨.
#
# ┌─────────────────────────────────────────────────────────────────┐
# │ 이미 완료된 실험 (재실행 불필요)                                  │
# │                                                                 │
# │  single/ploidy(2n)/ccr × 28 tasks × inj=raw      ✓             │
# │  single/ploidy/ccr     × 28 tasks × inj=memory   ✓             │
# │  sf_passive/sf_active/sf_selective/self_consistency × 7 short ✓ │
# └─────────────────────────────────────────────────────────────────┘
#
# ┌──────────────────────────────────────────────────────────────────────┐
# │ Phase 구성 (8 phases, 3 tiers)                                      │
# │                                                                      │
# │ Tier 1 — 논문 핵심 (Semi-Fresh + baselines)             ~14h total  │
# │   P1: Semi-Fresh core    (sf_passive, sf_active, sf_selective)      │
# │   P2: Semi-Fresh ablation (sf_passive_indep, sf_passive_bottom)     │
# │   P3: Additional baselines (self_consistency, symmetric, 2nd_op)    │
# │                                                                      │
# │ Tier 2 — 변수 분리 (sweeps)                             ~27h total  │
# │   P4: Injection=skills   (이전 4/28에서 중단, 재실행)               │
# │   P5: Injection: system_prompt + claude_md (신규)                   │
# │   P6: Effort sweep       (low, medium, max × single, ploidy)       │
# │   P7: Ploidy sweep       (1n, 3n, 4n × ploidy only)                │
# │                                                                      │
# │ Tier 3 — 신규 기여                                       ~8h total  │
# │   P8: Language sweep     (ko, ja, zh × single, ploidy)             │
# └──────────────────────────────────────────────────────────────────────┘
#
# 사용법:
#   ./experiments/run_all.sh                  # Tier 1 전체 (P1, P2, P3)
#   ./experiments/run_all.sh 1               # Phase 1만
#   ./experiments/run_all.sh 4 5 6 7         # Tier 2 전체 (병렬 실행)
#   ./experiments/run_all.sh --tier1          # = P1 P2 P3
#   ./experiments/run_all.sh --tier2          # = P4 P5 P6 P7
#   ./experiments/run_all.sh --tier3          # = P8
#   ./experiments/run_all.sh --all            # 전체 (P1~P8)
#   ./experiments/run_all.sh --status         # 실행 상태 확인
#   ./experiments/run_all.sh --tail [N]       # 로그 실시간 (phase N)
#   ./experiments/run_all.sh --kill           # 전체 종료
#   ./experiments/run_all.sh --summary        # 완료된 결과 요약
#
# 병렬 실행 권장 (최대 2개 동시):
#   Stream A: P1 → P2 → P5 → P8    (~22h)
#   Stream B: P3 → P4 → P6 → P7    (~26h)
#
#   터미널 1: ./experiments/run_all.sh 1 && ./experiments/run_all.sh 2 && ./experiments/run_all.sh 5 && ./experiments/run_all.sh 8
#   터미널 2: ./experiments/run_all.sh 3 && ./experiments/run_all.sh 4 && ./experiments/run_all.sh 6 && ./experiments/run_all.sh 7

set -e
cd "$(dirname "$0")/.."

LOG_DIR="experiments/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ─── Utility Functions ──────────────────────────────────────────────────────

run_phase() {
    local phase=$1
    shift
    local logfile="$LOG_DIR/phase${phase}_${TIMESTAMP}.log"

    # Check if phase is already running
    local pidfile="$LOG_DIR/phase${phase}.pid"
    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "⚠  Phase $phase already running (PID $(cat "$pidfile")). Skip or --kill first."
        return 1
    fi

    echo "Phase $phase → $logfile"
    echo "  Args: $*"
    nohup python experiments/run_experiment.py "$@" > "$logfile" 2>&1 &
    echo $! > "$pidfile"
    echo "  PID: $!"
}

show_status() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo " Phase Status"
    echo "═══════════════════════════════════════════════════════════"
    for p in 1 2 3 4 5 6 7 8; do
        local pidfile="$LOG_DIR/phase${p}.pid"
        if [ ! -f "$pidfile" ]; then
            echo "  P${p}: NOT STARTED"
            continue
        fi
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            local logfile
            logfile=$(ls -t "$LOG_DIR"/phase${p}_*.log 2>/dev/null | head -1)
            local progress=""
            if [ -n "$logfile" ]; then
                # Count completed task-method pairs
                local done_count
                done_count=$(grep -c "judging... done" "$logfile" 2>/dev/null || echo 0)
                local error_count
                error_count=$(grep -c "ERROR" "$logfile" 2>/dev/null || echo 0)
                local last_line
                last_line=$(tail -1 "$logfile" 2>/dev/null | sed 's/^/    /')
                progress="  done=$done_count errors=$error_count"
            fi
            echo "  P${p}: RUNNING (PID $pid)${progress}"
            [ -n "$last_line" ] && echo "$last_line"
        else
            echo "  P${p}: DONE (PID $pid was)"
        fi
    done
    echo ""
}

show_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo " Completed Results"
    echo "═══════════════════════════════════════════════════════════"
    for dir in experiments/results/*/; do
        [ -d "$dir" ] || continue
        local count
        count=$(ls "$dir"/*.json 2>/dev/null | grep -cv summary || echo 0)
        local name
        name=$(basename "$dir")
        [ "$count" -gt 0 ] && echo "  $name  ($count results)"
    done
    echo ""
}

tail_logs() {
    if [ -n "$1" ]; then
        local logfile
        logfile=$(ls -t "$LOG_DIR"/phase${1}_*.log 2>/dev/null | head -1)
        if [ -n "$logfile" ]; then
            tail -f "$logfile"
        else
            echo "No log found for phase $1"
        fi
    else
        tail -f "$LOG_DIR"/phase*_*.log
    fi
}

kill_all() {
    for pidfile in "$LOG_DIR"/phase*.pid; do
        [ -f "$pidfile" ] || continue
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "Killed $(basename "$pidfile" .pid) (PID $pid)"
        fi
        rm "$pidfile"
    done
}

# ─── Phase Descriptions ─────────────────────────────────────────────────────

show_phases() {
    cat << 'PHASES'

═══════════════════════════════════════════════════════════════
 Ploidy Experiment Phases
═══════════════════════════════════════════════════════════════

 Tier 1 — 논문 핵심 (Semi-Fresh + baselines)
   P1  Semi-Fresh core       sf_passive, sf_active, sf_selective      ~6h
   P2  Semi-Fresh ablation   sf_passive_indep, sf_passive_bottom      ~4h
   P3  Additional baselines  self_consistency, symmetric, 2nd_opinion ~5h

 Tier 2 — 변수 분리 (sweeps)
   P4  Injection=skills      재실행 (이전 4/28 중단)                  ~4h
   P5  Injection 신규         system_prompt, claude_md                 ~6h
   P6  Effort sweep          low, medium, max × single, ploidy        ~8h
   P7  Ploidy sweep          1n, 3n, 4n × ploidy method               ~9h

 Tier 3 — 신규 기여
   P8  Language sweep        ko, ja, zh × single, ploidy              ~8h

 Total: ~50h sequential, ~26h with 2 parallel streams.

 권장 병렬 구성:
   Stream A: P1 → P2 → P5 → P8
   Stream B: P3 → P4 → P6 → P7

═══════════════════════════════════════════════════════════════
PHASES
}

# ─── Special Commands ────────────────────────────────────────────────────────

case "${1:-}" in
    --status)  show_status; exit 0 ;;
    --tail)    shift; tail_logs "$@"; exit 0 ;;
    --kill)    kill_all; exit 0 ;;
    --summary) show_summary; exit 0 ;;
    --phases)  show_phases; exit 0 ;;
    --help|-h) show_phases; exit 0 ;;
    --tier1)   set -- 1 2 3 ;;
    --tier2)   set -- 4 5 6 7 ;;
    --tier3)   set -- 8 ;;
    --all)     set -- 1 2 3 4 5 6 7 8 ;;
esac

# Default: Tier 1 (가장 중요한 누락 데이터부터)
PHASES="${@:-1 2 3}"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " Launching phases: $PHASES"
echo " Timestamp: $TIMESTAMP"
echo "═══════════════════════════════════════════════════════════"

for p in $PHASES; do
    case $p in
        # ─── Tier 1: 논문 핵심 ──────────────────────────────────
        1) # Semi-Fresh core — 논문의 핵심 contribution
           # sf_passive: 요약을 프롬프트에 직접 주입 (passive delivery)
           # sf_active: 독립 분석 후 요약 참조 (active retrieval)
           # sf_selective: 불확실 영역만 전달 (selective delivery)
           run_phase 1 --all-long \
               --methods sf_passive,sf_active,sf_selective ;;

        2) # Semi-Fresh ablation — delivery mode vs instruction 분리
           # sf_passive_indep: passive + 독립분석 지시 (instruction이 driver인지?)
           # sf_passive_bottom: passive + 요약을 아래에 배치 (position이 driver인지?)
           run_phase 2 --all-long \
               --methods sf_passive_indep,sf_passive_bottom ;;

        3) # Additional baselines — token budget 통제 비교
           # self_consistency: 5회 독립 + majority vote (same budget as ploidy)
           # symmetric: 양쪽 모두 full context (context asymmetry 없이)
           # second_opinion: 2회 독립, 단순 연결
           run_phase 3 --all-long \
               --methods self_consistency,symmetric,second_opinion ;;

        # ─── Tier 2: 변수 분리 ──────────────────────────────────
        4) # Injection=skills 재실행 (이전 4/28에서 중단)
           # skills: "RULE: ..." 형식의 선언적 규칙으로 컨텍스트 주입
           run_phase 4 --all-long \
               --methods single,ploidy,ccr \
               --injection skills ;;

        5) # Injection modes 신규: system_prompt + claude_md
           # system_prompt: 컨텍스트를 시스템 프롬프트로 주입 (위치 권위 편향 테스트)
           # claude_md: <project-instructions> 태그로 주입 (준수 행동 테스트)
           # 각각 개별 실행 — sweep 대신 순차 실행으로 안정성 확보
           run_phase 5a --all-long \
               --methods single,ploidy \
               --injection system_prompt
           run_phase 5b --all-long \
               --methods single,ploidy \
               --injection claude_md ;;

        6) # Effort sweep — 추론 깊이가 결과에 미치는 영향
           # H: effort는 단조 증가가 아님 (max가 오히려 worst일 수 있음)
           # high는 이미 완료 → low, medium, max만 실행
           run_phase 6 --all-long \
               --methods single,ploidy \
               --effort-sweep --efforts low,medium,max ;;

        7) # Ploidy sweep — Event A(context) vs Event B(stochastic) 분리
           # 1n=haploid: 최소, 확률 vs 컨텍스트 구분 불가
           # 3n=triploid: 그룹 내 합의로 원인 분리 가능
           # 4n=tetraploid: 최대 중복, 수확 체감 테스트
           # 2n은 이미 완료 → 1n, 3n, 4n만 실행
           run_phase 7 --all-long \
               --methods ploidy \
               --ploidy-sweep --ploidy-levels 1,3,4 ;;

        # ─── Tier 3: 신규 기여 ──────────────────────────────────
        8) # Language sweep — 로컬라이제이션이 정보 품질에 미치는 영향
           # H1: 현지화가 비판적 발견을 완곡화 (euphemization)
           # H2: 위계적 언어 규범이 기존 입장에 대한 도전을 억제
           # H3: Fresh 세션이 언어 변환에 더 취약 (맥락 결여)
           # en은 이미 완료 → ko, ja, zh만 실행
           run_phase 8 --all-long \
               --methods single,ploidy \
               --lang-sweep --langs ko,ja,zh ;;

        *) echo "Unknown phase: $p (valid: 1-8, --tier1, --tier2, --tier3, --all)"
           exit 1 ;;
    esac
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " All requested phases launched."
echo ""
echo " Monitor:"
echo "   ./experiments/run_all.sh --status"
echo "   ./experiments/run_all.sh --tail       # all logs"
echo "   ./experiments/run_all.sh --tail 1     # phase 1 only"
echo ""
echo " Control:"
echo "   ./experiments/run_all.sh --kill"
echo "═══════════════════════════════════════════════════════════"
