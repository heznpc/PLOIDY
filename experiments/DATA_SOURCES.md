# Experimental Data Sources — single canonical location

**Last updated**: 2026-05-28 12:30 KST
**Status**: as of 2026-05-28, ALL prior scattered cells have been rsynced into the canonical `experiments/results/` tree. Sessions only need to scan that one path. The prior scattered locations are kept on disk as backups but are no longer the source of truth.

Run `bash experiments/scripts/data-census.sh` to refresh the numbers below.

## Single canonical store

| Path | Cells | Dirs | Oldest | Newest | What it is |
|---|------:|-----:|--------|--------|------------|
| **`experiments/results/`** | **7,152** | **1,484** | 2026-03-17 | 2026-05-28 | Unified store. All `run_experiment.py` outputs across all models / sweep generations / ploidy levels / injection modes / languages / efforts. Gitignored (size ≈ 200MB); reproducible from runner + checked into Zenodo at paper-release tags. |

## Supplemental tracked artifacts

| Path | Files | What it is |
|---|---:|------------|
| `experiments/cells/` | 16 | Sweep specifications (P / Q / AD1 / AD3 / pilot_v2_{P,Q,merged} / smoke etc.). Each is a list of cell configs. |
| `experiments/logs/` | 106 | Per-sweep execution logs (`{sweep}.jsonl` with `cell_index / cell / returncode / stdout_tail` per row). |
| `experiments/data/processed/` | 19 | Aggregated analyses (`ad1_interim_refusal_flags.json`, `ad1_stage1_aggregated.json`, `event_a_b/{w1_per_trial,per_trial,fresh_excl_items_for_annotation}.jsonl`, plus claude session manifests). |

## Cell breakdown by model (canonical store)

| Model | Cells |
|---|---:|
| claude-opus-4-7 | 2,526 |
| claude-opus-4-6 | 1,522 |
| claude-haiku-4-5 | 321 |
| claude-sonnet-4-6 | 37 |
| gemini-3.1-pro | 36 |
| codex-default | 15 |
| gpt-5.4 | 12 |
| (model field missing) | 2,683 |

## Aggregate paired comparisons — opus-4-7, 1n, raw inj, en, high effort

| Comparison | N pairs | mean ΔF1 | Cohen's d | Wilcoxon p |
|---|---:|---:|---:|---:|
| ploidy − single | 225 | −0.090 | −0.66 | <0.0001 |
| ploidy − ccr | 166 | −0.055 | −0.46 | <0.0001 |
| ploidy − stochastic_n | 49 | −0.044 | −0.38 | 0.013 |
| single − ccr | 167 | +0.018 | +0.13 | 0.060 (ns) |

**On opus-4-7 at 1n: Ploidy is significantly worse than every baseline tested.**

## Ploidy-level F1 on opus-4-7 (raw inj, high effort, en)

| (deep_n, fresh_n) | N | mean F1 |
|---|---:|---:|
| 1n (1, 1) | 225 | 0.451 |
| 2n (2, 2) | 215 | 0.432 |
| 3n (3, 3) | 14 | 0.397 |
| 4n (4, 4) | 13 | 0.461 |

**Raising the ploidy level does not monotonically improve F1.** The H_2n+ prediction is effectively already tested in this corpus and not supported.

## opus-4-6 baseline (Mar 17 – Apr 17, 1n raw en high)

| Comparison | N pairs | mean ΔF1 | Cohen's d | Wilcoxon p |
|---|---:|---:|---:|---:|
| ploidy − single | 196 | −0.010 | −0.07 | 0.42 (ns) |
| ploidy − ccr | 48 | +0.067 | +0.54 | 0.0007 |

**On opus-4-6**: Ploidy ≈ Single (no real effect). Ploidy > CCR by +0.067 (medium). The "+0.054 N=95" paper claim came from this slice. The opus-4-6 → 4-7 transition wiped out the Ploidy-over-CCR effect *and* made Ploidy significantly worse than Single.

## Consolidation history

| Date | Action | Cells | Why |
|---|---|---|---|
| 2026-03-17 → 2026-04-17 | runner writes to `experiments/results/` | ~3,000 (opus-4-6 era) | original setup |
| 2026-04-23 | runner accidentally writes to `experiments/src/results/` | 62 (opus-4-7 precursor) | path bug, fixed by PR #55 |
| 2026-04-23 → 2026-05-15 | spec-v2 / spec-v3 sweep runs in `.claude/worktrees/strange-yalow-8d35ff/experiments/src/results/` | 4,874 | parallel design-iteration loop on worktree branch |
| 2026-05-21 (PR #55) | runner output path normalised | — | new sweeps go to `experiments/results/` only |
| **2026-05-28** | **all scattered cells rsynced into `experiments/results/`** | **+4,936** | **single canonical store** |

## Rules for any future session

1. **Scan `experiments/results/` only.** All cells live there. The other paths (`experiments/src/results/`, worktree) are read-only backups.
2. **Run `bash experiments/scripts/data-census.sh`** to refresh counts before quoting any aggregate number.
3. **Do not characterise a calendar period as "no experiments"** without consulting the by-mtime breakdown in the census output. The April 17 → May 21 window in particular has 4,874 cells (the spec-v2/v3 sweep) — that data is real and now lives in the canonical tree.
4. **`analyze_stats.py`** walks the canonical tree by default — its current behaviour is correct now that consolidation is done.

## Migration / followup TODOs

- [ ] **Patch analyze_stats.py** to load all cells from `experiments/results/` only (currently it does so — verify it still gives the same numbers after consolidation).
- [ ] **Zenodo bundle**: when v0.3.4-paper tags, snapshot `experiments/results/` + `experiments/cells/` + `experiments/logs/` + `experiments/data/processed/` into the deposit.
- [ ] **Delete scattered backups** after Zenodo bundle is verified (frees ~130MB, but keep until then for safety).
