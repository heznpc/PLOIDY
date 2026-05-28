# Experimental Data Sources — DO NOT MISS

**Last updated**: 2026-05-28 12:00 KST
**Issue this file fixes**: experiment data is split across **4 separate locations**, three of which sit *outside* the canonical `experiments/results/`. Every new Claude session that has only loaded the canonical path has under-counted the corpus by roughly **5,000 cells**. This file is the single index — load it on every session start before doing any aggregate stats.

Numbers below are from the 2026-05-28 12:00 census. Run `scripts/data-census.sh` (see bottom of this file) to refresh them.

## All data locations

| # | Path | Cells | Dirs | Oldest | Newest | What it is |
|---|------|------:|-----:|--------|--------|------------|
| 1 | `experiments/results/` | 2,216 | 182 | 2026-03-17 | 2026-05-28 | **Canonical** — main runner output via `run_experiment.py`. Includes all of the 4th-sweep (5 × 90 cells dated 2026-05-21 + 2026-05-28). |
| 2 | `experiments/src/results/` | 62 | 10 | 2026-04-23 | 2026-05-21 | **Stale path** — runner wrote here before PR #55 (2026-05-21) moved the output to (1). 4th-sweep precursor runs on opus-4-7 (April 23) live here. |
| 3 | `.claude/worktrees/strange-yalow-8d35ff/experiments/src/results/` | **4,874** | **1,292** | 2026-04-23 | 2026-05-15 | **Worktree spec-v2 / spec-v3 sweep** — *the* high-volume corpus. P / Q / AD1 / AD3 / pilot_v2_P,Q,merged / smoke campaigns from the 2-month design-iteration loop. Mostly opus-4-7 at deep_n × fresh_n = 1×1, 2×2, 3×3, 4×4. |
| 4 | `.claude/worktrees/strange-yalow-8d35ff/experiments/cells/` | 16 specs | — | 2026-04-23 | 2026-05-13 | **Sweep specifications** (not output) — each file is a list of cell configs (sweep name, model, method, deep_n, fresh_n, effort, injection, rep, task_idx). |
| 5 | `.claude/worktrees/strange-yalow-8d35ff/experiments/logs/` | 63 logs | — | 2026-04-23 | 2026-05-15 | **Per-sweep execution logs** (`{sweep}.jsonl` with `cell_index / cell / returncode / stdout_tail` per row). |
| 6 | `.claude/worktrees/strange-yalow-8d35ff/experiments/data/processed/` | 2 analyses | — | 2026-05-07 | 2026-05-15 | **Aggregated analyses** — `ad1_interim_refusal_flags.json`, `ad1_stage1_aggregated.json`, `event_a_b/{w1_per_trial,per_trial,fresh_excl_items_for_annotation}.jsonl`. |

## Aggregate paired comparisons (all sources, opus-4-7, 1n, raw inj, en, high effort)

| comparison | N pairs | mean ΔF1 | Cohen's d | Wilcoxon p |
|---|---:|---:|---:|---:|
| ploidy − single | 225 | −0.090 | −0.66 | <0.0001 |
| ploidy − ccr | 166 | −0.053 | −0.45 | <0.0001 |
| ploidy − stochastic_n | 49 | −0.047 | −0.39 | 0.009 |
| single − ccr | 167 | +0.018 | +0.13 | 0.060 |

**On opus-4-7, 1n Ploidy is significantly worse than every baseline tested.** Sample sizes are 1.5×–3× what the 4th-sweep alone provides because sources (2) + (3) contribute the bulk of the data.

## Ploidy-level F1 on opus-4-7 (raw inj, high effort, en) — all sources combined

| (deep_n, fresh_n) | N | mean F1 |
|---|---:|---:|
| 1n (1, 1) | 225 | 0.451 |
| 2n (2, 2) | 215 | 0.432 |
| 3n (3, 3) | 14 | 0.397 |
| 4n (4, 4) | 13 | 0.461 |

**Raising the ploidy level does not monotonically improve F1.** The paper's H_2n+ prediction is not supported by the data already on disk; the 2n+ sweep that was nominally "TBD" has effectively been run.

## opus-4-6 baseline (for transition comparison)

opus-4-6 (Mar 17 – Apr 17, 1n, raw, en, high), all sources:

| comparison | N pairs | mean ΔF1 | Cohen's d | Wilcoxon p |
|---|---:|---:|---:|---:|
| ploidy − single | 196 | −0.010 | −0.07 | 0.42 (ns) |
| ploidy − ccr | 48 | +0.067 | +0.54 | 0.0007 |

**On opus-4-6**: Ploidy ≈ Single (no real effect), Ploidy > CCR by +0.067 (medium). **The "+0.054 N=95" paper claim came from this slice.** The opus-4-6 → 4-7 transition wiped out the Ploidy-over-CCR effect and made Ploidy significantly worse than Single.

## Why sources got missed

- The runner output path was changed by PR #55 (2026-05-21) but the *prior* runs in `experiments/src/results/` were never migrated.
- The worktree at `.claude/worktrees/strange-yalow-8d35ff/` is git-tracked under a different branch (`claude/strange-yalow-8d35ff`) and is not visible from `git status` on `main`. It is also gitignored from the canonical `experiments/results/` tree.
- The April 23 opus-4-7 precursor runs (source 2) are the only opus-4-7 data outside the 4th-sweep dir on `main`. They are 22 ploidy cells, large enough to confirm the sign flip on their own but easy to miss.
- The April 20 – May 21 "two-month iteration loop" the user kept referring to lives entirely in sources (3)–(6). The canonical path on `main` is silent for that month.

## How to load all sources in one go

```bash
# Census refresh
python3 - <<'PY'
import json, glob, os
from collections import defaultdict

SOURCES = [
    "experiments/results",
    "experiments/src/results",
    ".claude/worktrees/strange-yalow-8d35ff/experiments/src/results",
]
cells = []
for s in SOURCES:
    if not os.path.isdir(s): continue
    for d in os.listdir(s):
        for fp in glob.glob(f"{s}/{d}/*.json"):
            if "summary" in fp or "secondary" in fp: continue
            try:
                j = json.load(open(fp))
                if "error" in j: continue
                cells.append(j)
            except: pass
print(f"Total cells across all sources: {len(cells)}")
PY
```

## Rules for any future session

1. **Run the census above first** before quoting any aggregate number.
2. **Cite the source paths** for any aggregate; if a comparison is on N pairs, name which sources contributed.
3. **Do not characterise a calendar gap as "no experiments"** without checking sources (3)–(6).
4. **Do not re-run a sweep that source (3) already contains.** If the data is on disk, use it.

## Migration TODO (not done yet)

- [ ] Decide whether to move source (2) into (1) (the runner write path is now (1); the (2) dir is frozen but still loaded by analyze_stats).
- [ ] Decide whether to consolidate source (3) into a canonical path on `main`. Currently the worktree branch holds the actual files; checking it out on `main` would expose them. Risk: the worktree was a parallel experimental track with a different protocol generation (spec-v2/v3) — merging may create double-counting.
- [ ] Patch `analyze_stats.py` to take a `--include-sources` list and to auto-include all four canonical source paths (currently it walks one root only).
- [ ] Reference this file from the main `CLAUDE.md` and from `paper/main.tex` §sec:setup so the data set inventory is explicit in the paper too.
