# Research Decisions Log

Records non-obvious choices with rationale. Append-only; don't rewrite history.

Format: `## YYYY-MM-DD -- <short title>` with **Context**, **Decision**, **Why**.

---

## 2026-04-20 -- Claude Code session extraction pipeline

**Context**: Past experiments ran via Claude Code `Bash` tool calls invoking
`experiments/src/run_experiment.py` (and siblings). The script normally writes
results to `experiments/results/<timestamp>/`, but several runs during
2026-04-07~16 produced no such directory — interrupted, errored, or redirected.
The only complete trace of those runs lives in
`~/.claude/projects/-Users-ren-IdeaProjects-*ploidy*/**/*.jsonl`, which is local
per-machine state, not version-controlled. "실험 내용이 매번 누락되는" 구조적 문제.

**Decision**: Introduce
[`experiments/src/extract_claude_sessions.py`](../experiments/src/extract_claude_sessions.py),
which walks every `~/.claude/projects/` jsonl, filters to entries with
Ploidy-relevant cwd or experiment-script invocations, and writes compact
per-session JSON summaries to
[`experiments/data/processed/claude_sessions/`](../experiments/data/processed/claude_sessions/)
plus `INDEX.json` and `INDEX.md`. Idempotent — re-run after every session.
First-run coverage (2026-04-20): 10 sessions, 44 experiment runs, 13 MCP calls,
3 errored.

**Why**: Claude Code conversation logs are the ground truth for what actually
ran, but they're large, scattered across multiple project-dir variants
(`-paper-ploidy`, `-Paper-ploidy-experiments`, `-ploidy`, `-paper`,
`-IdeaProjects`), and too raw to browse directly. The extraction turns that
substrate into a queryable research artifact so partial/failed runs stop
silently disappearing. The output fits under `data/processed/` (derived,
regenerable) per the template.

