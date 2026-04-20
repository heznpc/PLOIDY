# Claude Code session extracts

Derived from `~/.claude/projects/-Users-ren-IdeaProjects-*/**/*.jsonl` by
[`experiments/src/extract_claude_sessions.py`](../../../src/extract_claude_sessions.py).

## What this captures

Each `<project_dir>__<session_id>.json` file records the Ploidy-relevant activity
from one Claude Code conversation log:

- Bash calls that invoke experiment scripts (`run_experiment.py`,
  `run_diversity_experiment.py`, `analyze_stats.py`, `tasks_longcontext.py`,
  `tasks_extended.py`) with their paired stdout/stderr (head + tail, truncated).
- `mcp__ploidy__*` MCP tool invocations with arguments and responses.
- Session context: first user message preview, session title, modification time.

`INDEX.json` is the manifest. `INDEX.md` is the human-readable summary grouped by
date.

## Why it exists

Claude Code sessions run experiments via `Bash` tool calls; the Python script
normally persists results into `experiments/results/<timestamp>/`. When a run is
interrupted, fails, or is routed elsewhere, the only remaining trace is the
Claude Code conversation log — which is local, per-machine, and not
version-controlled. This pipeline distills those logs into a compact,
version-controllable summary so experiment activity is recoverable even when the
direct output is missing.

## Regenerating

Idempotent; re-run after each experiment session.

```bash
python3 experiments/src/extract_claude_sessions.py
```

The script clears and rewrites every per-session file (stable keys), updates
`INDEX.json`/`INDEX.md`, and reports totals to stdout.

## Scope filter

A session is included if either:
1. any entry's `cwd` contains `ploidy` (case-insensitive), or
2. any Bash command matches the experiment-script pattern.

This captures work done under unexpected cwds (sometimes `paper/` or plain
`IdeaProjects/`) while filtering out unrelated projects.
