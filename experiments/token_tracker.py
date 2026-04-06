"""Enhanced token tracking, checkpointing, and rate-limit management for Ploidy experiments.

Replaces the flat _token_tracker dict in run_experiment.py with a structured
TokenTracker that records per-call granularity, supports method-level aggregation,
checkpoint save/resume, KST-aware rate-limit wait scheduling, and cost-efficiency
metric computation.

Design goals:
  1. Zero-overhead for Tool-Fresh (annotates 0-token tool outputs separately)
  2. Exact tokens for API backends, char/4 estimates for CLI backends
  3. Checkpoint after every task completion — never lose more than one task of work
  4. KST refresh-window awareness (04:00/09:00/14:00/19:00 boundaries)

Usage:
    from token_tracker import TokenTracker, RateLimitScheduler, CheckpointManager

    tracker = TokenTracker()
    tracker.begin_method("ploidy")
    tracker.record_call(prompt_tokens=1200, completion_tokens=800, exact=True,
                        call_type="position", wall_seconds=4.2)
    tracker.record_tool_call(tool_name="grep", wall_seconds=0.3)
    tracker.end_method()
    summary = tracker.method_summary()
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# KST timezone (UTC+9, fixed offset — no DST)
# ---------------------------------------------------------------------------
KST = timezone(timedelta(hours=9))

# Claude Max/Pro token refresh boundaries in KST
_KST_REFRESH_HOURS = [4, 9, 14, 19]


# ---------------------------------------------------------------------------
# Per-call record
# ---------------------------------------------------------------------------


@dataclass
class CallRecord:
    """A single LLM or tool invocation within a method run."""

    call_type: str  # "position", "challenge", "convergence", "judge", "compress", "tool"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    exact: bool = False  # True = API-reported; False = char/4 estimate
    wall_seconds: float = 0.0
    tool_name: str | None = None  # set only for call_type="tool"
    timestamp: str = ""  # ISO 8601

    def __post_init__(self):
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        if not self.timestamp:
            self.timestamp = datetime.now(KST).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Per-method aggregate
# ---------------------------------------------------------------------------


@dataclass
class MethodTokenSummary:
    """Aggregated token metrics for one method execution on one task."""

    method_id: str
    task_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    tool_wall_seconds: float = 0.0
    total_wall_seconds: float = 0.0
    any_exact: bool = False
    calls: list[CallRecord] = field(default_factory=list)

    # Computed after scoring
    f1: float | None = None
    recall: float | None = None
    precision: float | None = None

    @property
    def estimated(self) -> bool:
        """True if ALL measurements are char/4 estimates (no exact API data)."""
        return not self.any_exact

    @property
    def f1_per_1k_tokens(self) -> float:
        """Primary efficiency metric: F1 score per 1,000 tokens consumed."""
        if self.total_tokens == 0 or self.f1 is None:
            return 0.0
        return self.f1 / (self.total_tokens / 1000)

    @property
    def recall_per_1k_tokens(self) -> float:
        """Recall per 1,000 tokens consumed."""
        if self.total_tokens == 0 or self.recall is None:
            return 0.0
        return self.recall / (self.total_tokens / 1000)

    def to_dict(self) -> dict:
        """Serialize for JSON output, including computed efficiency metrics."""
        d = {
            "method_id": self.method_id,
            "task_id": self.task_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "tool_wall_seconds": round(self.tool_wall_seconds, 2),
            "total_wall_seconds": round(self.total_wall_seconds, 2),
            "estimated": self.estimated,
            "f1": self.f1,
            "recall": self.recall,
            "precision": self.precision,
            "f1_per_1k_tokens": round(self.f1_per_1k_tokens, 6),
            "recall_per_1k_tokens": round(self.recall_per_1k_tokens, 6),
            "calls": [asdict(c) for c in self.calls],
        }
        return d


# ---------------------------------------------------------------------------
# TokenTracker — main class
# ---------------------------------------------------------------------------


class TokenTracker:
    """Per-call and per-method token usage tracker.

    Lifecycle:
        tracker.begin_method("ploidy", "task_01")
        tracker.record_call(...)       # repeated per LLM call
        tracker.record_tool_call(...)  # for Tool-Fresh zero-token operations
        tracker.end_method()
        summary = tracker.method_summary()
    """

    def __init__(self):
        self._current_method: str | None = None
        self._current_task: str | None = None
        self._current_calls: list[CallRecord] = []
        self._method_start_time: float = 0.0
        self._completed: list[MethodTokenSummary] = []

    def begin_method(self, method_id: str, task_id: str) -> None:
        """Start tracking a new method execution."""
        if self._current_method is not None:
            # Auto-close previous if caller forgot
            self.end_method()
        self._current_method = method_id
        self._current_task = task_id
        self._current_calls = []
        self._method_start_time = time.monotonic()

    def record_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        exact: bool = False,
        call_type: str = "llm",
        wall_seconds: float = 0.0,
    ) -> None:
        """Record a single LLM call's token usage.

        Args:
            prompt_tokens: Input tokens (exact from API, or char/4 estimate).
            completion_tokens: Output tokens.
            exact: True if the counts came from API response.usage.
            call_type: Semantic label ("position", "challenge", "convergence",
                       "judge", "compress").
            wall_seconds: Wall-clock duration of this specific call.
        """
        self._current_calls.append(
            CallRecord(
                call_type=call_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                exact=exact,
                wall_seconds=wall_seconds,
            )
        )

    def record_tool_call(
        self,
        tool_name: str,
        wall_seconds: float = 0.0,
    ) -> None:
        """Record a zero-token tool execution (Tool-Fresh).

        Tool-Fresh operations consume zero LLM tokens but have wall-clock cost.
        Recording them separately lets us compute tool_wall_seconds and annotate
        them distinctly in the per-call log.
        """
        self._current_calls.append(
            CallRecord(
                call_type="tool",
                prompt_tokens=0,
                completion_tokens=0,
                exact=True,  # tool calls are exact: 0 tokens, definitionally
                wall_seconds=wall_seconds,
                tool_name=tool_name,
            )
        )

    def end_method(self) -> MethodTokenSummary:
        """Finalize the current method and return its summary.

        Returns:
            Aggregated MethodTokenSummary for the just-completed method.
        """
        total_wall = time.monotonic() - self._method_start_time

        prompt_total = sum(c.prompt_tokens for c in self._current_calls)
        completion_total = sum(c.completion_tokens for c in self._current_calls)
        llm_calls = sum(1 for c in self._current_calls if c.call_type != "tool")
        tool_calls = sum(1 for c in self._current_calls if c.call_type == "tool")
        tool_wall = sum(c.wall_seconds for c in self._current_calls if c.call_type == "tool")
        any_exact = any(c.exact for c in self._current_calls if c.call_type != "tool")

        summary = MethodTokenSummary(
            method_id=self._current_method or "unknown",
            task_id=self._current_task or "unknown",
            prompt_tokens=prompt_total,
            completion_tokens=completion_total,
            total_tokens=prompt_total + completion_total,
            llm_calls=llm_calls,
            tool_calls=tool_calls,
            tool_wall_seconds=tool_wall,
            total_wall_seconds=total_wall,
            any_exact=any_exact,
            calls=list(self._current_calls),
        )
        self._completed.append(summary)
        self._current_method = None
        self._current_task = None
        self._current_calls = []
        return summary

    def attach_scores(
        self, method_id: str, task_id: str, f1: float, recall: float, precision: float
    ) -> None:
        """Attach scoring results to a completed method summary.

        Call this after judging to enable efficiency metric computation.
        """
        for s in reversed(self._completed):
            if s.method_id == method_id and s.task_id == task_id:
                s.f1 = f1
                s.recall = recall
                s.precision = precision
                return

    def all_summaries(self) -> list[MethodTokenSummary]:
        """Return all completed method summaries."""
        return list(self._completed)

    def method_aggregate(self) -> dict[str, dict]:
        """Compute per-method aggregates across all tasks.

        Returns:
            Dict keyed by method_id with mean tokens, mean F1, efficiency ratio.
        """
        from collections import defaultdict

        by_method: dict[str, list[MethodTokenSummary]] = defaultdict(list)
        for s in self._completed:
            by_method[s.method_id].append(s)

        result = {}
        for mid, summaries in sorted(by_method.items()):
            n = len(summaries)
            scored = [s for s in summaries if s.f1 is not None]
            mean_tokens = sum(s.total_tokens for s in summaries) / n
            mean_wall = sum(s.total_wall_seconds for s in summaries) / n
            mean_llm_calls = sum(s.llm_calls for s in summaries) / n
            mean_tool_calls = sum(s.tool_calls for s in summaries) / n
            mean_f1 = sum(s.f1 for s in scored) / len(scored) if scored else None
            mean_recall = sum(s.recall for s in scored) / len(scored) if scored else None
            mean_precision = sum(s.precision for s in scored) / len(scored) if scored else None

            eff = (mean_f1 / (mean_tokens / 1000)) if (mean_tokens > 0 and mean_f1) else None

            result[mid] = {
                "n_tasks": n,
                "mean_tokens": round(mean_tokens, 0),
                "mean_prompt_tokens": round(sum(s.prompt_tokens for s in summaries) / n, 0),
                "mean_completion_tokens": round(sum(s.completion_tokens for s in summaries) / n, 0),
                "mean_llm_calls": round(mean_llm_calls, 1),
                "mean_tool_calls": round(mean_tool_calls, 1),
                "mean_wall_seconds": round(mean_wall, 1),
                "mean_f1": round(mean_f1, 4) if mean_f1 is not None else None,
                "mean_recall": round(mean_recall, 4) if mean_recall is not None else None,
                "mean_precision": round(mean_precision, 4) if mean_precision is not None else None,
                "f1_per_1k_tokens": round(eff, 6) if eff is not None else None,
            }
        return result

    def marginal_analysis(self, base_method: str, combined_method: str) -> dict | None:
        """Compute marginal recall gained by adding a Fresh type.

        Compares base_method (e.g. "single") to combined_method (e.g. "ploidy")
        on shared tasks, computing the additional recall per additional 1K tokens.

        Returns:
            Dict with delta_recall, delta_tokens, marginal_recall_per_1k_tokens,
            or None if insufficient data.
        """
        from collections import defaultdict

        by_task: dict[str, dict[str, MethodTokenSummary]] = defaultdict(dict)
        for s in self._completed:
            if s.method_id in (base_method, combined_method) and s.recall is not None:
                by_task[s.task_id][s.method_id] = s

        pairs = [
            (v[base_method], v[combined_method])
            for v in by_task.values()
            if base_method in v and combined_method in v
        ]
        if not pairs:
            return None

        delta_recalls = [comb.recall - base.recall for base, comb in pairs]
        delta_tokens = [comb.total_tokens - base.total_tokens for base, comb in pairs]

        mean_dr = sum(delta_recalls) / len(delta_recalls)
        mean_dt = sum(delta_tokens) / len(delta_tokens)

        marginal = (mean_dr / (mean_dt / 1000)) if mean_dt > 0 else None

        return {
            "base_method": base_method,
            "combined_method": combined_method,
            "n_pairs": len(pairs),
            "mean_delta_recall": round(mean_dr, 4),
            "mean_delta_tokens": round(mean_dt, 0),
            "marginal_recall_per_1k_tokens": round(marginal, 6) if marginal is not None else None,
        }

    def pareto_frontier(self) -> list[dict]:
        """Compute the Pareto frontier of F1 vs total_tokens.

        Returns points where no other method achieves higher F1 at fewer tokens.
        """
        agg = self.method_aggregate()
        points = [
            {"method": mid, "mean_tokens": d["mean_tokens"], "mean_f1": d["mean_f1"]}
            for mid, d in agg.items()
            if d["mean_f1"] is not None
        ]
        # Sort by tokens ascending
        points.sort(key=lambda p: p["mean_tokens"])

        frontier = []
        best_f1 = -1.0
        for p in points:
            if p["mean_f1"] > best_f1:
                frontier.append(p)
                best_f1 = p["mean_f1"]
        return frontier

    def break_even_analysis(self, method_a: str, method_b: str) -> dict | None:
        """Determine at what token budget method_a outperforms method_b.

        Uses per-task data to find the crossover point. If method_a always
        outperforms (or never does), reports that instead.

        Returns:
            Dict with crossover information, or None if insufficient data.
        """
        from collections import defaultdict

        by_task: dict[str, dict[str, MethodTokenSummary]] = defaultdict(dict)
        for s in self._completed:
            if s.method_id in (method_a, method_b) and s.f1 is not None:
                by_task[s.task_id][s.method_id] = s

        pairs = [
            (v[method_a], v[method_b]) for v in by_task.values() if method_a in v and method_b in v
        ]
        if not pairs:
            return None

        a_wins = sum(1 for a, b in pairs if a.f1 > b.f1)
        b_wins = sum(1 for a, b in pairs if b.f1 > a.f1)
        ties = len(pairs) - a_wins - b_wins

        mean_tokens_a = sum(a.total_tokens for a, _ in pairs) / len(pairs)
        mean_tokens_b = sum(b.total_tokens for _, b in pairs) / len(pairs)
        mean_f1_a = sum(a.f1 for a, _ in pairs) / len(pairs)
        mean_f1_b = sum(b.f1 for _, b in pairs) / len(pairs)

        # Break-even token budget: the token level at which the more expensive
        # method's F1 advantage justifies its cost.  We report the extra tokens
        # needed per F1 point gained.
        delta_f1 = mean_f1_a - mean_f1_b
        delta_tokens = mean_tokens_a - mean_tokens_b
        tokens_per_f1_point = (delta_tokens / delta_f1) if delta_f1 != 0 else None

        return {
            "method_a": method_a,
            "method_b": method_b,
            "n_pairs": len(pairs),
            "a_wins": a_wins,
            "b_wins": b_wins,
            "ties": ties,
            "mean_tokens_a": round(mean_tokens_a, 0),
            "mean_tokens_b": round(mean_tokens_b, 0),
            "mean_f1_a": round(mean_f1_a, 4),
            "mean_f1_b": round(mean_f1_b, 4),
            "delta_tokens": round(delta_tokens, 0),
            "delta_f1": round(delta_f1, 4),
            "tokens_per_f1_point": round(tokens_per_f1_point, 0) if tokens_per_f1_point else None,
        }

    def export_json(self) -> dict:
        """Full JSON export for paper inclusion.

        Schema:
        {
            "generated_at": "2026-04-04T12:00:00+09:00",
            "per_task": [ MethodTokenSummary.to_dict(), ... ],
            "per_method": { method_id: aggregate_dict, ... },
            "pareto_frontier": [ {method, mean_tokens, mean_f1}, ... ],
            "marginal_analyses": [ ... ],  // populated by caller
        }
        """
        return {
            "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
            "per_task": [s.to_dict() for s in self._completed],
            "per_method": self.method_aggregate(),
            "pareto_frontier": self.pareto_frontier(),
        }


# ---------------------------------------------------------------------------
# Token estimation helper (matches existing run_experiment.py heuristic)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English, ~2 for CJK.

    Matches the existing _estimate_tokens in run_experiment.py for backward
    compatibility.
    """
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# CheckpointManager
# ---------------------------------------------------------------------------

# Checkpoint file format (JSON):
# {
#     "version": 1,
#     "run_id": "20260404_120000_effort-high_lang-en_inj-raw",
#     "status": "incomplete",           // "incomplete" | "complete"
#     "started_at": "2026-04-04T12:00:00+09:00",
#     "updated_at": "2026-04-04T14:32:00+09:00",
#     "config": {
#         "effort": "high", "language": "en", "injection_mode": "raw",
#         "model": "claude-opus-4-6", "backend": "claude",
#         "deep_n": 1, "fresh_n": 1,
#         "task_ids": [0, 1, 2, ...],
#         "method_ids": ["single", "ploidy", ...]
#     },
#     "completed_pairs": [              // list of (task_id, method_id) already done
#         {"task_id": "task_01", "method_id": "ploidy"},
#         ...
#     ],
#     "pending_pairs": [                // remaining work
#         {"task_id": "task_02", "method_id": "single"},
#         ...
#     ],
#     "token_summaries": [ ... ],       // TokenTracker serialized data
#     "last_error": null | "rate limit at 14:00 KST"
# }


@dataclass
class CheckpointState:
    """Serializable checkpoint for experiment resume."""

    version: int = 1
    run_id: str = ""
    status: str = "incomplete"  # "incomplete" | "complete"
    started_at: str = ""
    updated_at: str = ""
    config: dict = field(default_factory=dict)
    completed_pairs: list[dict] = field(default_factory=list)
    pending_pairs: list[dict] = field(default_factory=list)
    token_summaries: list[dict] = field(default_factory=list)
    last_error: str | None = None


class CheckpointManager:
    """Saves and loads experiment checkpoints for resume-from-interruption.

    Writes two marker files alongside the checkpoint JSON:
        results_dir/.incomplete  — created at start, removed on completion
        results_dir/.complete    — created when all tasks finish

    The scheduled trigger (cron) checks for .incomplete to decide whether
    to resume a run after a rate-limit sleep.
    """

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self._checkpoint_path = results_dir / "checkpoint.json"
        self._incomplete_marker = results_dir / ".incomplete"
        self._complete_marker = results_dir / ".complete"

    def init_checkpoint(
        self,
        run_id: str,
        config: dict,
        all_pairs: list[tuple[str, str]],
    ) -> CheckpointState:
        """Create initial checkpoint, writing .incomplete marker.

        Args:
            run_id: Directory name / run identifier.
            config: Experiment configuration dict.
            all_pairs: List of (task_id, method_id) tuples to execute.

        Returns:
            Fresh CheckpointState.
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(KST).isoformat(timespec="seconds")

        state = CheckpointState(
            run_id=run_id,
            status="incomplete",
            started_at=now,
            updated_at=now,
            config=config,
            completed_pairs=[],
            pending_pairs=[{"task_id": t, "method_id": m} for t, m in all_pairs],
        )
        self._write(state)
        self._incomplete_marker.touch()
        if self._complete_marker.exists():
            self._complete_marker.unlink()
        return state

    def load_checkpoint(self) -> CheckpointState | None:
        """Load existing checkpoint if present and incomplete.

        Returns:
            CheckpointState if resumable, None if no checkpoint or already complete.
        """
        if not self._checkpoint_path.exists():
            return None
        try:
            data = json.loads(self._checkpoint_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if data.get("status") == "complete":
            return None

        state = CheckpointState(
            version=data.get("version", 1),
            run_id=data.get("run_id", ""),
            status=data.get("status", "incomplete"),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
            config=data.get("config", {}),
            completed_pairs=data.get("completed_pairs", []),
            pending_pairs=data.get("pending_pairs", []),
            token_summaries=data.get("token_summaries", []),
            last_error=data.get("last_error"),
        )
        return state

    def mark_completed(
        self,
        task_id: str,
        method_id: str,
        token_summary: dict | None = None,
    ) -> None:
        """Mark a (task_id, method_id) pair as completed and save checkpoint.

        Called after each task-method execution finishes successfully.
        """
        state = self.load_checkpoint()
        if state is None:
            return

        pair = {"task_id": task_id, "method_id": method_id}
        state.completed_pairs.append(pair)
        state.pending_pairs = [
            p
            for p in state.pending_pairs
            if not (p["task_id"] == task_id and p["method_id"] == method_id)
        ]
        if token_summary:
            state.token_summaries.append(token_summary)
        state.updated_at = datetime.now(KST).isoformat(timespec="seconds")

        if not state.pending_pairs:
            state.status = "complete"

        self._write(state)

        if state.status == "complete":
            self._finalize()

    def mark_error(self, error_msg: str) -> None:
        """Record the last error (e.g., rate limit hit) in checkpoint."""
        state = self.load_checkpoint()
        if state is None:
            return
        state.last_error = error_msg
        state.updated_at = datetime.now(KST).isoformat(timespec="seconds")
        self._write(state)

    def remaining_pairs(self) -> list[tuple[str, str]]:
        """Return list of (task_id, method_id) pairs still pending."""
        state = self.load_checkpoint()
        if state is None:
            return []
        return [(p["task_id"], p["method_id"]) for p in state.pending_pairs]

    def is_incomplete(self) -> bool:
        """Check if this results directory has an incomplete run."""
        return self._incomplete_marker.exists()

    def _finalize(self) -> None:
        """Mark run as complete: remove .incomplete, create .complete."""
        if self._incomplete_marker.exists():
            self._incomplete_marker.unlink()
        self._complete_marker.touch()

    def _write(self, state: CheckpointState) -> None:
        """Write checkpoint state to disk atomically."""
        tmp = self._checkpoint_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False))
        tmp.rename(self._checkpoint_path)


# ---------------------------------------------------------------------------
# RateLimitScheduler
# ---------------------------------------------------------------------------

# Rate-limit error patterns from various backends
_RATE_LIMIT_PATTERNS = [
    # Claude CLI: "You've hit your limit · resets 6am (Asia/Seoul)"
    re.compile(r"hit your limit", re.IGNORECASE),
    # Generic: "Rate limit exceeded. Try again in 300 seconds"
    re.compile(r"rate limit", re.IGNORECASE),
    # HTTP 429 with Retry-After header surfaced in error messages
    re.compile(r"429", re.IGNORECASE),
    # Anthropic API: "rate_limit_error"
    re.compile(r"rate_limit_error", re.IGNORECASE),
    # OpenAI: "Rate limit reached for"
    re.compile(r"rate limit reached", re.IGNORECASE),
    # Generic: "quota exceeded" / "capacity" / "overloaded"
    re.compile(r"quota exceeded|capacity|overloaded|too many requests|503|502", re.IGNORECASE),
    # Usage exceeded
    re.compile(r"usage.*exceeded|exceeded.*usage", re.IGNORECASE),
]

# More specific pattern to extract the Claude CLI reset hour
_CLAUDE_RESET_HOUR_RE = re.compile(r"resets\s+(\d{1,2})(am|pm)", re.IGNORECASE)

# Pattern to extract explicit wait seconds
_EXPLICIT_SECONDS_RE = re.compile(r"(\d+)\s*seconds?", re.IGNORECASE)


class RateLimitScheduler:
    """KST-aware rate limit detection and wait-time calculation.

    Claude Max/Pro refreshes tokens at KST 04:00, 09:00, 14:00, 19:00
    (5-hour windows). When a rate limit is hit, this computes the optimal
    wait time to the next refresh boundary.
    """

    @staticmethod
    def is_rate_limit_error(error_msg: str) -> bool:
        """Detect whether an error message indicates a rate limit."""
        return any(p.search(error_msg) for p in _RATE_LIMIT_PATTERNS)

    @staticmethod
    def seconds_until_next_refresh(now: datetime | None = None) -> int:
        """Compute seconds until the next KST token refresh boundary.

        Refresh times: 04:00, 09:00, 14:00, 19:00 KST.

        Args:
            now: Current time (defaults to now in KST). Accepts any timezone.

        Returns:
            Seconds to wait (minimum 60, maximum ~5 hours).
        """
        if now is None:
            now = datetime.now(KST)
        else:
            now = now.astimezone(KST)

        current_hour = now.hour
        current_minute = now.minute

        for refresh_hour in _KST_REFRESH_HOURS:
            if refresh_hour > current_hour or (refresh_hour == current_hour and current_minute < 1):
                target = now.replace(hour=refresh_hour, minute=1, second=0, microsecond=0)
                wait = int((target - now).total_seconds())
                return max(wait, 60)

        # Past 19:00 KST — next refresh is 04:01 tomorrow
        tomorrow = now + timedelta(days=1)
        target = tomorrow.replace(hour=4, minute=1, second=0, microsecond=0)
        wait = int((target - now).total_seconds())
        return max(wait, 60)

    @staticmethod
    def parse_wait_from_error(error_msg: str) -> int:
        """Extract wait time from a rate-limit error message.

        Tries in order:
        1. Claude CLI reset hour ("resets 6am") — compute to that KST hour
        2. Explicit seconds ("try again in 300 seconds")
        3. Fallback to next KST refresh boundary

        Args:
            error_msg: The error string from a failed API/CLI call.

        Returns:
            Seconds to wait (minimum 60).
        """
        # 1. Claude CLI: "resets Xam/pm"
        match = _CLAUDE_RESET_HOUR_RE.search(error_msg)
        if match:
            hour = int(match.group(1))
            ampm = match.group(2).lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

            now = datetime.now(KST)
            target = now.replace(hour=hour, minute=1, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            wait = int((target - now).total_seconds())
            return max(wait, 60)

        # 2. Explicit seconds in error
        sec_match = _EXPLICIT_SECONDS_RE.search(error_msg)
        if sec_match:
            return max(int(sec_match.group(1)), 60)

        # 3. Fallback: wait until next KST refresh
        return RateLimitScheduler.seconds_until_next_refresh()

    @staticmethod
    def format_wait_message(wait_seconds: int) -> str:
        """Format a human-readable wait message with resume time.

        Returns something like:
            "Rate limit hit at 14:32 KST. Sleeping 268min until 19:01 KST refresh."
        """
        now = datetime.now(KST)
        resume_at = now + timedelta(seconds=wait_seconds)
        return (
            f"Rate limit hit at {now.strftime('%H:%M')} KST. "
            f"Sleeping {wait_seconds // 60}min "
            f"until {resume_at.strftime('%H:%M')} KST refresh."
        )


# ---------------------------------------------------------------------------
# Results JSON schema (for documentation / validation)
# ---------------------------------------------------------------------------

RESULTS_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Ploidy Experiment Results",
    "type": "object",
    "required": ["generated_at", "per_task", "per_method"],
    "properties": {
        "generated_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601 timestamp when results were generated",
        },
        "per_task": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["method_id", "task_id", "total_tokens", "llm_calls"],
                "properties": {
                    "method_id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "prompt_tokens": {"type": "integer"},
                    "completion_tokens": {"type": "integer"},
                    "total_tokens": {"type": "integer"},
                    "llm_calls": {"type": "integer"},
                    "tool_calls": {"type": "integer"},
                    "tool_wall_seconds": {"type": "number"},
                    "total_wall_seconds": {"type": "number"},
                    "estimated": {"type": "boolean"},
                    "f1": {"type": ["number", "null"]},
                    "recall": {"type": ["number", "null"]},
                    "precision": {"type": ["number", "null"]},
                    "f1_per_1k_tokens": {"type": "number"},
                    "recall_per_1k_tokens": {"type": "number"},
                    "calls": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "call_type": {
                                    "type": "string",
                                    "enum": [
                                        "position",
                                        "challenge",
                                        "convergence",
                                        "judge",
                                        "compress",
                                        "tool",
                                        "llm",
                                    ],
                                },
                                "prompt_tokens": {"type": "integer"},
                                "completion_tokens": {"type": "integer"},
                                "total_tokens": {"type": "integer"},
                                "exact": {"type": "boolean"},
                                "wall_seconds": {"type": "number"},
                                "tool_name": {"type": ["string", "null"]},
                                "timestamp": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                },
            },
        },
        "per_method": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "n_tasks": {"type": "integer"},
                    "mean_tokens": {"type": "number"},
                    "mean_prompt_tokens": {"type": "number"},
                    "mean_completion_tokens": {"type": "number"},
                    "mean_llm_calls": {"type": "number"},
                    "mean_tool_calls": {"type": "number"},
                    "mean_wall_seconds": {"type": "number"},
                    "mean_f1": {"type": ["number", "null"]},
                    "mean_recall": {"type": ["number", "null"]},
                    "mean_precision": {"type": ["number", "null"]},
                    "f1_per_1k_tokens": {"type": ["number", "null"]},
                },
            },
        },
        "pareto_frontier": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "mean_tokens": {"type": "number"},
                    "mean_f1": {"type": "number"},
                },
            },
        },
        "marginal_analyses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "base_method": {"type": "string"},
                    "combined_method": {"type": "string"},
                    "n_pairs": {"type": "integer"},
                    "mean_delta_recall": {"type": "number"},
                    "mean_delta_tokens": {"type": "number"},
                    "marginal_recall_per_1k_tokens": {"type": ["number", "null"]},
                },
            },
        },
    },
}
