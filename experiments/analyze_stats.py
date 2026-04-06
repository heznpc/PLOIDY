"""Statistical analysis pipeline for Ploidy experiment results.

Computes:
  1. Per-method descriptive statistics (mean, std, 95% bootstrap CI)
  2. Pairwise Wilcoxon signed-rank tests with Holm-Bonferroni correction
  3. Cohen's d effect sizes (ploidy vs each baseline)
  4. Recall / precision breakdown
  5. Cost-accuracy Pareto analysis (tokens vs F1)
  6. LaTeX table fragments for paper

Usage:
  python experiments/analyze_stats.py [--results-dir DIR] [--baseline ploidy]
    [--filter-effort high] [--filter-injection raw] [--filter-lang en]
    [--min-n 5] [--bootstrap-n 10000] [--latex] [--json]

Requires: numpy, scipy (install: pip install numpy scipy)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@dataclass
class ResultEntry:
    """A single experiment result with computed metrics."""

    task_id: str
    method: str
    method_name: str
    f1: float
    recall: float
    precision: float
    found: int
    partial: int
    missed: int
    total_gt: int
    bonus_findings: int
    elapsed_seconds: float
    total_tokens: int
    effort: str
    language: str
    injection_mode: str
    model: str
    deep_n: int
    fresh_n: int
    run_dir: str


def _compute_recall(found: int, partial: int, total_gt: int) -> float:
    if total_gt == 0:
        return 0.0
    return (found + 0.5 * partial) / total_gt


def _compute_precision(found: int, partial: int, bonus: int) -> float:
    denom = found + partial + bonus
    if denom == 0:
        return 0.0
    return (found + 0.5 * partial) / denom


def _extract_tokens(entry: dict) -> int:
    tu = entry.get("token_usage") or {}
    return tu.get("total_tokens", 0)


def load_results(results_dir: Path, filters: dict) -> list[ResultEntry]:
    """Load and parse all summary.json files, applying optional filters."""
    entries: list[ResultEntry] = []

    for d in sorted(os.listdir(results_dir)):
        summary_path = results_dir / d / "summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list):
            continue

        for r in data:
            if "error" in r or "f1" not in r:
                continue

            method = r.get("method") or r.get("condition") or "unknown"
            effort = r.get("effort") or _infer_field_from_dir(d, "effort-")
            lang = r.get("language") or _infer_field_from_dir(d, "lang-")
            inj = r.get("injection_mode") or _infer_field_from_dir(d, "inj-")
            model = r.get("model") or ""

            filter_map = {"effort": effort, "lang": lang, "injection": inj, "model": model}
            if any(filters.get(k) and v and v != filters[k] for k, v in filter_map.items()):
                continue

            found = r.get("found", 0)
            partial = r.get("partial", 0)
            missed = r.get("missed", 0)
            total_gt = r.get("total_gt", 0)
            bonus = r.get("bonus_findings", 0)

            recall = r.get("recall") or _compute_recall(found, partial, total_gt)
            precision = r.get("precision") or _compute_precision(found, partial, bonus)

            entries.append(
                ResultEntry(
                    task_id=r.get("task_id", ""),
                    method=method,
                    method_name=r.get("method_name") or r.get("condition_name") or method,
                    f1=r["f1"],
                    recall=recall,
                    precision=precision,
                    found=found,
                    partial=partial,
                    missed=missed,
                    total_gt=total_gt,
                    bonus_findings=bonus,
                    elapsed_seconds=r.get("elapsed_seconds", 0),
                    total_tokens=_extract_tokens(r),
                    effort=effort or "",
                    language=lang or "",
                    injection_mode=inj or "",
                    model=model,
                    deep_n=r.get("deep_n", 1),
                    fresh_n=r.get("fresh_n", 1),
                    run_dir=d,
                )
            )

    return entries


def _infer_field_from_dir(dirname: str, prefix: str) -> str | None:
    """Extract a value from a dirname like '20260328_effort-high_lang-en_inj-raw'."""
    for part in dirname.split("_"):
        if part.startswith(prefix):
            return part[len(prefix) :]
    return None


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------


@dataclass
class MethodStats:
    """Descriptive and inferential statistics for a single method."""

    method: str
    method_name: str
    n: int
    f1_mean: float
    f1_std: float
    f1_ci_lo: float
    f1_ci_hi: float
    recall_mean: float
    recall_std: float
    recall_ci_lo: float
    recall_ci_hi: float
    precision_mean: float
    precision_std: float
    precision_ci_lo: float
    precision_ci_hi: float
    tokens_mean: float
    time_mean: float
    f1_values: list[float] = field(default_factory=list, repr=False)
    recall_values: list[float] = field(default_factory=list, repr=False)
    precision_values: list[float] = field(default_factory=list, repr=False)


@dataclass
class PairwiseTest:
    """Result of a pairwise comparison between two methods."""

    method_a: str
    method_b: str
    n_pairs: int
    wilcoxon_stat: float | None
    p_value: float | None
    p_corrected: float | None
    cohens_d: float
    mean_diff: float
    significant: bool


def bootstrap_ci(
    values: np.ndarray, n_bootstrap: int = 10000, ci: float = 0.95, seed: int = 42
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for the mean (vectorized)."""
    rng = np.random.RandomState(seed)
    n = len(values)
    indices = rng.randint(0, n, size=(n_bootstrap, n))
    means = values[indices].mean(axis=1)
    alpha = (1 - ci) / 2
    return float(np.percentile(means, 100 * alpha)), float(np.percentile(means, 100 * (1 - alpha)))


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Compute Cohen's d (pooled standard deviation)."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    pooled_var = ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
    pooled_std = math.sqrt(pooled_var)
    if pooled_std == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled_std)


def compute_method_stats(
    entries: list[ResultEntry], min_n: int, n_bootstrap: int
) -> dict[str, MethodStats]:
    """Compute per-method descriptive statistics with bootstrap CI."""
    by_method: dict[str, list[ResultEntry]] = defaultdict(list)
    for e in entries:
        by_method[e.method].append(e)

    result: dict[str, MethodStats] = {}
    for method, method_entries in sorted(by_method.items()):
        if len(method_entries) < min_n:
            continue

        f1s = np.array([e.f1 for e in method_entries])
        recalls = np.array([e.recall for e in method_entries])
        precisions = np.array([e.precision for e in method_entries])
        tokens = np.array([e.total_tokens for e in method_entries])
        times = np.array([e.elapsed_seconds for e in method_entries])

        f1_ci_lo, f1_ci_hi = bootstrap_ci(f1s, n_bootstrap=n_bootstrap)
        rec_ci_lo, rec_ci_hi = bootstrap_ci(recalls, n_bootstrap=n_bootstrap)
        prec_ci_lo, prec_ci_hi = bootstrap_ci(precisions, n_bootstrap=n_bootstrap)

        result[method] = MethodStats(
            method=method,
            method_name=method_entries[0].method_name,
            n=len(method_entries),
            f1_mean=float(f1s.mean()),
            f1_std=float(f1s.std(ddof=1)) if len(f1s) > 1 else 0.0,
            f1_ci_lo=f1_ci_lo,
            f1_ci_hi=f1_ci_hi,
            recall_mean=float(recalls.mean()),
            recall_std=float(recalls.std(ddof=1)) if len(recalls) > 1 else 0.0,
            recall_ci_lo=rec_ci_lo,
            recall_ci_hi=rec_ci_hi,
            precision_mean=float(precisions.mean()),
            precision_std=float(precisions.std(ddof=1)) if len(precisions) > 1 else 0.0,
            precision_ci_lo=prec_ci_lo,
            precision_ci_hi=prec_ci_hi,
            tokens_mean=float(tokens.mean()),
            time_mean=float(times.mean()),
            f1_values=f1s.tolist(),
            recall_values=recalls.tolist(),
            precision_values=precisions.tolist(),
        )

    return result


def pairwise_wilcoxon(
    entries: list[ResultEntry],
    baseline: str,
    method_stats: dict[str, MethodStats],
    metric: str = "f1",
) -> list[PairwiseTest]:
    """Run pairwise Wilcoxon signed-rank tests: baseline vs each other method.

    Uses paired tests on shared (task_id, run_dir) combinations.
    Applies Holm-Bonferroni correction for multiple comparisons.

    Args:
        metric: Which metric to compare. One of 'f1', 'recall', 'precision'.
    """
    # Build paired data: (task_id, run_dir) → {method: metric_value}
    paired: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for e in entries:
        value = getattr(e, metric)
        paired[(e.task_id, e.run_dir)][e.method] = value

    if baseline not in method_stats:
        return []

    comparisons = [m for m in method_stats if m != baseline]
    raw_tests: list[PairwiseTest] = []

    for other in comparisons:
        pairs_a, pairs_b = [], []
        for key, methods in paired.items():
            if baseline in methods and other in methods:
                pairs_a.append(methods[baseline])
                pairs_b.append(methods[other])

        a = np.array(pairs_a)
        b = np.array(pairs_b)
        n_pairs = len(a)

        stat_val, p_val = None, None
        d = 0.0
        diff_mean = 0.0

        if n_pairs >= 2:
            d = cohens_d(a, b)
            diff_mean = float(a.mean() - b.mean())
        if n_pairs >= 5 and not np.all(a == b):
            try:
                stat_val, p_val = sp_stats.wilcoxon(a, b, alternative="two-sided")
                stat_val, p_val = float(stat_val), float(p_val)
            except ValueError:
                pass

        raw_tests.append(
            PairwiseTest(
                method_a=baseline,
                method_b=other,
                n_pairs=n_pairs,
                wilcoxon_stat=stat_val,
                p_value=p_val,
                p_corrected=None,
                cohens_d=d,
                mean_diff=diff_mean,
                significant=False,
            )
        )

    # Holm-Bonferroni correction
    valid_tests = [t for t in raw_tests if t.p_value is not None]
    valid_tests.sort(key=lambda t: t.p_value)  # type: ignore[arg-type]
    m = len(valid_tests)
    for rank, test in enumerate(valid_tests):
        adjusted = test.p_value * (m - rank)  # type: ignore[operator]
        test.p_corrected = min(adjusted, 1.0)
        test.significant = test.p_corrected < 0.05

    return raw_tests


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _d_label(d: float) -> str:
    """Interpret Cohen's d magnitude."""
    ad = abs(d)
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


def _sig_stars(p: float | None) -> str:
    if p is None:
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def print_report(
    method_stats: dict[str, MethodStats],
    pairwise: list[PairwiseTest],
    baseline: str,
    filters: dict,
    metric: str = "f1",
) -> str:
    """Generate a human-readable statistical report."""
    metric_upper = metric.upper()
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append(f"PLOIDY STATISTICAL ANALYSIS REPORT  (metric: {metric_upper})")
    lines.append("=" * 72)

    active_filters = {k: v for k, v in filters.items() if v}
    if active_filters:
        lines.append(f"Filters: {active_filters}")
    lines.append(f"Baseline: {baseline}")
    lines.append(f"Primary metric: {metric_upper}")
    lines.append("")

    # --- Descriptive stats table ---
    lines.append("─" * 72)
    lines.append("1. DESCRIPTIVE STATISTICS (per method)")
    lines.append("─" * 72)

    def _get_primary(ms: MethodStats) -> tuple[float, float, float, float]:
        """Return (mean, std, ci_lo, ci_hi) for the chosen metric."""
        if metric == "recall":
            return ms.recall_mean, ms.recall_std, ms.recall_ci_lo, ms.recall_ci_hi
        if metric == "precision":
            return ms.precision_mean, ms.precision_std, ms.precision_ci_lo, ms.precision_ci_hi
        return ms.f1_mean, ms.f1_std, ms.f1_ci_lo, ms.f1_ci_hi

    header = (
        f"{'Method':<25s} {'N':>4s} {metric_upper:>6s} {'±std':>6s} {'95% CI':>15s} "
        f"{'Recall':>7s} {'Prec':>7s} {'F1':>6s}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for ms in sorted(method_stats.values(), key=lambda x: -_get_primary(x)[0]):
        m, s, lo, hi = _get_primary(ms)
        ci = f"[{lo:.3f}, {hi:.3f}]"
        lines.append(
            f"{ms.method:<25s} {ms.n:>4d} {m:>6.3f} {s:>6.3f} {ci:>15s} "
            f"{ms.recall_mean:>7.3f} {ms.precision_mean:>7.3f} {ms.f1_mean:>6.3f}"
        )

    lines.append("")

    # --- Pairwise tests ---
    delta_label = f"\u0394{metric_upper}"
    lines.append("─" * 72)
    lines.append(f"2. PAIRWISE TESTS on {metric_upper} ({baseline} vs each)")
    lines.append("─" * 72)
    header2 = (
        f"{'Comparison':<30s} {'N':>4s} {delta_label:>7s} {'d':>6s} {'|d|':>10s} "
        f"{'p':>8s} {'p_corr':>8s} {'Sig':>4s}"
    )
    lines.append(header2)
    lines.append("-" * len(header2))

    for t in sorted(pairwise, key=lambda x: -(x.mean_diff)):
        comp = f"{t.method_a} vs {t.method_b}"
        p_str = f"{t.p_value:.4f}" if t.p_value is not None else "n/a"
        pc_str = f"{t.p_corrected:.4f}" if t.p_corrected is not None else "n/a"
        sig = _sig_stars(t.p_corrected)
        lines.append(
            f"{comp:<30s} {t.n_pairs:>4d} {t.mean_diff:>+7.3f} {t.cohens_d:>6.2f} "
            f"{_d_label(t.cohens_d):>10s} {p_str:>8s} {pc_str:>8s} {sig:>4s}"
        )

    lines.append("")

    # --- Cost-accuracy ---
    lines.append("─" * 72)
    lines.append("3. COST-ACCURACY SUMMARY")
    lines.append("─" * 72)
    header3 = f"{'Method':<25s} {'F1':>6s} {'Tokens':>10s} {'Time(s)':>8s} {'F1/kTok':>8s}"
    lines.append(header3)
    lines.append("-" * len(header3))

    for ms in sorted(method_stats.values(), key=lambda x: -x.f1_mean):
        efficiency = (ms.f1_mean / (ms.tokens_mean / 1000)) if ms.tokens_mean > 0 else 0
        lines.append(
            f"{ms.method:<25s} {ms.f1_mean:>6.3f} {ms.tokens_mean:>10.0f} "
            f"{ms.time_mean:>8.1f} {efficiency:>8.4f}"
        )

    lines.append("")

    report = "\n".join(lines)
    print(report)
    return report


def generate_latex(
    method_stats: dict[str, MethodStats],
    pairwise: list[PairwiseTest],
    baseline: str,
) -> str:
    """Generate LaTeX table fragments for paper inclusion."""
    lines: list[str] = []

    # Main results table
    lines.append("% --- Main results table ---")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{Method comparison: F1, recall, precision with 95\\% bootstrap CI.}")
    lines.append("\\label{tab:main-results}")
    lines.append("\\begin{tabular}{lrcccc}")
    lines.append("\\toprule")
    lines.append("Method & $N$ & F1 & 95\\% CI & Recall & Precision \\\\")
    lines.append("\\midrule")

    for ms in sorted(method_stats.values(), key=lambda x: -x.f1_mean):
        name = ms.method_name.replace("_", "\\_")
        bf = (lambda s: f"\\textbf{{{s}}}") if ms.method == baseline else (lambda s: s)
        lines.append(
            f"{bf(name)} & {ms.n} & {bf(f'{ms.f1_mean:.3f}')} & "
            f"[{ms.f1_ci_lo:.3f}, {ms.f1_ci_hi:.3f}] & "
            f"{bf(f'{ms.recall_mean:.3f}')} & {ms.precision_mean:.3f} \\\\"
        )

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    lines.append("")

    # Pairwise significance table
    lines.append("% --- Pairwise significance table ---")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append(
        f"\\caption{{Pairwise Wilcoxon signed-rank tests: "
        f"{baseline} vs baselines (Holm-Bonferroni corrected).}}"
    )
    lines.append("\\label{tab:pairwise}")
    lines.append("\\begin{tabular}{lrcccc}")
    lines.append("\\toprule")
    lines.append(
        "Comparison & $N_{\\text{pairs}}$ & $\\Delta$F1 & Cohen's $d$ & $p_{\\text{corr}}$ & Sig. \\\\"
    )
    lines.append("\\midrule")

    for t in sorted(pairwise, key=lambda x: -(x.mean_diff)):
        name = t.method_b.replace("_", "\\_")
        pc = f"{t.p_corrected:.4f}" if t.p_corrected is not None else "---"
        sig = _sig_stars(t.p_corrected)
        lines.append(
            f"vs {name} & {t.n_pairs} & {t.mean_diff:+.3f} & "
            f"{t.cohens_d:.2f} ({_d_label(t.cohens_d)}) & {pc} & {sig} \\\\"
        )

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def export_json(
    method_stats: dict[str, MethodStats],
    pairwise: list[PairwiseTest],
    entries: list[ResultEntry],
) -> dict:
    """Export full analysis as JSON-serializable dict."""
    return {
        "summary": {
            method: {
                "n": ms.n,
                "f1_mean": round(ms.f1_mean, 4),
                "f1_std": round(ms.f1_std, 4),
                "f1_ci_95": [round(ms.f1_ci_lo, 4), round(ms.f1_ci_hi, 4)],
                "recall_mean": round(ms.recall_mean, 4),
                "precision_mean": round(ms.precision_mean, 4),
                "tokens_mean": round(ms.tokens_mean, 0),
                "time_mean": round(ms.time_mean, 1),
            }
            for method, ms in method_stats.items()
        },
        "pairwise_tests": [
            {
                "baseline": t.method_a,
                "comparison": t.method_b,
                "n_pairs": t.n_pairs,
                "mean_diff": round(t.mean_diff, 4),
                "cohens_d": round(t.cohens_d, 3),
                "effect_size": _d_label(t.cohens_d),
                "p_value": round(t.p_value, 6) if t.p_value is not None else None,
                "p_corrected": round(t.p_corrected, 6) if t.p_corrected is not None else None,
                "significant": t.significant,
            }
            for t in pairwise
        ],
        "total_entries": len(entries),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Statistical analysis of Ploidy experiments")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Directory containing experiment result folders",
    )
    parser.add_argument("--baseline", default="ploidy", help="Baseline method for comparisons")
    parser.add_argument(
        "--metric",
        choices=["f1", "recall", "precision"],
        default="f1",
        help="Primary metric for pairwise tests and CI (default: f1)",
    )
    parser.add_argument("--filter-effort", default=None, help="Filter by effort level")
    parser.add_argument("--filter-injection", default=None, help="Filter by injection mode")
    parser.add_argument("--filter-lang", default=None, help="Filter by language")
    parser.add_argument("--filter-model", default=None, help="Filter by model")
    parser.add_argument("--min-n", type=int, default=5, help="Minimum samples per method")
    parser.add_argument("--bootstrap-n", type=int, default=10000, help="Bootstrap iterations")
    parser.add_argument("--latex", action="store_true", help="Output LaTeX table fragments")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("-o", "--output", type=Path, help="Write report to file")
    args = parser.parse_args()

    filters = {
        "effort": args.filter_effort,
        "lang": args.filter_lang,
        "injection": args.filter_injection,
        "model": args.filter_model,
    }

    entries = load_results(args.results_dir, filters)
    if not entries:
        print("No valid results found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(entries)} valid results from {args.results_dir}")

    method_stats = compute_method_stats(entries, args.min_n, args.bootstrap_n)
    pairwise = pairwise_wilcoxon(entries, args.baseline, method_stats, metric=args.metric)

    report = print_report(method_stats, pairwise, args.baseline, filters, metric=args.metric)

    if args.latex:
        latex = generate_latex(method_stats, pairwise, args.baseline)
        print("\n" + latex)
        if args.output:
            (args.output.parent / (args.output.stem + ".tex")).write_text(latex)

    if args.json:
        data = export_json(method_stats, pairwise, entries)
        json_str = json.dumps(data, indent=2)
        if args.output:
            (args.output.parent / (args.output.stem + ".json")).write_text(json_str)
        else:
            print(json_str)

    if args.output:
        args.output.write_text(report)
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
