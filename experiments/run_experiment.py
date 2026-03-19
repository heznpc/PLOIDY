"""
Ploidy Experiment Runner
========================
Evaluates context-asymmetric debate across the Context Asymmetry Spectrum.

Uses `claude --print` CLI (no API key needed, uses Max/Pro subscription).
Each call = fresh session = perfect context isolation.

Methods (11):
  single          - Single session, full context
  second_opinion  - Two independent sessions, concatenated
  ccr             - CCR: deep produces, fresh reviews
  symmetric       - Symmetric debate (both full context)
  ploidy          - Asymmetric debate (deep vs fresh)
  self_consistency - 5 independent runs + majority vote (same token budget as ploidy)
  sf_passive      - Semi-Fresh (Passive): compressed summary in prompt
  sf_active       - Semi-Fresh (Active): summary available, must retrieve after independent analysis
  sf_selective    - Semi-Fresh (Selective): only failure/uncertainty info provided
  sf_passive_indep - Ablation: passive + independent-first instruction
  sf_passive_bottom - Ablation: passive with summary at bottom

Experimental Variables:
  --effort         Effort level (low/medium/high/max) — controls LLM reasoning depth
  --model          Model identifier
  --long           Use long-context tasks with anchoring biases
  --injection      Context injection mode (raw/system_prompt/memory/skills/claude_md)
  --lang           Output language (en/ko/ja/zh)

Usage:
    python experiments/run_experiment.py
    python experiments/run_experiment.py --tasks 0,1,2 --methods ploidy,single
    python experiments/run_experiment.py --long --effort high --methods single,ploidy,sf_active
    python experiments/run_experiment.py --long --effort-sweep   # Run all effort levels
    python experiments/run_experiment.py --injection-sweep        # Run all injection modes
    python experiments/run_experiment.py --injection memory --methods ploidy,single
"""

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

MODEL = "claude-opus-4-6"
JUDGE_MODEL = "claude-opus-4-6"
EFFORT = "high"  # default effort level
LANGUAGE = "en"  # default output language
INJECTION_MODE = "raw"  # default context injection mode
DEEP_N = 1  # number of Deep sessions (stochastic sampling)
FRESH_N = 1  # number of Fresh sessions (stochastic sampling)

# Valid effort levels for Claude Code
EFFORT_LEVELS = ["low", "medium", "high", "max"]

# Languages for localization variable testing
LANGUAGES = {
    "en": "Respond in English.",
    "ko": "한국어로 답변하세요. 기술적 용어는 가능한 한 한국어로 번역하세요.",
    "ja": "日本語で回答してください。技術用語はできる限り日本語に翻訳してください。",
    "zh": "请用中文回答。尽可能将技术术语翻译成中文。",
}

# Context injection modes — tests whether the *form* of context delivery
# affects model behavior and debate outcomes, independent of content.
#
# Hypotheses:
# - H1: Memory-style injection (accumulated observations) may produce more
#        anchored/sycophantic responses than skills-style (declarative rules)
# - H2: System-prompt injection may create stronger priors than user-message
#        injection due to positional authority bias
# - H3: The interaction between injection mode and context asymmetry may
#        differ — Fresh sessions may be differentially affected by how the
#        Deep session's context was originally formed
INJECTION_MODES = {
    "raw": {
        "description": "Raw context in user prompt (baseline)",
        "format": lambda ctx: f"Context about this code/system:\n{ctx}",
    },
    "system_prompt": {
        "description": "Context as system-level instruction",
        "format": lambda ctx: (
            f"You are a senior engineer with deep knowledge of this system. "
            f"You have the following project context that informs your analysis:\n\n{ctx}"
        ),
    },
    "memory": {
        "description": "Context as accumulated memories (CLAUDE.md / memory.md style)",
        "format": lambda ctx: (
            "The following memories were accumulated from your prior work sessions "
            "on this project. They represent observations, decisions, and lessons "
            "learned over time:\n\n"
            "---\n"
            "## Project Memory\n\n"
            + "\n".join(
                f"- **Observation #{i + 1}**: {line.strip()}"
                for i, line in enumerate(ctx.strip().split("\n"))
                if line.strip()
            )
            + "\n---"
        ),
    },
    "skills": {
        "description": "Context as declarative rules/capabilities (skills.md style)",
        "format": lambda ctx: (
            "# Project Skills & Rules\n\n"
            "When analyzing this codebase, apply the following rules and constraints:\n\n"
            + "\n".join(
                f"- RULE: {line.strip()}"
                for i, line in enumerate(ctx.strip().split("\n"))
                if line.strip()
            )
        ),
    },
    "claude_md": {
        "description": "Context as CLAUDE.md project instructions",
        "format": lambda ctx: (
            f"<project-instructions>\n"
            f"# CLAUDE.md\n\n"
            f"## Project Context\n\n{ctx}\n\n"
            f"## Conventions\n"
            f"- Be thorough in code review\n"
            f"- Flag all security issues\n"
            f"- Consider operational context\n"
            f"</project-instructions>"
        ),
    },
}


# ─── Context Injection Helper ────────────────────────────────────────────────


def format_deep_context(context: str, mode: str = None) -> str:
    """Format context for the Deep session using the specified injection mode.

    Args:
        context: Raw context string from the task.
        mode: Injection mode key (raw/system_prompt/memory/skills/claude_md).

    Returns:
        Formatted context string.
    """
    actual_mode = mode or INJECTION_MODE
    if actual_mode not in INJECTION_MODES:
        actual_mode = "raw"
    return INJECTION_MODES[actual_mode]["format"](context)


def build_deep_prompt(task_context: str, task_prompt: str, mode: str = None) -> str:
    """Build the full Deep session prompt with injection-mode-appropriate context.

    For system_prompt mode, context goes into --system-prompt flag via call_llm.
    For all other modes, context is prepended to the user prompt.

    Args:
        task_context: The task's context string.
        task_prompt: The task's prompt string.
        mode: Injection mode key.

    Returns:
        The user prompt (context may be embedded or separate depending on mode).
    """
    actual_mode = mode or INJECTION_MODE
    formatted_ctx = format_deep_context(task_context, actual_mode)

    if actual_mode == "system_prompt":
        # Context goes via --system-prompt; user prompt has only the task
        return task_prompt
    else:
        return f"{formatted_ctx}\n\n{task_prompt}"


def get_system_prompt_for_mode(task_context: str, mode: str = None) -> str | None:
    """Return system prompt if injection mode uses it, else None.

    Args:
        task_context: The task's context string.
        mode: Injection mode key.

    Returns:
        System prompt string, or None.
    """
    actual_mode = mode or INJECTION_MODE
    if actual_mode == "system_prompt":
        return format_deep_context(task_context, actual_mode)
    return None


# ─── LLM Backend ────────────────────────────────────────────────────────────

BACKEND = "claude"  # claude | gemini | openai
TEMPERATURE = 0.0  # fixed for reproducibility (controls Event B variance)
MAX_TOKENS = 8192  # sufficient for debate synthesis phases

# Backend-specific model defaults
BACKEND_DEFAULTS = {
    "claude": "claude-opus-4-6",
    "gemini": "gemini-3.1-pro",
    "codex": "codex-default",
    "openai": "gpt-4.1",
}


def _call_claude(prompt: str, model: str, effort: str, system_prompt: str = None) -> str:
    """Call via claude CLI --print. Free with Max/Pro subscription."""
    cmd = ["claude", "--print", "--model", model]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    if effort and effort != "high":
        cmd.extend(["--effort", effort])
    cmd.append(prompt)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
    return result.stdout.strip()


def _call_codex(prompt: str, model: str, effort: str, system_prompt: str = None) -> str:
    """Call via codex exec. Free with ChatGPT Free/Plus."""
    import tempfile

    if system_prompt:
        prompt = f"{system_prompt}\n\n{prompt}"
    outfile = tempfile.mktemp(suffix=".txt")
    cmd = ["codex", "exec", "-o", outfile, "--full-auto"]
    if model and model != "codex-default":
        cmd.extend(["-m", model])
    cmd.append(prompt)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"codex CLI error: {result.stderr.strip()}")
    try:
        with open(outfile) as f:
            return f.read().strip()
    finally:
        import os
        os.unlink(outfile) if os.path.exists(outfile) else None


def _call_gemini(prompt: str, model: str, effort: str, system_prompt: str = None) -> str:
    """Call via gemini CLI -p. Free with Gemini CLI."""
    if system_prompt:
        prompt = f"{system_prompt}\n\n{prompt}"
    cmd = ["gemini", "-p", prompt]
    # Only pass -m if user explicitly specified a non-default model
    if model and model not in ("gemini-default", "gemini-3.1-pro"):
        cmd.extend(["-m", model])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"gemini CLI error: {result.stderr.strip()}")
    return result.stdout.strip()


def _call_openai_api(prompt: str, model: str, effort: str, system_prompt: str = None) -> str:
    """Call via OpenAI-compatible API.

    Unified backend for all non-Claude models. Set base_url to target different providers:
      - OpenAI direct:  OPENAI_BASE_URL=https://api.openai.com/v1
      - OpenRouter:     OPENAI_BASE_URL=https://openrouter.ai/api/v1
      - Ollama local:   OPENAI_BASE_URL=http://localhost:11434/v1
      - Anthropic:      OPENAI_BASE_URL=https://api.anthropic.com/v1 (with adapter)
    """
    import os

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required: pip install openai")

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "not-needed"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content or ""


_BACKENDS = {
    "claude": _call_claude,
    "gemini": _call_gemini,
    "codex": _call_codex,
    "openai": _call_openai_api,
}


def call_llm(
    prompt: str,
    model: str = None,
    effort: str = None,
    lang: str = None,
    system_prompt: str = None,
) -> str:
    """Call the configured LLM backend. Each call = fresh session.

    Supports claude, gemini, openai (API), and ollama backends.
    Set via --backend flag or BACKEND global.

    Args:
        prompt: The prompt to send.
        model: Model override (defaults to backend-specific default).
        effort: Effort level (low/medium/high/max).
        lang: Language code for localization (en/ko/ja/zh).
        system_prompt: Optional system prompt.

    Returns:
        The model's response text.
    """
    actual_lang = lang or LANGUAGE
    if actual_lang != "en" and actual_lang in LANGUAGES:
        prompt = f"{prompt}\n\n{LANGUAGES[actual_lang]}"

    actual_model = model or MODEL
    eff = effort or EFFORT
    backend_fn = _BACKENDS.get(BACKEND)
    if backend_fn is None:
        raise ValueError(f"Unknown backend: {BACKEND}. Choose from: {list(_BACKENDS.keys())}")
    return backend_fn(prompt, actual_model, eff, system_prompt)


def call_llm_multi_turn(turns: list[dict], model: str = None, effort: str = None) -> str:
    """Simulate multi-turn by concatenating into single prompt.
    claude --print doesn't support multi-turn, so we format it explicitly."""
    parts = []
    for turn in turns:
        if turn["role"] == "user":
            parts.append(f"[USER]\n{turn['content']}")
        elif turn["role"] == "assistant":
            parts.append(f"[PREVIOUS ASSISTANT RESPONSE]\n{turn['content']}")
    parts.append("\n[NOW RESPOND TO THE LATEST USER MESSAGE ABOVE]")
    return call_llm("\n\n".join(parts), model, effort)


# ─── Tasks ───────────────────────────────────────────────────────────────────


@dataclass
class Task:
    id: str
    name: str
    context: str
    prompt: str
    ground_truth: list[str]
    domain: str


TASKS: list[Task] = [
    Task(
        id="bug_race_condition",
        name="Race condition in async cache",
        context="""This is part of a web API server that handles 10K+ req/s.
We've been using this cache for 6 months. Last week we added the TTL feature
because users complained about stale data. The senior dev who wrote this left
the company. The cache is critical — it's used by the auth middleware.""",
        prompt="""Review this Python code for bugs:

```python
import asyncio
import time

class AsyncCache:
    def __init__(self, ttl=300):
        self._store = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get(self, key):
        if key in self._store:
            value, timestamp = self._store[key]
            if time.time() - timestamp < self._ttl:
                return value
            else:
                del self._store[key]
        return None

    async def set(self, key, value):
        async with self._lock:
            self._store[key] = (value, time.time())

    async def get_or_compute(self, key, compute_fn):
        result = await self.get(key)
        if result is not None:
            return result
        value = await compute_fn()
        await self.set(key, value)
        return value
```""",
        ground_truth=[
            "get() reads _store without lock — race condition with concurrent set()",
            "get_or_compute() has TOCTOU — multiple coroutines can call compute_fn() for same key",
            "del in get() is unprotected — can raise RuntimeError if dict changes during iteration",
        ],
        domain="code_review",
    ),
    Task(
        id="bug_sql_injection",
        name="SQL injection in search endpoint",
        context="""This is an internal admin tool used only by 5 employees.
We built it quickly for the ops team. It connects to a read-only replica.
The team lead said 'no need for ORM, just raw SQL for speed'.
We've been using this pattern across 20+ endpoints for a year.""",
        prompt="""Review this Python code for bugs:

```python
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db():
    return sqlite3.connect("app.db")

@app.route("/admin/search")
def search_users():
    query = request.args.get("q", "")
    role = request.args.get("role", "user")

    db = get_db()
    cursor = db.cursor()

    if role == "admin":
        sql = f"SELECT * FROM users WHERE role='admin' AND name LIKE '%{query}%'"
    else:
        sql = f"SELECT * FROM users WHERE role='user' AND name LIKE '%{query}%'"

    cursor.execute(sql)
    results = cursor.fetchall()
    db.close()
    return jsonify(results)
```""",
        ground_truth=[
            "SQL injection via query parameter — f-string directly interpolates user input",
            "role parameter is user-controlled — attacker can pass role=admin to access admin data",
            "Connection not properly managed — no context manager, connection leak on exception",
        ],
        domain="code_review",
    ),
    Task(
        id="bug_memory_leak",
        name="Memory leak in event handler",
        context="""This event system powers our real-time dashboard.
It's been running fine in dev but the production server's memory grows
~100MB/day. We added the weakref optimization last sprint based on a
blog post. The dashboard has ~50 event types and ~200 listeners.""",
        prompt="""Review this Python code for bugs:

```python
import weakref
from collections import defaultdict
from typing import Callable

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._handler_refs: dict[str, list] = defaultdict(list)

    def on(self, event: str, handler: Callable, weak: bool = False):
        if weak:
            ref = weakref.ref(handler)
            self._handler_refs[event].append(ref)
        else:
            self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    def emit(self, event: str, *args, **kwargs):
        for handler in self._handlers.get(event, []):
            handler(*args, **kwargs)
        for ref in self._handler_refs.get(event, []):
            handler = ref()
            if handler is not None:
                handler(*args, **kwargs)

    def clear(self, event: str = None):
        if event:
            self._handlers.pop(event, None)
        else:
            self._handlers.clear()
```""",
        ground_truth=[
            "weakref.ref on bound methods/lambdas dies immediately — ref() returns None right away because there's no other strong reference",
            "off() doesn't remove from _handler_refs — weak handlers can never be unsubscribed",
            "clear() doesn't clear _handler_refs — memory leak in weak handler list",
            "Dead weakrefs accumulate in _handler_refs lists — never cleaned up on emit()",
        ],
        domain="code_review",
    ),
    Task(
        id="arch_db_choice",
        name="Database choice for time-series IoT data",
        context="""We're building an IoT monitoring platform. Requirements:
- 10,000 devices sending metrics every 5 seconds
- Need 90-day retention with 1-second granularity
- Dashboards need sub-second query for last-24h, <5s for last-7d
- Team of 3 backend devs, all experienced with PostgreSQL
- Budget: $2K/month cloud infra
- Already using PostgreSQL 16 for user/device metadata
- The CTO wants everything in one database to "keep it simple"

The team lead proposed using PostgreSQL with partitioned tables for all time-series data.""",
        prompt="""Evaluate this architecture decision:
"Use PostgreSQL 16 with time-based partitioning (daily partitions) for all IoT time-series data.
Use pg_cron for partition management and materialized views for dashboard aggregations."

Should we accept this decision or propose an alternative? Justify with specific technical reasoning.""",
        ground_truth=[
            "PostgreSQL can handle this volume but will struggle — 10K devices x 1 write/5s = 2K writes/sec sustained, feasible but leaves little headroom",
            "Daily partitions for 90 days = 90 partitions — manageable but query planning overhead grows",
            "Materialized views for dashboards won't give sub-second refresh for last-24h — need continuous aggregation or dedicated TSDB",
            "TimescaleDB extension on existing PostgreSQL is the pragmatic middle ground — keeps single DB while adding native time-series features",
            "Dedicated TSDB (InfluxDB/QuestDB) would be better technically but adds operational complexity for a 3-person team",
        ],
        domain="architecture",
    ),
    Task(
        id="arch_auth_migration",
        name="Auth system migration strategy",
        context="""Monolith Django app serving 50K DAU. Current auth:
- Session-based auth with Django's built-in auth
- Sessions stored in PostgreSQL (same DB as app data)
- 12 internal microservices call the monolith's /api/verify endpoint
- Mobile app uses token refresh via custom JWT middleware (added 2 years ago)
- Average session: 4.2 hours
- The JWT secret was accidentally committed to git 8 months ago — rotated immediately but CEO is nervous
- SAML SSO for 3 enterprise clients was bolted on with django-saml2

The VP of Engineering wants to migrate to Auth0 "by end of quarter" (10 weeks).""",
        prompt="""Evaluate this migration plan:
"Replace all auth with Auth0 in a single cutover. Migrate all users, remove Django auth,
update all 12 microservices to validate Auth0 JWTs, and convert SAML clients to Auth0 connections.
Target: 10-week timeline, single cutover weekend."

Is this plan feasible? What are the risks and what would you change?""",
        ground_truth=[
            "Single cutover for 50K DAU + 12 services + 3 SAML clients in 10 weeks is extremely risky — any failure affects all users simultaneously",
            "Strangler fig pattern is safer — run Auth0 in parallel, migrate traffic gradually by service/user-segment",
            "SAML enterprise clients need their own migration timeline — they have their own change management processes",
            "12 microservices all validating Auth0 JWTs means 12 deployment risks — need canary/feature-flag rollout per service",
            "Session migration for 50K active users needs a dual-read period — users shouldn't be forced to re-login",
        ],
        domain="architecture",
    ),
    Task(
        id="logic_pagination",
        name="Off-by-one in cursor pagination",
        context="""This is our GraphQL API's pagination layer. We switched from
offset pagination to cursor-based 3 months ago because of performance issues
with large offsets. The cursor is base64-encoded. QA passed it, and it's been
in production. A customer reported "sometimes I see the same item twice when
paging through results" but we couldn't reproduce it.""",
        prompt='''Review this Python code for bugs:

```python
import base64
from dataclasses import dataclass

@dataclass
class PageInfo:
    has_next: bool
    end_cursor: str | None

def paginate(items: list, first: int = 10, after: str | None = None):
    """Cursor-based pagination. Cursor = base64(index)."""
    if after:
        index = int(base64.b64decode(after).decode())
        start = index
    else:
        start = 0

    end = start + first
    page = items[start:end]

    has_next = end < len(items)
    end_cursor = base64.b64encode(str(end).encode()).decode() if page else None

    return page, PageInfo(has_next=has_next, end_cursor=end_cursor)
```''',
        ground_truth=[
            "Cursor points to index, but start = index means the item AT the cursor is included again — should be start = index + 1",
            "This is the reported duplicate bug — last item of page N appears as first item of page N+1",
            "No validation of cursor — malformed/tampered base64 will crash with unhandled exception",
            "Cursor encodes raw index — reveals list position to client, fragile if list changes between requests",
        ],
        domain="code_review",
    ),
    Task(
        id="logic_retry",
        name="Broken retry with exponential backoff",
        context="""Our payment service calls an external payment gateway.
We added retry logic after seeing transient 503 errors. The on-call team
noticed that during a gateway outage last week, our retry storm caused
the gateway to rate-limit us for 2 hours after it recovered.""",
        prompt="""Review this Python code for bugs:

```python
import asyncio
import random
import httpx

async def call_payment_api(payload: dict, max_retries: int = 5) -> dict:
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post("https://api.payment.com/charge", json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise  # client error, don't retry
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)
        except httpx.TransportError:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)

    return {"status": "failed", "error": "max retries exceeded"}
```""",
        ground_truth=[
            "Creates new AsyncClient per attempt — no connection reuse, wastes resources and TCP connections",
            "No jitter coordination across instances — all instances retry at similar times causing thundering herd",
            "Retries on 409/422/etc that should not be retried — only 400 is excluded",
            "Returns a dict on failure instead of raising — caller can't distinguish success from failure",
            "No idempotency key — retrying a payment charge without idempotency can cause double-charging",
        ],
        domain="code_review",
    ),
]


# ─── Methods ─────────────────────────────────────────────────────────────────


def method_single_session(task: Task) -> str:
    """Baseline 1: single session with full context."""
    sys_prompt = get_system_prompt_for_mode(task.context)
    prompt = build_deep_prompt(task.context, task.prompt)
    return call_llm(
        f"{prompt}\n\nList every bug, risk, or issue you can find. Be specific and technical.",
        system_prompt=sys_prompt,
    )


def method_second_opinion(task: Task) -> str:
    """Baseline 2: two independent sessions, concatenate answers."""
    sys_prompt = get_system_prompt_for_mode(task.context)
    prompt = (
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    r1 = call_llm(prompt, system_prompt=sys_prompt)
    r2 = call_llm(prompt, system_prompt=sys_prompt)
    return f"=== Opinion 1 ===\n{r1}\n\n=== Opinion 2 ===\n{r2}"


def method_ccr(task: Task) -> str:
    """Baseline 3: CCR replication — deep produces, fresh reviews."""
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.",
        system_prompt=sys_prompt,
    )
    fresh = call_llm(
        f"{task.prompt}\n\nA colleague produced this analysis:\n\n{deep}\n\n"
        f"Review their analysis. What did they miss? What did they get wrong? "
        f"Are there additional issues? Be specific."
    )
    return f"=== Deep Analysis ===\n{deep}\n\n=== Fresh Review ===\n{fresh}"


def method_symmetric_debate(task: Task) -> str:
    """Baseline 4: symmetric debate — both get full context."""
    sys_prompt = get_system_prompt_for_mode(task.context)
    prompt = (
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    pos_a = call_llm(prompt, system_prompt=sys_prompt)
    pos_b = call_llm(prompt, system_prompt=sys_prompt)
    synthesis = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"Two reviewers independently found these issues:\n\n"
        f"=== Reviewer A ===\n{pos_a}\n\n=== Reviewer B ===\n{pos_b}\n\n"
        f"Synthesize a final combined list. For each point, note agreement or disagreement.",
        system_prompt=sys_prompt,
    )
    return f"=== Position A ===\n{pos_a}\n\n=== Position B ===\n{pos_b}\n\n=== Synthesis ===\n{synthesis}"


def method_self_consistency(task: Task) -> str:
    """Baseline 5: 5 independent runs, majority-vote synthesis.
    Same token budget as Ploidy (~5 LLM calls)."""
    sys_prompt = get_system_prompt_for_mode(task.context)
    prompt = (
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    runs = [call_llm(prompt, system_prompt=sys_prompt) for _ in range(5)]
    synthesis = call_llm(
        "Five independent reviewers analyzed the same code/system.\n\n"
        + "\n\n".join(f"=== Reviewer {i + 1} ===\n{r}" for i, r in enumerate(runs))
        + "\n\nSynthesize by majority vote: list only issues found by 3+ reviewers. "
        "For each, note how many reviewers found it (e.g., 4/5)."
    )
    return (
        "\n\n".join(f"=== Run {i + 1} ===\n{r}" for i, r in enumerate(runs))
        + f"\n\n=== Majority Vote Synthesis ===\n{synthesis}"
    )


def _compress_position(position: str) -> str:
    """Compress a Deep position into a structured summary for Semi-Fresh sessions."""
    return call_llm(
        f"Compress the following code review / architecture analysis into a SHORT structured summary.\n"
        f"Include ONLY:\n"
        f"- Key issues found (one line each)\n"
        f"- Approaches considered\n"
        f"- Constraints mentioned\n\n"
        f"Do NOT include the full reasoning or project narrative. Max 300 words.\n\n"
        f"Analysis to compress:\n{position}"
    )


def _compress_failures_only(position: str) -> str:
    """Extract only failure/risk information from a position, excluding successful analysis."""
    return call_llm(
        f"From the following analysis, extract ONLY:\n"
        f"- Issues that were flagged as uncertain or low-confidence\n"
        f"- Risks or concerns that were noted but not fully resolved\n"
        f"- Limitations or gaps acknowledged by the reviewer\n\n"
        f"Do NOT include issues the reviewer was confident about.\n"
        f"Do NOT include the project context or background. Max 200 words.\n\n"
        f"Analysis:\n{position}"
    )


def method_semi_fresh_passive(task: Task) -> str:
    """Semi-Fresh (Passive): compressed summary injected into prompt."""
    # Deep position
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep_pos = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.",
        system_prompt=sys_prompt,
    )

    # Compress Deep's position
    summary = _compress_position(deep_pos)

    # Semi-Fresh session: summary is directly in the prompt (passive delivery)
    semi_fresh_pos = call_llm(
        f"A previous reviewer analyzed this code/system and produced this summary:\n\n"
        f"--- PRIOR ANALYSIS SUMMARY ---\n{summary}\n--- END SUMMARY ---\n\n"
        f"Now perform your own independent review:\n\n{task.prompt}\n\n"
        f"Use the prior summary as background context, but form your own conclusions.\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
    )

    # Convergence
    convergence = call_llm(
        f"Two reviewers analyzed this code/system:\n\n"
        f"=== Deep Session (full project context) ===\n{deep_pos}\n\n"
        f"=== Semi-Fresh Session (received compressed summary only) ===\n{semi_fresh_pos}\n\n"
        f"Synthesize a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n2. Who found it (Deep, Semi-Fresh, or Both)\n"
        f"3. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    return (
        f"=== Deep Position ===\n{deep_pos}\n\n"
        f"=== Compressed Summary (given to Semi-Fresh) ===\n{summary}\n\n"
        f"=== Semi-Fresh Position ===\n{semi_fresh_pos}\n\n"
        f"=== Convergence ===\n{convergence}"
    )


def method_semi_fresh_active(task: Task) -> str:
    """Semi-Fresh (Active): summary available via explicit retrieval, not injected."""
    # Deep position
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep_pos = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.",
        system_prompt=sys_prompt,
    )

    # Compress Deep's position
    summary = _compress_position(deep_pos)

    # Semi-Fresh session: told summary exists, must decide when/whether to use it
    semi_fresh_pos = call_llm(
        f"{task.prompt}\n\n"
        f"You have NO background context about this system.\n"
        f"However, a previous reviewer has already analyzed this code. "
        f"Their compressed summary is available below if you want to consult it "
        f"AFTER forming your initial assessment.\n\n"
        f"INSTRUCTION: First, write your own independent analysis. "
        f"Then, consult the prior summary and note any additional issues or disagreements.\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.\n\n"
        f"--- PRIOR ANALYSIS (consult after your independent review) ---\n{summary}\n--- END ---"
    )

    # Convergence
    convergence = call_llm(
        f"Two reviewers analyzed this code/system:\n\n"
        f"=== Deep Session (full project context) ===\n{deep_pos}\n\n"
        f"=== Semi-Fresh Session (formed independent view, then consulted summary) ===\n{semi_fresh_pos}\n\n"
        f"Synthesize a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n2. Who found it (Deep, Semi-Fresh, or Both)\n"
        f"3. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    return (
        f"=== Deep Position ===\n{deep_pos}\n\n"
        f"=== Compressed Summary (available to Semi-Fresh) ===\n{summary}\n\n"
        f"=== Semi-Fresh Position (independent first, then consulted) ===\n{semi_fresh_pos}\n\n"
        f"=== Convergence ===\n{convergence}"
    )


def method_semi_fresh_passive_independent(task: Task) -> str:
    """Ablation: Passive delivery + independent-first instruction.
    Same as SF-Passive but adds 'first analyze independently' instruction.
    If this matches SF-Active's recall → instruction is the driver, not delivery mode.
    If this matches SF-Passive's recall → delivery mode is the driver."""
    # Deep position
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep_pos = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.",
        system_prompt=sys_prompt,
    )

    # Compress Deep's position
    summary = _compress_position(deep_pos)

    # Ablation: summary at TOP (passive) but with independent-first instruction
    semi_fresh_pos = call_llm(
        f"A previous reviewer analyzed this code/system and produced this summary:\n\n"
        f"--- PRIOR ANALYSIS SUMMARY ---\n{summary}\n--- END SUMMARY ---\n\n"
        f"INSTRUCTION: First, write your own independent analysis of the code/system below. "
        f"Then, revisit the prior summary above and note any additional issues or disagreements.\n\n"
        f"{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
    )

    # Convergence
    convergence = call_llm(
        f"Two reviewers analyzed this code/system:\n\n"
        f"=== Deep Session (full project context) ===\n{deep_pos}\n\n"
        f"=== Semi-Fresh Session (passive delivery + independent instruction) ===\n{semi_fresh_pos}\n\n"
        f"Synthesize a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n2. Who found it (Deep, Semi-Fresh, or Both)\n"
        f"3. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    return (
        f"=== Deep Position ===\n{deep_pos}\n\n"
        f"=== Compressed Summary (given to Semi-Fresh) ===\n{summary}\n\n"
        f"=== Semi-Fresh Position ===\n{semi_fresh_pos}\n\n"
        f"=== Convergence ===\n{convergence}"
    )


def method_semi_fresh_passive_bottom(task: Task) -> str:
    """Ablation: Passive delivery with summary at BOTTOM (not top).
    Same as SF-Passive but summary placed after the prompt, not before.
    If this matches SF-Active's recall → position (primacy/recency) is the driver.
    If this matches SF-Passive's recall → position doesn't matter, delivery mode does."""
    # Deep position
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep_pos = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.",
        system_prompt=sys_prompt,
    )

    # Compress Deep's position
    summary = _compress_position(deep_pos)

    # Ablation: summary at BOTTOM (passive, no independent instruction)
    semi_fresh_pos = call_llm(
        f"{task.prompt}\n\n"
        f"A previous reviewer analyzed this code/system and produced the summary below.\n"
        f"Use the prior summary as background context, but form your own conclusions.\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.\n\n"
        f"--- PRIOR ANALYSIS SUMMARY ---\n{summary}\n--- END SUMMARY ---"
    )

    # Convergence
    convergence = call_llm(
        f"Two reviewers analyzed this code/system:\n\n"
        f"=== Deep Session (full project context) ===\n{deep_pos}\n\n"
        f"=== Semi-Fresh Session (passive delivery, summary at bottom) ===\n{semi_fresh_pos}\n\n"
        f"Synthesize a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n2. Who found it (Deep, Semi-Fresh, or Both)\n"
        f"3. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    return (
        f"=== Deep Position ===\n{deep_pos}\n\n"
        f"=== Compressed Summary (given to Semi-Fresh) ===\n{summary}\n\n"
        f"=== Semi-Fresh Position ===\n{semi_fresh_pos}\n\n"
        f"=== Convergence ===\n{convergence}"
    )


def method_semi_fresh_selective(task: Task) -> str:
    """Semi-Fresh (Selective): only failure/uncertainty info provided, not full findings."""
    # Deep position
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep_pos = call_llm(
        f"{build_deep_prompt(task.context, task.prompt)}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.",
        system_prompt=sys_prompt,
    )

    # Extract only failures/uncertainties
    failure_digest = _compress_failures_only(deep_pos)

    # Semi-Fresh session: receives only what the Deep session was uncertain about
    semi_fresh_pos = call_llm(
        f"{task.prompt}\n\n"
        f"You have NO background context about this system.\n"
        f"A previous reviewer flagged these areas of uncertainty:\n\n"
        f"--- AREAS OF UNCERTAINTY ---\n{failure_digest}\n--- END ---\n\n"
        f"Use this as a starting point, but perform your own comprehensive review.\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
    )

    # Convergence
    convergence = call_llm(
        f"Two reviewers analyzed this code/system:\n\n"
        f"=== Deep Session (full project context) ===\n{deep_pos}\n\n"
        f"=== Semi-Fresh Session (received only uncertainty areas) ===\n{semi_fresh_pos}\n\n"
        f"Synthesize a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n2. Who found it (Deep, Semi-Fresh, or Both)\n"
        f"3. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    return (
        f"=== Deep Position ===\n{deep_pos}\n\n"
        f"=== Failure Digest (given to Semi-Fresh) ===\n{failure_digest}\n\n"
        f"=== Semi-Fresh Position ===\n{semi_fresh_pos}\n\n"
        f"=== Convergence ===\n{convergence}"
    )


def method_ploidy(task: Task) -> str:
    """Treatment: Ploidy — asymmetric context structured debate.

    Supports Deep(n) × Fresh(m) sessions to address both:
    - Event A (context asymmetry): Deep vs Fresh have different information
    - Event B (stochastic variance): multiple sessions at same depth sample
      different points from the output distribution
    """
    sys_prompt = get_system_prompt_for_mode(task.context)
    deep_n = DEEP_N
    fresh_n = FRESH_N

    # POSITION phase — spawn n Deep + m Fresh sessions
    deep_positions = []
    for i in range(deep_n):
        pos = call_llm(
            f"{build_deep_prompt(task.context, task.prompt)}\n\n"
            f"List every bug, risk, or issue you can find. Be specific and technical.\n"
            f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.",
            system_prompt=sys_prompt,
        )
        deep_positions.append(pos)

    fresh_positions = []
    for i in range(fresh_n):
        pos = call_llm(
            f"{task.prompt}\n\n"
            f"You have NO background context about this system. Review based purely on the code/question itself.\n"
            f"List every bug, risk, or issue you can find. Be specific and technical.\n"
            f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
        )
        fresh_positions.append(pos)

    # Aggregate positions for challenge phase
    deep_aggregate = "\n\n".join(
        f"--- Deep Session {i + 1}/{deep_n} ---\n{p}" for i, p in enumerate(deep_positions)
    )
    fresh_aggregate = "\n\n".join(
        f"--- Fresh Session {i + 1}/{fresh_n} ---\n{p}" for i, p in enumerate(fresh_positions)
    )

    # CHALLENGE phase — one representative challenge per side
    deep_challenge = call_llm(
        f"You are an experienced reviewer with full project context. "
        f"{'Your team' if deep_n > 1 else 'You'} found:\n\n{deep_aggregate}\n\n"
        f"Now, {'reviewers' if fresh_n > 1 else 'a reviewer'} with NO project context found:\n\n"
        f"{fresh_aggregate}\n\n"
        f"For EACH of their points, respond with:\n"
        f"- AGREE: valid finding\n"
        f"- CHALLENGE: wrong/misleading given project context, explain why\n"
        f"- SYNTHESIZE: partially right, here's the nuance\n\n"
        f"Also list anything your side found that they missed."
    )
    fresh_challenge = call_llm(
        f"You are a fresh reviewer with NO project context. "
        f"{'Your team' if fresh_n > 1 else 'You'} found:\n\n{fresh_aggregate}\n\n"
        f"Now, {'reviewers' if deep_n > 1 else 'a reviewer'} with deep project context found:\n\n"
        f"{deep_aggregate}\n\n"
        f"For EACH of their points, respond with:\n"
        f"- AGREE: valid finding\n"
        f"- CHALLENGE: seems like rationalization or context-anchored bias, explain why\n"
        f"- SYNTHESIZE: partially right, here's the nuance\n\n"
        f"Also list anything your side found that they missed."
    )

    # CONVERGENCE
    session_desc = f"Deep({deep_n}) × Fresh({fresh_n})"
    convergence = call_llm(
        f"A {session_desc} debate was held. Synthesize into a final verdict.\n\n"
        f"=== Deep Sessions (have project context) — Positions ===\n{deep_aggregate}\n\n"
        f"=== Fresh Sessions (no context) — Positions ===\n{fresh_aggregate}\n\n"
        f"=== Deep challenges Fresh ===\n{deep_challenge}\n\n"
        f"=== Fresh challenges Deep ===\n{fresh_challenge}\n\n"
        f"Produce a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n"
        f"2. Who found it (Deep, Fresh, or Both) and how many sessions found it\n"
        f"3. Whether it was agreed, contested, or synthesized\n"
        f"4. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    parts = []
    for i, p in enumerate(deep_positions):
        parts.append(f"=== Deep Position {i + 1}/{deep_n} ===\n{p}")
    for i, p in enumerate(fresh_positions):
        parts.append(f"=== Fresh Position {i + 1}/{fresh_n} ===\n{p}")
    parts.append(f"=== Deep Challenges Fresh ===\n{deep_challenge}")
    parts.append(f"=== Fresh Challenges Deep ===\n{fresh_challenge}")
    parts.append(f"=== Convergence ({session_desc}) ===\n{convergence}")

    return "\n\n".join(parts)


# ─── Judge ───────────────────────────────────────────────────────────────────


def judge_result(task: Task, method_name: str, output: str) -> dict:
    """Judge how many ground-truth issues were found."""
    gt_list = "\n".join(f"  {i + 1}. {gt}" for i, gt in enumerate(task.ground_truth))

    judgment = call_llm(
        f"You are an expert judge evaluating a code review / architecture analysis.\n\n"
        f"GROUND TRUTH issues (known correct answers):\n{gt_list}\n\n"
        f"REVIEWER OUTPUT:\n{output}\n\n"
        f"For EACH ground truth issue, determine:\n"
        f"- FOUND: clearly identified (even if worded differently)\n"
        f"- PARTIAL: hinted at but not fully articulated\n"
        f"- MISSED: not identified\n\n"
        f"Also count additional valid issues NOT in ground truth (bonus findings).\n\n"
        f"Respond in this EXACT JSON format and nothing else:\n"
        f'{{"scores": [{{"ground_truth_index": 1, "verdict": "FOUND", "evidence": "..."}}, ...], '
        f'"bonus_findings": 0, "summary": "..."}}',
        model=JUDGE_MODEL,
    )

    try:
        json_start = judgment.index("{")
        json_end = judgment.rindex("}") + 1
        return json.loads(judgment[json_start:json_end])
    except (ValueError, json.JSONDecodeError):
        return {"raw_judgment": judgment, "parse_error": True}


# ─── Runner ──────────────────────────────────────────────────────────────────

METHODS = {
    "single": ("Single Session", method_single_session),
    "second_opinion": ("Second Opinion", method_second_opinion),
    "ccr": ("CCR (Unidirectional)", method_ccr),
    "symmetric": ("Symmetric Debate", method_symmetric_debate),
    "ploidy": ("Ploidy (Asymmetric)", method_ploidy),
    "self_consistency": ("Self-Consistency (5-vote)", method_self_consistency),
    "sf_passive": ("Semi-Fresh (Passive)", method_semi_fresh_passive),
    "sf_active": ("Semi-Fresh (Active)", method_semi_fresh_active),
    "sf_selective": ("Semi-Fresh (Selective)", method_semi_fresh_selective),
    "sf_passive_indep": ("SF-Passive+Independent", method_semi_fresh_passive_independent),
    "sf_passive_bottom": ("SF-Passive+Bottom", method_semi_fresh_passive_bottom),
}


def run_experiment(task_ids=None, method_ids=None, effort: str = None, lang: str = None):
    """Run experiments across tasks and methods.

    Args:
        task_ids: Specific task indices to run (None = all).
        method_ids: Specific method keys to run (None = all).
        effort: Effort level override for this run.
        lang: Language code for localization (en/ko/ja/zh).
    """
    tasks = TASKS if task_ids is None else [TASKS[i] for i in task_ids]
    methods = METHODS if method_ids is None else {k: METHODS[k] for k in method_ids}
    eff = effort or EFFORT
    actual_lang = lang or LANGUAGE

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    inj = INJECTION_MODE
    results_dir = (
        Path(__file__).parent / "results" / f"{timestamp}_effort-{eff}_lang-{actual_lang}_inj-{inj}"
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    all_results = []

    for task in tasks:
        print(f"\n{'=' * 60}")
        print(f"Task: {task.name} ({task.id})")
        print(f"Ground truth: {len(task.ground_truth)} known issues")
        print(f"Effort: {eff} | Language: {actual_lang} | Injection: {inj}")
        print(f"{'=' * 60}")

        for method_id, (method_name, method_fn) in methods.items():
            print(f"\n  [{method_name}] running (effort={eff})...", end=" ", flush=True)
            t0 = time.time()

            try:
                output = method_fn(task)
                elapsed = time.time() - t0
                print(f"done ({elapsed:.0f}s)")

                print(f"  [{method_name}] judging...", end=" ", flush=True)
                judgment = judge_result(task, method_name, output)
                print("done")

                if "scores" in judgment:
                    found = sum(1 for s in judgment["scores"] if s["verdict"] == "FOUND")
                    partial = sum(1 for s in judgment["scores"] if s["verdict"] == "PARTIAL")
                    missed = sum(1 for s in judgment["scores"] if s["verdict"] == "MISSED")
                    total = len(task.ground_truth)
                    recall = (found + 0.5 * partial) / total
                    bonus = judgment.get("bonus_findings", 0)
                    precision = (found + 0.5 * partial) / max(found + partial + bonus, 1)
                    f1 = 2 * precision * recall / max(precision + recall, 0.001)
                    print(
                        f"  → {found}/{total} found, {partial} partial, {missed} missed | F1={f1:.3f}"
                    )
                else:
                    found = partial = missed = 0
                    f1 = 0.0
                    print("  → judge parse error")

                result = {
                    "task_id": task.id,
                    "task_name": task.name,
                    "method": method_id,
                    "method_name": method_name,
                    "effort": eff,
                    "language": actual_lang,
                    "injection_mode": INJECTION_MODE,
                    "deep_n": DEEP_N,
                    "fresh_n": FRESH_N,
                    "backend": BACKEND,
                    "model": MODEL,
                    "temperature": TEMPERATURE,
                    "max_tokens": MAX_TOKENS,
                    "found": found,
                    "partial": partial,
                    "missed": missed,
                    "total_gt": len(task.ground_truth),
                    "bonus_findings": judgment.get("bonus_findings", 0),
                    "f1": round(f1, 4),
                    "elapsed_seconds": round(elapsed, 1),
                    "judgment": judgment,
                }
                all_results.append(result)

                with open(results_dir / f"{task.id}_{method_id}.json", "w") as f:
                    json.dump(
                        {"task": asdict(task), "output": output, **result},
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

            except Exception as e:
                elapsed = time.time() - t0
                print(f"ERROR ({elapsed:.0f}s): {e}")
                all_results.append(
                    {"task_id": task.id, "method": method_id, "effort": eff, "error": str(e)}
                )

    # Summary
    with open(results_dir / "summary.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'=' * 80}")
    print(f"RESULTS (effort={eff})")
    print(f"{'=' * 80}")
    print(f"{'Task':<32} {'Method':<22} {'Found':>5} {'Part':>5} {'Miss':>5} {'F1':>7}")
    print("-" * 80)
    for r in all_results:
        if "error" not in r:
            print(
                f"{r['task_name']:<32} {r['method_name']:<22} "
                f"{r['found']:>5} {r['partial']:>5} {r['missed']:>5} {r['f1']:>7.3f}"
            )

    print(f"\n{'=' * 80}")
    print("AVERAGES")
    print(f"{'=' * 80}")
    for mid, (mname, _) in methods.items():
        mrs = [r for r in all_results if r.get("method") == mid and "error" not in r]
        if mrs:
            af1 = sum(r["f1"] for r in mrs) / len(mrs)
            af = sum(r["found"] for r in mrs) / len(mrs)
            at = sum(r["total_gt"] for r in mrs) / len(mrs)
            asec = sum(r["elapsed_seconds"] for r in mrs) / len(mrs)
            print(f"  {mname:<28} F1={af1:.3f}  Found={af:.1f}/{at:.1f}  Avg={asec:.0f}s")

    print(f"\nSaved: {results_dir}")
    return all_results


def run_effort_sweep(task_ids=None, method_ids=None, efforts=None):
    """Run experiments across all effort levels for factorial analysis.

    Runs each method at each effort level to measure effort x method interaction.
    This tests the hypothesis that effort level is a confounding variable in
    context-asymmetric debate.

    Args:
        task_ids: Specific task indices to run.
        method_ids: Specific method keys to run.
        efforts: Effort levels to sweep (default: all 4).

    Returns:
        Aggregated results across all effort levels.
    """
    global EFFORT
    sweep_efforts = efforts or EFFORT_LEVELS
    all_sweep_results = []

    print(f"\n{'#' * 80}")
    print(f"EFFORT SWEEP: {sweep_efforts}")
    print(f"{'#' * 80}")

    for eff in sweep_efforts:
        EFFORT = eff
        print(f"\n\n{'*' * 80}")
        print(f"  EFFORT LEVEL: {eff.upper()}")
        print(f"{'*' * 80}")

        results = run_experiment(task_ids, method_ids, effort=eff)
        for r in results:
            r["effort"] = eff
        all_sweep_results.extend(results)

    # Cross-effort summary
    print(f"\n\n{'#' * 80}")
    print("EFFORT SWEEP SUMMARY")
    print(f"{'#' * 80}")
    print(f"{'Effort':<10} {'Method':<22} {'Avg F1':>8} {'Avg Recall':>12} {'Avg Time':>10}")
    print("-" * 70)

    methods = METHODS if method_ids is None else {k: METHODS[k] for k in method_ids}
    for eff in sweep_efforts:
        for mid, (mname, _) in methods.items():
            mrs = [
                r
                for r in all_sweep_results
                if r.get("method") == mid and r.get("effort") == eff and "error" not in r
            ]
            if mrs:
                af1 = sum(r["f1"] for r in mrs) / len(mrs)
                af = sum(r["found"] for r in mrs) / len(mrs)
                at = sum(r["total_gt"] for r in mrs) / len(mrs)
                asec = sum(r["elapsed_seconds"] for r in mrs) / len(mrs)
                print(f"  {eff:<8} {mname:<22} {af1:>8.3f} {af:>5.1f}/{at:.1f} {asec:>8.0f}s")

    # Save sweep results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = Path(__file__).parent / "results" / f"{timestamp}_effort-sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    with open(sweep_dir / "sweep_summary.json", "w") as f:
        json.dump(all_sweep_results, f, indent=2, ensure_ascii=False)
    print(f"\nSweep saved: {sweep_dir}")

    return all_sweep_results


def run_language_sweep(task_ids=None, method_ids=None, languages=None):
    """Run experiments across languages for localization analysis.

    Tests whether linguistic framing affects information quality.
    When LLMs localize responses to feel natural in different languages,
    social/cultural context injection may distort technical findings.

    Hypotheses:
    - H1: Localized responses may euphemize or soften critical findings
    - H2: Hierarchical language norms (e.g., Korean keigo) may suppress
           challenges to established positions
    - H3: The information loss from localization interacts with context
           asymmetry — Fresh sessions may be more affected because they
           lack context to anchor technical terms

    Args:
        task_ids: Specific task indices to run.
        method_ids: Specific method keys to run.
        languages: Language codes to sweep (default: all).

    Returns:
        Aggregated results across all languages.
    """
    global LANGUAGE
    sweep_langs = languages or list(LANGUAGES.keys())
    all_lang_results = []

    print(f"\n{'#' * 80}")
    print(f"LANGUAGE SWEEP: {sweep_langs}")
    print(f"{'#' * 80}")

    for lang_code in sweep_langs:
        LANGUAGE = lang_code
        print(f"\n\n{'*' * 80}")
        print(f"  LANGUAGE: {lang_code.upper()} — {LANGUAGES.get(lang_code, 'English')}")
        print(f"{'*' * 80}")

        results = run_experiment(task_ids, method_ids, lang=lang_code)
        for r in results:
            r["language"] = lang_code
        all_lang_results.extend(results)

    # Cross-language summary
    print(f"\n\n{'#' * 80}")
    print("LANGUAGE SWEEP SUMMARY")
    print(f"{'#' * 80}")
    print(f"{'Lang':<6} {'Method':<22} {'Avg F1':>8} {'Avg Recall':>12} {'Avg Time':>10}")
    print("-" * 70)

    methods = METHODS if method_ids is None else {k: METHODS[k] for k in method_ids}
    for lang_code in sweep_langs:
        for mid, (mname, _) in methods.items():
            mrs = [
                r
                for r in all_lang_results
                if r.get("method") == mid and r.get("language") == lang_code and "error" not in r
            ]
            if mrs:
                af1 = sum(r["f1"] for r in mrs) / len(mrs)
                af = sum(r["found"] for r in mrs) / len(mrs)
                at = sum(r["total_gt"] for r in mrs) / len(mrs)
                asec = sum(r["elapsed_seconds"] for r in mrs) / len(mrs)
                print(f"  {lang_code:<4} {mname:<22} {af1:>8.3f} {af:>5.1f}/{at:.1f} {asec:>8.0f}s")

    # Save sweep results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = Path(__file__).parent / "results" / f"{timestamp}_lang-sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    with open(sweep_dir / "lang_sweep_summary.json", "w") as f:
        json.dump(all_lang_results, f, indent=2, ensure_ascii=False)
    print(f"\nLang sweep saved: {sweep_dir}")

    return all_lang_results


def run_injection_sweep(task_ids=None, method_ids=None, modes=None):
    """Run experiments across context injection modes.

    Tests whether the *form* of context delivery affects model behavior
    and debate outcomes, independent of the information content.

    This directly addresses the question: does the same information produce
    different results when delivered as accumulated memories (memory.md) vs
    declarative rules (skills.md) vs system instructions vs raw text?

    Hypotheses:
    - H1: Memory-style injection (accumulated observations) may produce more
           anchored/sycophantic responses than skills-style (declarative rules),
           because the model treats "learned observations" as stronger priors
    - H2: System-prompt injection may create stronger positional authority bias
           than user-message injection, affecting how readily the model
           challenges its own context during debate
    - H3: CLAUDE.md-style injection (project instructions with XML tags) may
           trigger different compliance behaviors than raw context, as models
           are trained to treat tagged instructions as authoritative
    - H4: The interaction between injection mode and context asymmetry may
           differ — the Fresh session's independence may be more or less
           valuable depending on how the Deep session's context was framed

    Args:
        task_ids: Specific task indices to run.
        method_ids: Specific method keys to run.
        modes: Injection mode keys to sweep (default: all).

    Returns:
        Aggregated results across all injection modes.
    """
    global INJECTION_MODE
    sweep_modes = modes or list(INJECTION_MODES.keys())
    all_inj_results = []

    print(f"\n{'#' * 80}")
    print(f"INJECTION MODE SWEEP: {sweep_modes}")
    print(f"{'#' * 80}")

    for mode in sweep_modes:
        INJECTION_MODE = mode
        desc = INJECTION_MODES[mode]["description"]
        print(f"\n\n{'*' * 80}")
        print(f"  INJECTION MODE: {mode.upper()} — {desc}")
        print(f"{'*' * 80}")

        results = run_experiment(task_ids, method_ids)
        for r in results:
            r["injection_mode"] = mode
        all_inj_results.extend(results)

    # Cross-mode summary
    print(f"\n\n{'#' * 80}")
    print("INJECTION MODE SWEEP SUMMARY")
    print(f"{'#' * 80}")
    print(f"{'Mode':<14} {'Method':<22} {'Avg F1':>8} {'Avg Recall':>12} {'Avg Time':>10}")
    print("-" * 75)

    methods = METHODS if method_ids is None else {k: METHODS[k] for k in method_ids}
    for mode in sweep_modes:
        for mid, (mname, _) in methods.items():
            mrs = [
                r
                for r in all_inj_results
                if r.get("method") == mid and r.get("injection_mode") == mode and "error" not in r
            ]
            if mrs:
                af1 = sum(r["f1"] for r in mrs) / len(mrs)
                af = sum(r["found"] for r in mrs) / len(mrs)
                at = sum(r["total_gt"] for r in mrs) / len(mrs)
                asec = sum(r["elapsed_seconds"] for r in mrs) / len(mrs)
                print(f"  {mode:<12} {mname:<22} {af1:>8.3f} {af:>5.1f}/{at:.1f} {asec:>8.0f}s")

    # Save sweep results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = Path(__file__).parent / "results" / f"{timestamp}_injection-sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    with open(sweep_dir / "injection_sweep_summary.json", "w") as f:
        json.dump(all_inj_results, f, indent=2, ensure_ascii=False)
    print(f"\nInjection sweep saved: {sweep_dir}")

    return all_inj_results


# Ploidy level names from biology
PLOIDY_NAMES = {1: "haploid", 2: "diploid", 3: "triploid", 4: "tetraploid"}


def run_ploidy_sweep(task_ids=None, method_ids=None, levels=None):
    """Run experiments across ploidy levels (1n through 4n).

    Tests the interaction between stochastic sampling (Event B) and
    context asymmetry (Event A). At 1n, each context depth has one
    session — disagreements could be stochastic or context-driven.
    At higher ploidy, within-group agreement distinguishes the two:
    if 3/3 Deep agree but 0/3 Fresh find it, the cause is context,
    not randomness.

    The biological metaphor is structurally precise:
    - Chromosome set count = stochastic samples per context depth
    - Haploid (1n) = minimal, fragile
    - Diploid (2n) = standard, one backup
    - Polyploid (3n+) = robust, redundant error correction

    Args:
        task_ids: Specific task indices to run.
        method_ids: Specific method keys to run (only 'ploidy' is affected).
        levels: Ploidy levels to sweep (default: [1, 2, 3, 4]).

    Returns:
        Aggregated results across all ploidy levels.
    """
    global DEEP_N, FRESH_N
    sweep_levels = levels or [1, 2, 3, 4]
    all_ploidy_results = []

    print(f"\n{'#' * 80}")
    print(f"PLOIDY SWEEP: {sweep_levels}")
    print(f"{'#' * 80}")

    for n in sweep_levels:
        DEEP_N = n
        FRESH_N = n
        name = PLOIDY_NAMES.get(n, f"{n}n-ploid")
        print(f"\n\n{'*' * 80}")
        print(f"  PLOIDY: {n}n ({name}) — Deep×{n}, Fresh×{n}")
        print(f"{'*' * 80}")

        results = run_experiment(task_ids, method_ids)
        for r in results:
            r["ploidy"] = n
            r["ploidy_name"] = name
        all_ploidy_results.extend(results)

    # Cross-ploidy summary
    print(f"\n\n{'#' * 80}")
    print("PLOIDY SWEEP SUMMARY")
    print(f"{'#' * 80}")
    print(f"{'Ploidy':<14} {'Method':<22} {'Avg F1':>8} {'Avg Recall':>12} {'Avg Time':>10}")
    print("-" * 75)

    methods = METHODS if method_ids is None else {k: METHODS[k] for k in method_ids}
    for n in sweep_levels:
        name = PLOIDY_NAMES.get(n, f"{n}n")
        for mid, (mname, _) in methods.items():
            mrs = [
                r
                for r in all_ploidy_results
                if r.get("method") == mid and r.get("ploidy") == n and "error" not in r
            ]
            if mrs:
                af1 = sum(r["f1"] for r in mrs) / len(mrs)
                af = sum(r["found"] for r in mrs) / len(mrs)
                at = sum(r["total_gt"] for r in mrs) / len(mrs)
                asec = sum(r["elapsed_seconds"] for r in mrs) / len(mrs)
                print(
                    f"  {n}n ({name:<8}) {mname:<22} {af1:>8.3f} {af:>5.1f}/{at:.1f} {asec:>8.0f}s"
                )

    # Save sweep results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = Path(__file__).parent / "results" / f"{timestamp}_ploidy-sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    with open(sweep_dir / "ploidy_sweep_summary.json", "w") as f:
        json.dump(all_ploidy_results, f, indent=2, ensure_ascii=False)
    print(f"\nPloidy sweep saved: {sweep_dir}")

    return all_ploidy_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ploidy Experiment Runner")
    parser.add_argument("--tasks", type=str, help="Task indices, e.g., 0,1,2")
    parser.add_argument("--methods", type=str, help="Method keys, e.g., ploidy,single")
    parser.add_argument("--model", type=str, default=MODEL, help="Model identifier")
    parser.add_argument("--long", action="store_true", help="Use long-context tasks (3 tasks)")
    parser.add_argument("--extended", action="store_true", help="Use extended task set (25 tasks)")
    parser.add_argument(
        "--all-long", action="store_true", help="Use all long-context tasks (3 + 25 = 28 tasks)"
    )
    parser.add_argument(
        "--effort",
        type=str,
        default="high",
        choices=EFFORT_LEVELS,
        help="Effort level (low/medium/high/max)",
    )
    parser.add_argument(
        "--effort-sweep",
        action="store_true",
        help="Run all effort levels for factorial analysis",
    )
    parser.add_argument(
        "--efforts",
        type=str,
        help="Specific effort levels for sweep, e.g., low,high,max",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="en",
        help="Output language (en/ko/ja/zh)",
    )
    parser.add_argument(
        "--lang-sweep",
        action="store_true",
        help="Run all languages for localization analysis",
    )
    parser.add_argument(
        "--langs",
        type=str,
        help="Specific languages for sweep, e.g., en,ko,ja",
    )
    parser.add_argument(
        "--injection",
        type=str,
        default="raw",
        choices=list(INJECTION_MODES.keys()),
        help="Context injection mode (raw/system_prompt/memory/skills/claude_md)",
    )
    parser.add_argument(
        "--injection-sweep",
        action="store_true",
        help="Run all injection modes for context delivery analysis",
    )
    parser.add_argument(
        "--injections",
        type=str,
        help="Specific injection modes for sweep, e.g., raw,memory,skills",
    )
    parser.add_argument(
        "--deep-n",
        type=int,
        default=1,
        help="Number of Deep sessions (stochastic sampling, default: 1)",
    )
    parser.add_argument(
        "--fresh-n",
        type=int,
        default=1,
        help="Number of Fresh sessions (stochastic sampling, default: 1)",
    )
    parser.add_argument(
        "--ploidy",
        type=int,
        default=None,
        help="Set session count per role (1=haploid, 2=diploid, 3=triploid). Overrides --deep-n and --fresh-n.",
    )
    parser.add_argument(
        "--ploidy-sweep",
        action="store_true",
        help="Run ploidy levels 1n through 4n for stochastic sampling analysis",
    )
    parser.add_argument(
        "--ploidy-levels",
        type=str,
        help="Specific ploidy levels for sweep, e.g., 1,3,4",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="claude",
        choices=list(_BACKENDS.keys()),
        help="LLM backend: claude (CLI, free with subscription) or openai (API, supports OpenRouter/Ollama via OPENAI_BASE_URL)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature for API calls (default: 0.0 for reproducibility)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help="Max output tokens (default: 8192)",
    )
    args = parser.parse_args()
    BACKEND = args.backend
    TEMPERATURE = args.temperature
    MAX_TOKENS = args.max_tokens
    MODEL = (
        args.model if args.model != "claude-opus-4-6" else BACKEND_DEFAULTS.get(BACKEND, args.model)
    )
    JUDGE_MODEL = MODEL  # Use same model for judging by default
    EFFORT = args.effort
    LANGUAGE = args.lang
    INJECTION_MODE = args.injection
    if args.ploidy is not None:
        DEEP_N = args.ploidy
        FRESH_N = args.ploidy
    else:
        DEEP_N = args.deep_n
        FRESH_N = args.fresh_n

    if args.long:
        from tasks_longcontext import LONG_CONTEXT_TASKS

        TASKS.clear()
        TASKS.extend(LONG_CONTEXT_TASKS)

    if hasattr(args, "extended") and args.extended:
        from tasks_extended import EXTENDED_TASKS

        TASKS.clear()
        TASKS.extend(EXTENDED_TASKS)

    if hasattr(args, "all_long") and args.all_long:
        from tasks_extended import EXTENDED_TASKS
        from tasks_longcontext import LONG_CONTEXT_TASKS

        TASKS.clear()
        TASKS.extend(LONG_CONTEXT_TASKS)
        TASKS.extend(EXTENDED_TASKS)

    task_ids = [int(x) for x in args.tasks.split(",")] if args.tasks else None
    method_ids = args.methods.split(",") if args.methods else None

    if args.effort_sweep:
        sweep_efforts = args.efforts.split(",") if args.efforts else None
        run_effort_sweep(task_ids, method_ids, sweep_efforts)
    elif args.lang_sweep:
        sweep_langs = args.langs.split(",") if args.langs else None
        run_language_sweep(task_ids, method_ids, sweep_langs)
    elif args.injection_sweep:
        sweep_modes = args.injections.split(",") if args.injections else None
        run_injection_sweep(task_ids, method_ids, sweep_modes)
    elif args.ploidy_sweep:
        sweep_levels = (
            [int(x) for x in args.ploidy_levels.split(",")]
            if args.ploidy_levels
            else None
        )
        run_ploidy_sweep(task_ids, method_ids, sweep_levels)
    else:
        run_experiment(task_ids, method_ids)
