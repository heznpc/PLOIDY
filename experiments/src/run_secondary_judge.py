#!/usr/bin/env python3
"""Re-evaluate existing experiment outputs with a second judge model.

Pre-registered (planning/decisions.md, 2026-05-21) anti-LLM-as-judge gate
for the H2 replication: a 5-task subset of any results directory is
re-scored by a non-Claude judge (Gemini 3.1 Pro by default, GPT-5.4
optional) and Cohen's kappa is computed over the per-ground-truth-issue
verdicts {FOUND, PARTIAL, MISSED}.

The subset is chosen *before* the secondary judge is invoked, deterministically
by sorted filename, to remove the post-hoc cherry-pick failure mode. The
secondary judge model is chosen at script-invocation time (``--secondary-judge``),
not at result-inspection time.

A reported ``kappa < kappa_threshold`` (default 0.40) flags the H2 verdict
as judge-invalid per the pre-registration. The script exits non-zero in
that case so CI / batch drivers can treat the gate as a hard stop.

Usage::

    python src/run_secondary_judge.py \\
        --results-dir experiments/results/<timestamp_dir> \\
        --secondary-judge gemini-3.1-pro \\
        --backend gemini \\
        --out experiments/results/<timestamp_dir>/secondary_judge.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path


JUDGE_PROMPT_TEMPLATE = (
    "You are an expert judge evaluating a code review / architecture analysis.\n\n"
    "GROUND TRUTH issues (known correct answers):\n{gt_list}\n\n"
    "REVIEWER OUTPUT:\n{output}\n\n"
    "For EACH ground truth issue, determine:\n"
    "- FOUND: clearly identified (even if worded differently)\n"
    "- PARTIAL: hinted at but not fully articulated\n"
    "- MISSED: not identified\n\n"
    "Also count additional valid issues NOT in ground truth (bonus findings).\n\n"
    "Respond in this EXACT JSON format and nothing else:\n"
    '{{"scores": [{{"ground_truth_index": 1, "verdict": "FOUND", "evidence": "..."}}, ...], '
    '"bonus_findings": 0, "summary": "..."}}'
)


VALID_VERDICTS: tuple[str, ...] = ("FOUND", "PARTIAL", "MISSED")


def call_gemini_cli(prompt: str, model: str, timeout: int = 600) -> str:
    cmd = ["gemini", "-p", prompt]
    if model and model != "gemini-default":
        cmd.extend(["-m", model])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"gemini CLI error: {r.stderr.strip()}")
    return r.stdout.strip()


def call_openai_compat(prompt: str, model: str, timeout: int = 600) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("openai package required for --backend openai") from exc
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "not-needed"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        timeout=timeout,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return (response.choices[0].message.content or "").strip()


BACKENDS = {
    "gemini": call_gemini_cli,
    "openai": call_openai_compat,
}


def parse_judgment(text: str) -> dict:
    """Best-effort JSON extraction from a judge's free-text response."""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError) as exc:
        return {"raw_judgment": text, "parse_error": True, "exc": str(exc)}


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa over {FOUND, PARTIAL, MISSED} verdict pairs.

    Returns float('nan') for the degenerate single-class case.
    """
    if not pairs:
        return float("nan")
    total = len(pairs)
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / total
    c1 = Counter(a for a, _ in pairs)
    c2 = Counter(b for _, b in pairs)
    pe = sum((c1[v] / total) * (c2[v] / total) for v in VALID_VERDICTS)
    if abs(1.0 - pe) < 1e-9:
        return float("nan")
    return (po - pe) / (1.0 - pe)


def load_result_files(results_dir: Path) -> list[Path]:
    """Return result JSONs in deterministic (sorted) order, excluding summary.json."""
    return sorted(p for p in results_dir.glob("*.json") if p.name != "summary.json")


def _verdict_map(scores: list[dict]) -> dict[int, str]:
    """Build {ground_truth_index -> verdict} from a judgment.scores list."""
    out: dict[int, str] = {}
    for s in scores or []:
        idx = s.get("ground_truth_index")
        verdict = s.get("verdict")
        if isinstance(idx, int) and verdict in VALID_VERDICTS:
            out[idx] = verdict
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Run directory containing the per-(method,task) JSONs to re-judge",
    )
    parser.add_argument(
        "--secondary-judge",
        required=True,
        help="Model id for the secondary judge (e.g. gemini-3.1-pro, gpt-5.4)",
    )
    parser.add_argument(
        "--backend",
        choices=tuple(BACKENDS.keys()),
        default="gemini",
        help="How to invoke the secondary judge (default: gemini CLI)",
    )
    parser.add_argument(
        "--n-subset",
        type=int,
        default=5,
        help="Number of results to re-judge (default 5, the pre-registered subset)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Where to write the JSON report (default: <results-dir>/secondary_judge.json)",
    )
    parser.add_argument(
        "--kappa-threshold",
        type=float,
        default=0.40,
        help="Below this, the H2 verdict is INVALID per pre-registration (default 0.40)",
    )
    args = parser.parse_args()

    results_dir: Path = args.results_dir
    if not results_dir.is_dir():
        print(f"results dir not found: {results_dir}", file=sys.stderr)
        return 2

    files = load_result_files(results_dir)
    if not files:
        print("no result JSONs found", file=sys.stderr)
        return 2
    subset = files[: args.n_subset]
    print(f"Re-judging {len(subset)}/{len(files)} files from {results_dir}")
    print(f"Secondary judge: {args.secondary_judge} via {args.backend}")
    call = BACKENDS[args.backend]

    pairs: list[tuple[str, str]] = []
    per_file: list[dict] = []
    for fp in subset:
        try:
            d = json.loads(fp.read_text())
        except Exception as exc:
            print(f"skip {fp.name}: {exc}", file=sys.stderr)
            per_file.append({"file": fp.name, "error": f"read: {exc}"})
            continue

        task = d.get("task") or {}
        ground_truth = list(task.get("ground_truth") or [])
        if not ground_truth:
            per_file.append({"file": fp.name, "skipped": "no ground_truth in task"})
            continue
        primary_judgment = d.get("judgment") or {}
        primary_scores = _verdict_map(primary_judgment.get("scores") or [])

        gt_list = "\n".join(f"  {i + 1}. {gt}" for i, gt in enumerate(ground_truth))
        prompt = JUDGE_PROMPT_TEMPLATE.format(gt_list=gt_list, output=d.get("output", ""))
        try:
            raw = call(prompt, args.secondary_judge)
        except Exception as exc:
            print(f"  {fp.name}: judge call FAILED: {exc}", file=sys.stderr)
            per_file.append({"file": fp.name, "error": f"judge: {exc}"})
            continue

        secondary_judgment = parse_judgment(raw)
        secondary_scores = _verdict_map(secondary_judgment.get("scores") or [])

        matched = 0
        for gt_idx in range(1, len(ground_truth) + 1):
            v1 = primary_scores.get(gt_idx)
            v2 = secondary_scores.get(gt_idx)
            if v1 and v2:
                pairs.append((v1, v2))
                matched += 1

        per_file.append(
            {
                "file": fp.name,
                "task_id": d.get("task_id"),
                "method": d.get("method"),
                "primary_judge_model": d.get("model"),
                "secondary_judge_model": args.secondary_judge,
                "primary": primary_scores,
                "secondary": secondary_scores,
                "n_paired": matched,
            }
        )
        print(f"  {fp.name}: matched {matched}/{len(ground_truth)} verdicts")

    kappa = cohen_kappa(pairs)
    if math.isnan(kappa):
        h2_gate = "UNDEFINED"
    elif kappa >= args.kappa_threshold:
        h2_gate = "VALID"
    else:
        h2_gate = "INVALID"

    report = {
        "results_dir": str(results_dir),
        "n_files_attempted": len(subset),
        "n_files_used": sum(1 for r in per_file if r.get("n_paired")),
        "n_paired_verdicts": len(pairs),
        "secondary_judge": args.secondary_judge,
        "secondary_backend": args.backend,
        "kappa": kappa,
        "kappa_threshold": args.kappa_threshold,
        "h2_judge_gate": h2_gate,
        "per_file": per_file,
    }
    out = args.out or (results_dir / "secondary_judge.json")
    out.write_text(json.dumps(report, indent=2))
    print()
    if math.isnan(kappa):
        print("Cohen's kappa = nan (degenerate single-class case)")
    else:
        print(f"Cohen's kappa = {kappa:.3f} (gate threshold {args.kappa_threshold})")
    print(f"Pre-reg verdict: {h2_gate}")
    print(f"Report → {out}")

    if h2_gate == "VALID":
        return 0
    if h2_gate == "INVALID":
        return 1
    return 3  # UNDEFINED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
