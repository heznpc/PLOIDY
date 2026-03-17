"""
Ploidy Experiment Runner
========================
Evaluates context-asymmetric debate across the Context Asymmetry Spectrum.

Uses `claude --print` CLI (no API key needed, uses Max/Pro subscription).
Each call = fresh session = perfect context isolation.

Methods (9):
  single          - Single session, full context
  second_opinion  - Two independent sessions, concatenated
  ccr             - CCR: deep produces, fresh reviews
  symmetric       - Symmetric debate (both full context)
  ploidy          - Asymmetric debate (deep vs fresh)
  self_consistency - 5 independent runs + majority vote (same token budget as ploidy)
  sf_passive      - Semi-Fresh (Passive): compressed summary in prompt
  sf_active       - Semi-Fresh (Active): summary available, must retrieve after independent analysis
  sf_selective    - Semi-Fresh (Selective): only failure/uncertainty info provided

Usage:
    python experiments/run_experiment.py
    python experiments/run_experiment.py --tasks 0,1,2 --methods ploidy,single,sf_passive
    python experiments/run_experiment.py --long --methods single,ploidy,sf_passive,sf_active,sf_selective
"""

import subprocess
import argparse
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

MODEL = "claude-opus-4-6"
JUDGE_MODEL = "claude-opus-4-6"


# ─── LLM Call via claude CLI ─────────────────────────────────────────────────

def call_llm(prompt: str, model: str = None) -> str:
    """Call claude CLI --print. Each call = fresh session."""
    cmd = ["claude", "--print", "--model", model or MODEL, prompt]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
    return result.stdout.strip()


def call_llm_multi_turn(turns: list[dict], model: str = None) -> str:
    """Simulate multi-turn by concatenating into single prompt.
    claude --print doesn't support multi-turn, so we format it explicitly."""
    parts = []
    for turn in turns:
        if turn["role"] == "user":
            parts.append(f"[USER]\n{turn['content']}")
        elif turn["role"] == "assistant":
            parts.append(f"[PREVIOUS ASSISTANT RESPONSE]\n{turn['content']}")
    parts.append("\n[NOW RESPOND TO THE LATEST USER MESSAGE ABOVE]")
    return call_llm("\n\n".join(parts), model)


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
        prompt='''Review this Python code for bugs:

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
```''',
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
        prompt='''Review this Python code for bugs:

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
```''',
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
        prompt='''Review this Python code for bugs:

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
```''',
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
        prompt='''Review this Python code for bugs:

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
```''',
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
    return call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )


def method_second_opinion(task: Task) -> str:
    """Baseline 2: two independent sessions, concatenate answers."""
    prompt = (
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    r1 = call_llm(prompt)
    r2 = call_llm(prompt)
    return f"=== Opinion 1 ===\n{r1}\n\n=== Opinion 2 ===\n{r2}"


def method_ccr(task: Task) -> str:
    """Baseline 3: CCR replication — deep produces, fresh reviews."""
    deep = call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    fresh = call_llm(
        f"{task.prompt}\n\nA colleague produced this analysis:\n\n{deep}\n\n"
        f"Review their analysis. What did they miss? What did they get wrong? "
        f"Are there additional issues? Be specific."
    )
    return f"=== Deep Analysis ===\n{deep}\n\n=== Fresh Review ===\n{fresh}"


def method_symmetric_debate(task: Task) -> str:
    """Baseline 4: symmetric debate — both get full context."""
    prompt = (
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    pos_a = call_llm(prompt)
    pos_b = call_llm(prompt)
    synthesis = call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"Two reviewers independently found these issues:\n\n"
        f"=== Reviewer A ===\n{pos_a}\n\n=== Reviewer B ===\n{pos_b}\n\n"
        f"Synthesize a final combined list. For each point, note agreement or disagreement."
    )
    return f"=== Position A ===\n{pos_a}\n\n=== Position B ===\n{pos_b}\n\n=== Synthesis ===\n{synthesis}"


def method_self_consistency(task: Task) -> str:
    """Baseline 5: 5 independent runs, majority-vote synthesis.
    Same token budget as Ploidy (~5 LLM calls)."""
    prompt = (
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical."
    )
    runs = [call_llm(prompt) for _ in range(5)]
    synthesis = call_llm(
        f"Five independent reviewers analyzed the same code/system.\n\n"
        + "\n\n".join(f"=== Reviewer {i+1} ===\n{r}" for i, r in enumerate(runs))
        + f"\n\nSynthesize by majority vote: list only issues found by 3+ reviewers. "
        f"For each, note how many reviewers found it (e.g., 4/5)."
    )
    return (
        "\n\n".join(f"=== Run {i+1} ===\n{r}" for i, r in enumerate(runs))
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
    deep_pos = call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
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
    deep_pos = call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
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


def method_semi_fresh_selective(task: Task) -> str:
    """Semi-Fresh (Selective): only failure/uncertainty info provided, not full findings."""
    # Deep position
    deep_pos = call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
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
    """Treatment: Ploidy — asymmetric context structured debate."""
    # POSITION phase
    deep_pos = call_llm(
        f"Context about this code/system:\n{task.context}\n\n{task.prompt}\n\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
    )
    fresh_pos = call_llm(
        f"{task.prompt}\n\n"
        f"You have NO background context about this system. Review based purely on the code/question itself.\n"
        f"List every bug, risk, or issue you can find. Be specific and technical.\n"
        f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
    )

    # CHALLENGE phase
    deep_challenge = call_llm(
        f"You previously reviewed this code with full project context and found:\n\n{deep_pos}\n\n"
        f"Now, a reviewer with NO project context found these issues:\n\n{fresh_pos}\n\n"
        f"For EACH of their points, respond with:\n"
        f"- AGREE: valid finding\n"
        f"- CHALLENGE: wrong/misleading given project context, explain why\n"
        f"- SYNTHESIZE: partially right, here's the nuance\n\n"
        f"Also list anything YOU found that THEY missed."
    )
    fresh_challenge = call_llm(
        f"You previously reviewed this code with NO project context and found:\n\n{fresh_pos}\n\n"
        f"Now, a reviewer with deep project context found these issues:\n\n{deep_pos}\n\n"
        f"For EACH of their points, respond with:\n"
        f"- AGREE: valid finding\n"
        f"- CHALLENGE: seems like rationalization or context-anchored bias, explain why\n"
        f"- SYNTHESIZE: partially right, here's the nuance\n\n"
        f"Also list anything YOU found that THEY missed."
    )

    # CONVERGENCE
    convergence = call_llm(
        f"Two reviewers debated this code/system. Synthesize their debate into a final verdict.\n\n"
        f"=== Deep Session (has project context) — Position ===\n{deep_pos}\n\n"
        f"=== Fresh Session (no context) — Position ===\n{fresh_pos}\n\n"
        f"=== Deep challenges Fresh ===\n{deep_challenge}\n\n"
        f"=== Fresh challenges Deep ===\n{fresh_challenge}\n\n"
        f"Produce a final list of ALL confirmed issues. For each:\n"
        f"1. The issue\n"
        f"2. Who found it (Deep, Fresh, or Both)\n"
        f"3. Whether it was agreed, contested, or synthesized\n"
        f"4. Final severity (CRITICAL / HIGH / MEDIUM / LOW)"
    )

    return (
        f"=== Deep Position ===\n{deep_pos}\n\n"
        f"=== Fresh Position ===\n{fresh_pos}\n\n"
        f"=== Deep Challenges Fresh ===\n{deep_challenge}\n\n"
        f"=== Fresh Challenges Deep ===\n{fresh_challenge}\n\n"
        f"=== Convergence ===\n{convergence}"
    )


# ─── Judge ───────────────────────────────────────────────────────────────────

def judge_result(task: Task, method_name: str, output: str) -> dict:
    """Judge how many ground-truth issues were found."""
    gt_list = "\n".join(f"  {i+1}. {gt}" for i, gt in enumerate(task.ground_truth))

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
}


def run_experiment(task_ids=None, method_ids=None):
    tasks = TASKS if task_ids is None else [TASKS[i] for i in task_ids]
    methods = METHODS if method_ids is None else {k: METHODS[k] for k in method_ids}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results" / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)

    all_results = []

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task.name} ({task.id})")
        print(f"Ground truth: {len(task.ground_truth)} known issues")
        print(f"{'='*60}")

        for method_id, (method_name, method_fn) in methods.items():
            print(f"\n  [{method_name}] running...", end=" ", flush=True)
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
                    print(f"  → {found}/{total} found, {partial} partial, {missed} missed | F1={f1:.3f}")
                else:
                    found = partial = missed = 0
                    f1 = 0.0
                    print("  → judge parse error")

                result = {
                    "task_id": task.id, "task_name": task.name,
                    "method": method_id, "method_name": method_name,
                    "found": found, "partial": partial, "missed": missed,
                    "total_gt": len(task.ground_truth),
                    "bonus_findings": judgment.get("bonus_findings", 0),
                    "f1": round(f1, 4), "elapsed_seconds": round(elapsed, 1),
                    "judgment": judgment,
                }
                all_results.append(result)

                with open(results_dir / f"{task.id}_{method_id}.json", "w") as f:
                    json.dump({"task": asdict(task), "output": output, **result}, f, indent=2, ensure_ascii=False)

            except Exception as e:
                elapsed = time.time() - t0
                print(f"ERROR ({elapsed:.0f}s): {e}")
                all_results.append({"task_id": task.id, "method": method_id, "error": str(e)})

    # Summary
    with open(results_dir / "summary.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"{'Task':<32} {'Method':<22} {'Found':>5} {'Part':>5} {'Miss':>5} {'F1':>7}")
    print("-" * 80)
    for r in all_results:
        if "error" not in r:
            print(f"{r['task_name']:<32} {r['method_name']:<22} {r['found']:>5} {r['partial']:>5} {r['missed']:>5} {r['f1']:>7.3f}")

    print(f"\n{'='*80}")
    print("AVERAGES")
    print(f"{'='*80}")
    for mid, (mname, _) in methods.items():
        mrs = [r for r in all_results if r.get("method") == mid and "error" not in r]
        if mrs:
            af1 = sum(r["f1"] for r in mrs) / len(mrs)
            af = sum(r["found"] for r in mrs) / len(mrs)
            at = sum(r["total_gt"] for r in mrs) / len(mrs)
            asec = sum(r["elapsed_seconds"] for r in mrs) / len(mrs)
            print(f"  {mname:<28} F1={af1:.3f}  Found={af:.1f}/{at:.1f}  Avg={asec:.0f}s")

    print(f"\nSaved: {results_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=str, help="e.g., 0,1,2")
    parser.add_argument("--methods", type=str, help="e.g., ploidy,single")
    parser.add_argument("--model", type=str, default=MODEL)
    parser.add_argument("--long", action="store_true", help="Use long-context tasks")
    args = parser.parse_args()
    MODEL = args.model

    if args.long:
        from tasks_longcontext import LONG_CONTEXT_TASKS
        TASKS.clear()
        TASKS.extend(LONG_CONTEXT_TASKS)

    run_experiment(
        [int(x) for x in args.tasks.split(",")] if args.tasks else None,
        args.methods.split(",") if args.methods else None,
    )
