#!/usr/bin/env python3
"""Extract Ploidy-relevant activity from Claude Code session logs.

Source: ~/.claude/projects/-Users-ren-IdeaProjects-*ploidy* (3 variants)
Output: experiments/data/raw/claude_sessions/
  - One JSON per source .jsonl with experiment activity
  - INDEX.json: machine-readable manifest
  - INDEX.md: human-readable summary grouped by date

What is extracted per session:
  - Bash calls executing experiment scripts (run_experiment.py, run_diversity_experiment.py,
    analyze_stats.py, tasks_longcontext.py, tasks_extended.py)
  - MCP tool calls to mcp__ploidy__* (any)
  - Command, paired stdout/stderr (head + tail, truncated), exit status, timestamp
  - First user message (first 500 chars) for context
  - Session title when present

Idempotent: safe to re-run. Overwrites per-session outputs and the index.

Run from repo root:
    python3 experiments/src/extract_claude_sessions.py

The goal is to make experiment activity recoverable even when the direct script
output (experiments/results/<timestamp>/) is missing or incomplete.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

_CLAUDE_PROJECTS_ROOT = Path.home() / ".claude/projects"
# Scan every project dir and filter by actual Ploidy activity (cwd contains 'ploidy',
# or any Bash call matches the experiment-script pattern). Experiments sometimes ran
# under unexpected cwds (e.g. paper/, IdeaProjects/), so narrow whitelists miss them.
PROJECT_DIRS = (
    sorted(p for p in _CLAUDE_PROJECTS_ROOT.glob("-Users-ren-*") if p.is_dir())
    if _CLAUDE_PROJECTS_ROOT.exists()
    else []
)

EXPERIMENT_SCRIPTS = (
    "run_experiment",
    "run_diversity_experiment",
    "analyze_stats",
    "tasks_longcontext",
    "tasks_extended",
)
EXPERIMENT_CMD_PAT = re.compile(
    r"python[0-9]*\b[^|;&\n]*?\b(" + "|".join(EXPERIMENT_SCRIPTS) + r")\.py"
)
PLOIDY_MCP_PAT = re.compile(r"^mcp__ploidy__")

TRUNCATE_HEAD = 3000
TRUNCATE_TAIL = 3000

REPO_ROOT = Path(__file__).resolve().parents[2]
# Extracts are derived from the external jsonl logs; belong under data/processed/
# per the template (data/raw/ is append-only / immutable inputs).
OUT_DIR = REPO_ROOT / "experiments/data/processed/claude_sessions"


def iter_jsonl(path: Path):
    with path.open(errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def truncate(text: str) -> dict:
    n = len(text)
    if n <= TRUNCATE_HEAD + TRUNCATE_TAIL:
        return {"head": text, "tail": None, "length": n}
    return {"head": text[:TRUNCATE_HEAD], "tail": text[-TRUNCATE_TAIL:], "length": n}


def extract_tool_result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for rc in content:
            if isinstance(rc, dict) and rc.get("type") == "text":
                parts.append(rc.get("text", ""))
        return "".join(parts)
    return ""


def classify_script(cmd: str) -> str | None:
    m = EXPERIMENT_CMD_PAT.search(cmd)
    return m.group(1) if m else None


def extract_from_jsonl(jsonl_path: Path) -> dict | None:
    pending: dict[str, dict] = {}
    tool_calls: list[dict] = []
    first_user_message: str | None = None
    session_title: str | None = None
    has_ploidy_cwd: bool = False

    for d in iter_jsonl(jsonl_path):
        cwd = d.get("cwd") or ""
        if cwd and "ploidy" in cwd.lower():
            has_ploidy_cwd = True
        t = d.get("type")
        if t == "custom-title":
            session_title = d.get("title") or session_title
            continue

        msg = d.get("message")
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")

        if first_user_message is None and role == "user":
            if isinstance(content, str):
                first_user_message = content[:500]
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        first_user_message = (item.get("text") or "")[:500]
                        break

        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict):
                continue
            kind = item.get("type")
            if kind == "tool_use":
                name = item.get("name", "")
                tool_use_id = item.get("id")
                inp = item.get("input") if isinstance(item.get("input"), dict) else {}
                if name == "Bash":
                    cmd = inp.get("command", "")
                    script = classify_script(cmd)
                    if script:
                        pending[tool_use_id] = {
                            "kind": "bash_experiment",
                            "script": script,
                            "command": cmd,
                            "ts": d.get("timestamp"),
                        }
                elif PLOIDY_MCP_PAT.match(name):
                    pending[tool_use_id] = {
                        "kind": "mcp_ploidy",
                        "tool": name,
                        "args": inp,
                        "ts": d.get("timestamp"),
                    }
            elif kind == "tool_result":
                tool_use_id = item.get("tool_use_id")
                rec = pending.pop(tool_use_id, None)
                if rec is None:
                    continue
                text = extract_tool_result_text(item.get("content"))
                rec["result"] = truncate(text)
                rec["is_error"] = bool(item.get("is_error"))
                tool_calls.append(rec)

    # Orphan tool_use (no matching result): still record
    for rec in pending.values():
        rec["result"] = None
        rec["is_error"] = None
        rec["orphan"] = True
        tool_calls.append(rec)

    # Keep only sessions that either ran a Ploidy-related experiment command
    # or clearly operated inside a ploidy cwd. Skips noise from unrelated projects.
    if not tool_calls and not has_ploidy_cwd:
        return None
    if not tool_calls:
        return None

    tool_calls.sort(key=lambda r: r.get("ts") or "")
    mtime = datetime.fromtimestamp(jsonl_path.stat().st_mtime, tz=UTC)
    rel_source = (
        str(jsonl_path.relative_to(Path.home()))
        if jsonl_path.is_relative_to(Path.home())
        else str(jsonl_path)
    )

    return {
        "session_id": jsonl_path.stem,
        "source": rel_source,
        "project_dir": jsonl_path.parent.name,
        "mtime": mtime.isoformat(),
        "session_title": session_title,
        "first_user_message": first_user_message,
        "n_experiment_runs": sum(1 for r in tool_calls if r["kind"] == "bash_experiment"),
        "n_mcp_ploidy_calls": sum(1 for r in tool_calls if r["kind"] == "mcp_ploidy"),
        "n_errors": sum(1 for r in tool_calls if r.get("is_error")),
        "tool_calls": tool_calls,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clear previous extracts (idempotent, avoids stale files for renamed sessions)
    for f in OUT_DIR.glob("*.json"):
        if f.name != "INDEX.json":
            f.unlink()

    all_entries: list[dict] = []
    skipped = 0
    for project_dir in PROJECT_DIRS:
        if not project_dir.exists():
            continue
        for jsonl in project_dir.rglob("*.jsonl"):
            try:
                entry = extract_from_jsonl(jsonl)
            except Exception as e:  # noqa: BLE001
                print(f"[err] {jsonl}: {e}", file=sys.stderr)
                skipped += 1
                continue
            if entry is None:
                continue
            # Disambiguate session_id across project_dirs
            out_key = f"{entry['project_dir']}__{entry['session_id']}"
            out_path = OUT_DIR / f"{out_key}.json"
            entry["out_key"] = out_key
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
            all_entries.append(entry)

    all_entries.sort(key=lambda e: e["mtime"], reverse=True)

    by_date: dict[str, list[dict]] = {}
    for e in all_entries:
        by_date.setdefault(e["mtime"][:10], []).append(e)

    index = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_dirs": [str(p) for p in PROJECT_DIRS if p.exists()],
        "totals": {
            "sessions_with_activity": len(all_entries),
            "experiment_runs": sum(e["n_experiment_runs"] for e in all_entries),
            "mcp_ploidy_calls": sum(e["n_mcp_ploidy_calls"] for e in all_entries),
            "errored_calls": sum(e["n_errors"] for e in all_entries),
        },
        "dates": sorted(by_date.keys(), reverse=True),
        "by_date_counts": {d: len(v) for d, v in sorted(by_date.items(), reverse=True)},
        "entries": [
            {
                "out_key": e["out_key"],
                "session_id": e["session_id"],
                "project_dir": e["project_dir"],
                "mtime": e["mtime"],
                "n_experiment_runs": e["n_experiment_runs"],
                "n_mcp_ploidy_calls": e["n_mcp_ploidy_calls"],
                "n_errors": e["n_errors"],
                "session_title": e["session_title"],
                "first_user_message_preview": (e["first_user_message"] or "").replace("\n", " ")[
                    :140
                ],
            }
            for e in all_entries
        ],
    }
    with (OUT_DIR / "INDEX.json").open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    md = [
        "# Claude Code Session Extraction Index",
        "",
        f"Generated: {index['generated_at']}",
        "",
        f"- Sessions with experiment activity: **{index['totals']['sessions_with_activity']}**",
        f"- Bash experiment-script runs: **{index['totals']['experiment_runs']}**",
        f"- `mcp__ploidy__*` tool calls: **{index['totals']['mcp_ploidy_calls']}**",
        f"- Errored calls: **{index['totals']['errored_calls']}**",
        "",
        "Per-session extracts live alongside this file as `{project_dir}__{session_id}.json`.",
        "",
        "## Activity by date (most recent first)",
        "",
    ]
    for date in sorted(by_date.keys(), reverse=True):
        sessions = by_date[date]
        runs = sum(s["n_experiment_runs"] for s in sessions)
        mcp = sum(s["n_mcp_ploidy_calls"] for s in sessions)
        md.append(f"### {date} — {len(sessions)} session(s), {runs} runs, {mcp} MCP calls")
        for s in sorted(sessions, key=lambda x: x["mtime"]):
            title = s["session_title"] or (s["first_user_message"] or "").replace("\n", " ")[:100]
            md.append(
                f"- `{s['session_id'][:8]}` ({s['project_dir']}) — {s['n_experiment_runs']} runs, {s['n_mcp_ploidy_calls']} mcp, {s['n_errors']} err — {title[:120]}"
            )
        md.append("")

    with (OUT_DIR / "INDEX.md").open("w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Extracted {len(all_entries)} sessions (skipped {skipped} on error)")
    print(f"Totals: {index['totals']}")
    print(f"Output: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
