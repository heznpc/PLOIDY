#!/usr/bin/env bash
# 4th-sweep runner with outer restart on token-limit-related exits.
#
# Two-layer resilience for the Claude Code Max 5-hour reset cycle:
#
#   Inner layer (run_experiment.py):
#     - max_retries=20 per LLM call
#     - _calc_wait_until_reset() now has a 5h-cycle fallback anchored
#       at 03:10 local time (overridable via PLOIDY_RESET_*)
#
#   Outer layer (this script):
#     - if the runner exits non-zero, sleep until the next 5h boundary
#       and re-invoke with --resume so completed cells skip
#     - the per-cell result_file.exists() check inside the runner
#       handles the actual skip
#
# Usage:
#
#   ./experiments/scripts/run_4th_sweep.sh        # one full n=1 pass
#   PLOIDY_RUNS=5 ./experiments/scripts/run_4th_sweep.sh   # n=5 (sequential)
#
# State lives under experiments/logs/4th-sweep-phase{N}/, one dir per
# repetition (so analyze_stats.py can aggregate across them).

set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

LOG_ROOT="${ROOT}/experiments/logs"
mkdir -p "$LOG_ROOT"

RUNS="${PLOIDY_RUNS:-1}"
METHODS="${PLOIDY_METHODS:-single,ccr,ploidy}"
EFFORT="${PLOIDY_EFFORT:-high}"
LANG="${PLOIDY_LANG:-en}"
INJECTION="${PLOIDY_INJECTION:-raw}"
ANCHOR_HOUR="${PLOIDY_RESET_ANCHOR_HOUR:-3}"
ANCHOR_MIN="${PLOIDY_RESET_ANCHOR_MIN:-10}"
CYCLE_SECS="${PLOIDY_RESET_CYCLE_SECS:-18000}"  # 5h

next_reset_wait() {
  # Print seconds until the next 5h-cycle boundary (+ 60s safety buffer).
  python3 - <<PY
from datetime import datetime, timedelta
now = datetime.now()
anchor = now.replace(hour=${ANCHOR_HOUR}, minute=${ANCHOR_MIN}, second=0, microsecond=0)
if anchor > now:
    anchor -= timedelta(days=1)
delta = (now - anchor).total_seconds()
cycles = int(delta // ${CYCLE_SECS})
nxt = anchor + timedelta(seconds=(cycles + 1) * ${CYCLE_SECS})
print(int((nxt - now).total_seconds()) + 60)
PY
}

run_one_pass() {
  local run_idx="$1"
  local log="${LOG_ROOT}/4th-sweep-run${run_idx}.log"
  local dir_file="${LOG_ROOT}/4th-sweep-run${run_idx}.dir"

  echo "$(date) ── run #${run_idx} start" | tee -a "$log"

  while true; do
    if [ -s "$dir_file" ]; then
      local resume_dir
      resume_dir="$(cat "$dir_file")"
      echo "$(date) — invoking with --resume ${resume_dir}" | tee -a "$log"
      PYTHONUNBUFFERED=1 python3 "${ROOT}/experiments/src/run_experiment.py" \
        --gradient \
        --methods "$METHODS" \
        --effort "$EFFORT" \
        --injection "$INJECTION" \
        --lang "$LANG" \
        --resume "$resume_dir" >> "$log" 2>&1
    else
      echo "$(date) — first invocation" | tee -a "$log"
      PYTHONUNBUFFERED=1 python3 "${ROOT}/experiments/src/run_experiment.py" \
        --gradient \
        --methods "$METHODS" \
        --effort "$EFFORT" \
        --injection "$INJECTION" \
        --lang "$LANG" >> "$log" 2>&1
      # Capture the just-created results dir for future --resume calls.
      latest_dir="$(ls -td "${ROOT}/experiments/results/"*"_effort-${EFFORT}_lang-${LANG}_inj-${INJECTION}" 2>/dev/null | head -1)"
      if [ -n "${latest_dir:-}" ]; then
        echo "$latest_dir" > "$dir_file"
      fi
    fi

    local rc=$?
    if [ "$rc" -eq 0 ]; then
      echo "$(date) ── run #${run_idx} completed (exit 0)" | tee -a "$log"
      return 0
    fi

    local wait
    wait="$(next_reset_wait)"
    echo "$(date) ── run #${run_idx} exit=${rc}; sleeping ${wait}s (~$((wait/60))min) until next 5h-cycle boundary" | tee -a "$log"
    sleep "$wait"
  done
}

for i in $(seq 1 "$RUNS"); do
  run_one_pass "$i"
done

echo "$(date) ── all $RUNS runs done"
