# Ploidy Expert Review -- 2026-03-15

Five expert agents independently reviewed the Ploidy codebase. This document consolidates their findings.

| Reviewer | Role |
|----------|------|
| 1 | Security Engineer |
| 2 | MCP Integration Specialist |
| 3 | Senior Python Architect |
| 4 | Product / Developer Experience |
| 5 | AI Research Scientist |

---

## 1. Security Audit

### CRITICAL: None

Pre-alpha stubs -- no production-facing surface yet.

### HIGH (4 issues)

| ID | Issue | Detail |
|----|-------|--------|
| H1 | SQL injection risk | `store.py` accepts raw strings; no parameterized query pattern established |
| H2 | No session authentication | Any MCP client can impersonate either role |
| H3 | Context isolation breach | Fresh session can access experienced session's context via `get_session()` |
| H4 | Unpinned dependencies | `mcp`, `aiosqlite` unpinned -- supply chain risk |

### MEDIUM (6 issues)

| ID | Issue |
|----|-------|
| M1 | `db_path` path traversal risk |
| M2 | `role` field is free-form string, no enum |
| M3 | `list_debates` limit has no upper bound |
| M4 | `DebateMessage.content` has no size limit |
| M5 | No async context manager for DB lifecycle |
| M6 | Race conditions in phase transitions (need `asyncio.Lock`) |

### LOW (6 issues)

| ID | Issue |
|----|-------|
| L1 | No rate limiting |
| L2 | No logging |
| L3 | ID generation strategy undefined |
| L4 | Timestamp as raw string |
| L5 | No explicit data directory |
| L6 | No tests |

---

## 2. MCP Protocol Review

### Architecture Issues

- **Wrong server class** -- uses `Server` instead of `FastMCP`.
- **No entry point** in `pyproject.toml`.
- **"Who plays Session B?"** -- fundamental unresolved question.
- **Multi-session concept conflicts with MCP's single-client session model.**

### Missing MCP Features

| Feature | Status |
|---------|--------|
| Resources (debate history) | Missing |
| Prompts (debate protocol templates) | Missing |
| Sampling (critical for Session B) | Missing |
| Progress notifications | Missing |
| Tool annotations | Missing |
| Roots capability | Missing |

### Recommendations

1. Use **MCP Sampling** as the core mechanism for Session B.
2. Switch to `FastMCP`.
3. Add entry point (`[project.scripts]` or `__main__.py`).
4. Expose debate history as **Resources** and protocol steps as **Prompts**.
5. Simplify to a single tool call (`debate_start` -> server handles everything internally).

---

## 3. Python Architecture Review

### Critical Issues

- Server import wrong (`Server` -> `FastMCP`).
- No entry point (`__main__.py`, `[project.scripts]`).
- `store`: `object` type annotation instead of concrete types.
- No exception classes defined.
- Hardcoded relative `db_path`.

### Dependencies

- `mcp`, `aiosqlite` unpinned.
- Consider `Pydantic BaseModel` over `dataclass`.
- Missing `mypy` in dev deps.

### Recommendations by Priority

| Priority | Items |
|----------|-------|
| **P0** | Entry point, FastMCP migration, custom exception classes |
| **P1** | Type fixes, phase transitions table, DB lifecycle management, pin deps |
| **P2** | Tests, Pydantic consideration, structured logging |
| **P3** | Ruff rules expansion, mypy config |

### Language Choice: Python is correct.

---

## 4. Product / DX Review

### First Impressions

- Tagline is excellent: *"Same model, different context depths, better decisions."*
- No installation instructions.
- No usage example.
- "Early development" is vague -- gives no sense of what works today.

### Onboarding: Blocked

- No `pip install` command.
- No CLI command.
- No MCP config example (e.g., `claude_desktop_config.json` snippet).
- No `__main__.py` or entry point.

### Critical Gap

Session B orchestration mechanism is **completely undesigned**:
- Who spawns Session B?
- How does the response route back?
- What does the user see during a debate?

### Competitive Positioning

| Competitor | Relationship |
|------------|-------------|
| Agent Mail | Ploidy adds structured protocol + intentional asymmetry |
| memctl / Engram | Complementary, not competitive |

### Recommendations

| Priority | Items |
|----------|-------|
| **P0** | Session B design, entry point, install instructions |
| **P1** | Working tool implementation, usage example |
| **P2** | `CONTRIBUTING.md`, CI pipeline, `good-first-issue` labels |

---

## 5. Academic Review

### Novelty Assessment

- **Conditionally defensible.** Inversion of "asymmetry as problem" into "asymmetry as feature" is genuinely novel.
- **MUST survive the "is this just running the model twice?" objection.**
- Need a straw-man ablation baseline (protocol vs. no-protocol).

### Theoretical Rigor

- **alpha (asymmetry coefficient)** is not operationally defined.
- Connection to Chen et al. (2603.05293) is analogical, not formal.
- Convergence score aggregation (harmonic mean) is unjustified.

### Experimental Gaps

| Gap | Detail |
|-----|--------|
| Zero results | No experiments have been run |
| Missing baseline | "Independent second opinion" baseline absent |
| Chat-chamber effect | Not operationally measured |
| Statistical methodology | Not specified |
| Model pairing ablation | Ablation 5 undermines the single-model framing |

### Venue Strategy

| Target | Assessment |
|--------|-----------|
| NeurIPS 2026 (May deadline) | Unrealistic -- 2 months, 0% implementation |
| **NeurIPS 2026 Workshop** | Recommended first target |
| ICLR 2027 or AAMAS 2027 | Full paper target |

### Anticipated Reviewer Objections

| # | Objection | Strength | Mitigation |
|---|-----------|----------|------------|
| 1 | "Just running model twice" | 9/10 | Protocol vs. no-protocol experiment |
| 2 | "Epoche framing is pretentious" | 7/10 | Trim philosophy, lead with empirics |
| 3 | "Chen et al. doesn't apply" | 8/10 | Reframe as motivating analogy, not formal basis |
| 4 | "2x compute cost" | 6/10 | Show cost-accuracy Pareto curves |
| 5 | "No convergence guarantees" | 7/10 | Hard `max_rounds` + empirical bounds |

### Ethics

- Do not imply converged output = unbiased.
- Do not suggest automated moral reasoning.
- Report environmental cost (2x+ tokens).

---

## Cross-Cutting Theme

All five reviewers independently identified the same **#1 issue**:

> **"Who runs Session B?"**
>
> The Session B orchestration mechanism is the single most critical unresolved design question. It blocks implementation, UX, and paper validation simultaneously.

---

## Action Items

### P0 -- Blocking everything

1. **Session B orchestration design doc** -- resolve the fundamental architecture question.
2. **FastMCP + `__main__.py` + entry point** -- make the server runnable.
3. **Straw-man experiment design** -- define the protocol-vs-no-protocol baseline.

### P1 -- Before public release

4. SQL parameterization + session auth patterns.
5. Pin dependencies (`mcp`, `aiosqlite`).
6. README: install / config / usage instructions.
7. Paper scope: 3 tasks + workshop submission.

### P2 -- Before contributors

8. `CONTRIBUTING.md` + CI pipeline.
9. Tests (protocol state machine first).
10. Working tool implementation.
