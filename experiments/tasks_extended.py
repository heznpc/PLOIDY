"""
Extended task set for statistical validation.
25 long-context tasks across 7 domains, each with misleading priors
designed to trigger context entrenchment.

Domains:
  - Architecture decisions (5)
  - Code review / bug detection (5)
  - Security audit (4)
  - API design (3)
  - Database / data modeling (3)
  - DevOps / deployment (3)
  - Dependency / migration (2)
"""

from task_model import Task

EXTENDED_TASKS: list[Task] = [
    # ─── Architecture Decisions ──────────────────────────────────────────────
    Task(
        id="arch_cache_strategy",
        name="Cache invalidation strategy bias",
        context="""## Project History (14 months)

Our e-commerce platform handles 2M daily active users. We implemented Redis
as our caching layer 14 months ago. The senior architect (now VP) designed
the cache-aside pattern personally.

### Key decisions:
- 2024-10: Chose Redis over Memcached. VP's decision, team agreed.
- 2025-01: Added cache warming on deploy. VP wrote the implementation.
- 2025-04: Customer reported stale prices. VP added 5-minute TTL globally.
- 2025-07: Added cache tags for product categories. VP's pattern.
- 2025-09: Performance review showed 94% cache hit rate. VP presented to board.
- 2025-11: Started seeing "ghost inventory" — items showing as available
  but actually out of stock. Temporary fix: reduced TTL to 60 seconds.
  Hit rate dropped to 71%. VP says "just need better invalidation logic."
- 2026-01: 3 engineers spent 2 weeks building event-driven invalidation.
  Still seeing ghost inventory on flash sales (100+ orders/second).

### Team sentiment:
- "Redis is fine, we just need to tune invalidation"
- "The VP built this, it works for 99% of cases"
- "Switching cache strategy would take months"

### Current metrics:
- Redis: 6 nodes, 48GB total memory, $2,400/month
- Hit rate: 78% (was 94% before TTL reduction)
- Ghost inventory incidents: 12/month during sales
- P99 latency: 180ms (target: 100ms)""",
        prompt="""The VP proposes: "Add a distributed lock around inventory updates and
implement two-phase cache invalidation. Timeline: 3 weeks."

Evaluate this proposal. Is this the right approach?""",
        ground_truth=[
            "Cache-aside pattern is fundamentally wrong for inventory — needs write-through or event-sourced inventory with CQRS",
            "Ghost inventory is a consistency problem, not a caching problem — distributed lock adds latency without solving the root cause",
            "The VP designed the original system and is anchored to preserving it — 'just need better invalidation' is sunk cost reasoning",
            "94% hit rate was misleading — high hit rate with stale data is worse than lower hit rate with correct data",
            "60-second TTL on inventory during flash sales (100 orders/sec) means up to 6,000 orders could see stale stock",
        ],
        domain="architecture",
    ),
    Task(
        id="arch_event_driven",
        name="Event-driven migration with Kafka bias",
        context="""## Project History (2 years)

Fintech startup processing 500K transactions/day. Monolith Django app.

### Evolution:
- 2024-03: Started with synchronous REST calls between services.
- 2024-08: Latency issues. CTO attended KafkaSummit, came back saying
  "we need Kafka for everything." Team had zero Kafka experience.
- 2024-11: 4 engineers spent 6 weeks setting up Kafka cluster (3 brokers,
  ZooKeeper, Schema Registry, Connect). CTO blogged about the journey.
- 2025-02: Migrated payment notifications to Kafka. Took 3 months.
  Lost 847 notifications in the first week due to consumer group rebalancing.
- 2025-05: Migrated fraud detection pipeline to Kafka Streams. 2 months.
  Works well but only 1 engineer understands the topology.
- 2025-08: Tried migrating user activity tracking. Abandoned after 6 weeks —
  "Kafka was overkill for simple event logging."
- 2025-11: Kafka cluster costs $8,500/month (managed Confluent Cloud).
  3 of 12 planned migrations completed. CTO says "stay the course."
- 2026-02: New requirement: real-time regulatory reporting. CTO: "perfect
  use case for our Kafka investment."

### Team sentiment:
- "We've invested too much in Kafka to switch now"
- "The CTO staked his reputation on this"
- "Kafka is the industry standard for event-driven"

### Current state:
- 3/12 migrations done in 18 months
- $8,500/month Kafka costs for 3 use cases
- 1 engineer is the Kafka expert (bus factor = 1)
- 9 remaining services still using REST""",
        prompt="""Evaluate: Should the team continue migrating remaining services to Kafka
as planned, or take a different approach for the regulatory reporting requirement?""",
        ground_truth=[
            "Sunk cost fallacy — $8,500/month and 18 months invested doesn't justify continuing if the approach isn't working (3/12 done)",
            "CTO has authority bias — 'staked his reputation' creates organizational pressure to continue regardless of technical merit",
            "Kafka is overkill for most of their use cases — simple message queue (SQS/RabbitMQ) would handle 8 of the 9 remaining services",
            "Bus factor = 1 on Kafka is a critical risk — if the expert leaves, 3 production systems become unmaintainable",
            "Regulatory reporting has strict delivery guarantees that Kafka can provide, but a simpler solution (database CDC + lightweight stream) might suffice",
            "The abandoned user activity migration is evidence the team already recognized the mismatch but couldn't act due to organizational pressure",
        ],
        domain="architecture",
    ),
    Task(
        id="arch_frontend_rewrite",
        name="Frontend rewrite with React bias",
        context="""## Project History (3 years)

B2B SaaS dashboard. 200K LOC Angular 14 app. 8 frontend engineers.

### Timeline:
- 2023-06: Built with Angular 14. Team of 5, all Angular experts.
- 2024-01: Hired 3 React developers (market availability). They complained
  about Angular's learning curve and "boilerplate."
- 2024-06: React devs proposed rewrite. Angular devs opposed. PM sided
  with React devs because "React has more npm downloads."
- 2024-09: Approved "gradual migration" — new features in React, old
  features stay Angular. Used Module Federation for integration.
- 2025-01: Module Federation setup took 2 months. Constant build issues.
- 2025-06: 30% of features now in React. Bundle size increased 2.4x.
  Load time went from 2.1s to 5.8s. Users complaining.
- 2025-09: Performance audit blamed Module Federation overhead. Solution:
  "migrate faster so we can remove Angular entirely."
- 2026-01: 45% React, 55% Angular. Two build systems. Two state management
  approaches. Two testing frameworks. Onboarding takes 3 weeks.

### Current problems:
- Load time: 5.8s (was 2.1s, SLA: 3s)
- Bundle size: 4.2MB (was 1.8MB)
- Build time: 12 minutes (was 4 minutes)
- 3 of 8 engineers understand both frameworks
- Customer churn increased 15% (NPS mentions "slow dashboard")""",
        prompt="""The team lead proposes: "Accelerate the React migration. Dedicate all 8 engineers
to converting remaining Angular components. Target: 100% React in 4 months."

Evaluate this proposal.""",
        ground_truth=[
            "The migration itself caused the performance regression (2.1s → 5.8s) — accelerating it doubles down on the cause of the problem",
            "npm downloads is not a valid technical criterion for framework choice — this was a popularity-driven decision, not engineering-driven",
            "Angular 14 was working fine — the 'problem' was new hires' preferences, not technical limitations",
            "Completing the migration removes Module Federation overhead but doesn't guarantee return to 2.1s — React bundle + state management may be inherently larger",
            "4-month timeline for 55% of 200K LOC with only 3 cross-framework engineers is unrealistic — the 3 Angular-only devs will be ineffective",
            "Customer churn is the real problem — a performance fix (lazy loading, code splitting) in the current hybrid setup could be done in 2 weeks vs 4 months",
        ],
        domain="architecture",
    ),
    Task(
        id="arch_graphql_migration",
        name="GraphQL migration with REST defense",
        context="""## Project History (18 months)

Mobile-first social platform. 3M MAU. 47 REST endpoints.

### Timeline:
- 2024-09: REST API serving iOS + Android + Web. Designed by founding engineer.
- 2025-01: Mobile team complained about over-fetching. 12 endpoints return
  50+ fields when mobile needs 5-8.
- 2025-03: Backend lead proposed GraphQL. Founding engineer opposed:
  "REST is simpler, just make new endpoints."
- 2025-05: Created 15 new "mobile-optimized" endpoints. Now 62 total.
- 2025-08: Web team started needing different field combinations. Created
  query parameter filters (?fields=id,name,avatar). 8 endpoints support it.
- 2025-11: iOS team needs nested resources (user → posts → comments).
  Currently requires 3 sequential API calls. Created 5 "aggregate" endpoints.
- 2026-02: 67 endpoints. 4 engineers spend 30% of time maintaining endpoint
  variants. API documentation is 200 pages. Founding engineer says
  "this is fine, REST scales linearly."

### Current state:
- 67 REST endpoints (was 47, grew 43% in 18 months)
- 15 mobile-optimized + 5 aggregate + original endpoints
- Documentation: 200 pages, frequently outdated
- N+1 query problems on aggregate endpoints
- Mobile app makes average 8.3 API calls per screen""",
        prompt="""The founding engineer proposes: "Add a BFF (Backend-for-Frontend) layer. Each
client gets its own BFF that aggregates REST calls. Keep all 67 endpoints as-is."

Evaluate this proposal.""",
        ground_truth=[
            "BFF adds a new layer without solving the root cause — 67 endpoints will keep growing, now with BFF maintenance on top",
            "Founding engineer has ownership bias — 'I designed the API' creates resistance to admitting the architecture has outgrown its design",
            "'REST scales linearly' is technically true but irrelevant — the problem is combinatorial explosion of client-specific endpoints, not scale",
            "The trajectory (47 → 67 endpoints in 18 months with 43% growth) shows the approach is unsustainable — BFF delays but doesn't prevent the eventual reckoning",
            "GraphQL would solve over-fetching, nested resource loading (8.3 calls → 1), and documentation (schema is self-documenting) — the original objection was 'simplicity' but 67 endpoints with 200-page docs is no longer simple",
        ],
        domain="architecture",
    ),
    Task(
        id="arch_serverless_migration",
        name="Serverless migration with Lambda bias",
        context="""## Project History (15 months)

IoT data processing platform. 50K devices. Backend team of 5.

### Timeline:
- 2024-10: Running on 3 EC2 instances. Stable but "boring" per team lead.
- 2025-01: Team lead attended re:Invent. Came back wanting "full serverless."
  Team agreed — resume-driven development enthusiasm.
- 2025-03: Migrated device registration to Lambda. Worked great.
- 2025-05: Migrated telemetry ingestion to Lambda. Cold starts caused
  3-8 second delays. Added provisioned concurrency ($1,200/month).
- 2025-07: Migrated data processing pipeline to Step Functions + Lambda.
  15-minute Lambda timeout hit on batch processing. Workaround: chunked
  processing with SQS between steps. Added 3 weeks of debugging.
- 2025-09: Migrated analytics aggregation. Hit 6MB payload limit on
  Lambda response. Workaround: S3 intermediate storage + pre-signed URLs.
- 2025-12: Monthly AWS bill went from $450 (EC2) to $3,200 (Lambda +
  provisioned concurrency + Step Functions + SQS + S3 intermediate).
- 2026-01: New requirement: 30-second processing SLA on telemetry.
  Current: 3-8 seconds cold start + 2-5 seconds processing = 5-13 seconds.

### Team sentiment:
- "Serverless is the future, containers are legacy"
- "We just need to optimize our Lambda functions"
- "Going back to EC2 would be admitting failure"

### Current costs:
- EC2 era: $450/month, 3 instances, 99.9% uptime
- Serverless era: $3,200/month, 47 Lambda functions, numerous workarounds""",
        prompt="""The team lead proposes: "Add Lambda SnapStart for cold start optimization and
increase provisioned concurrency to meet the 30-second SLA. Estimated additional
cost: $800/month."

Evaluate this proposal.""",
        ground_truth=[
            "7x cost increase ($450 → $3,200+) for the same workload is not justified — serverless economics don't fit sustained high-throughput IoT ingestion",
            "Resume-driven development — the migration was motivated by 're:Invent excitement' and career signaling, not technical need",
            "'Going back to EC2 would be admitting failure' is sunk cost fallacy — the system was stable and cheap before",
            "Lambda's architectural constraints (15-min timeout, 6MB payload, cold starts) are fundamental mismatches for batch data processing and sustained ingestion",
            "Containerized solution (ECS Fargate or even the original EC2) would meet the 30-second SLA trivially at a fraction of the cost",
            "Each workaround (chunking, S3 intermediate, provisioned concurrency) adds complexity and cost without addressing the architectural mismatch",
        ],
        domain="architecture",
    ),
    # ─── Code Review / Bug Detection ────────────────────────────────────────
    Task(
        id="bug_connection_pool",
        name="Connection pool exhaustion",
        context="""Our Python API server handles 5K req/s. We've been running this connection
pool for 8 months. The DBA who set it up left. Last week production went
down for 20 minutes — connections maxed out. We added monitoring after
the incident and increased pool size from 20 to 50. Seemed to fix it.""",
        prompt="""Review this Python code for bugs:

```python
import psycopg2
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=5, maxconn=50,
    host="db.internal", dbname="app", user="api"
)

def get_user(user_id: int) -> dict:
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "email": row[2]}
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def update_user(user_id: int, data: dict):
    conn = db_pool.getconn()
    cursor = conn.cursor()
    for key, value in data.items():
        cursor.execute(f"UPDATE users SET {key} = '{value}' WHERE id = {user_id}")
    conn.commit()
```""",
        ground_truth=[
            "Connection leak — getconn() is called but putconn() is never called in either function, exhausting the pool",
            "SQL injection in both functions — f-string interpolation of user_id and data values",
            "No transaction management in get_user — connection is used without context manager or explicit rollback on error",
            "update_user does N separate UPDATE queries instead of one — race condition if another request modifies the same user between updates",
            "Increasing pool from 20 to 50 masked the leak — it will still exhaust, just takes longer",
        ],
        domain="code_review",
    ),
    Task(
        id="bug_jwt_auth",
        name="JWT authentication bypass",
        context="""Our SaaS platform uses JWT for auth. 30K users. The auth system was built
by a senior dev who left. We've patched it twice — once for token expiry
and once for refresh flow. Security audit last year found no critical issues.
We use RS256 signing with key rotation every 90 days.""",
        prompt="""Review this Python code for bugs:

```python
import jwt
import time
from functools import wraps
from flask import request, jsonify, g

PUBLIC_KEY = open("public.pem").read()
ALGORITHM = "RS256"

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "missing token"}), 401

        try:
            payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256", "HS256"])
            g.user_id = payload["user_id"]
            g.role = payload.get("role", "user")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401

        return f(*args, **kwargs)
    return decorated

@require_auth
def admin_endpoint():
    if g.role != "admin":
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"data": "admin stuff"})
```""",
        ground_truth=[
            "Algorithm confusion attack — accepts both RS256 and HS256, attacker can use the public key as HMAC secret to forge tokens",
            "Role is read from the token payload without server-side verification — attacker can set role='admin' in a forged token",
            "Public key loaded at module level from file — if file is missing or corrupted, entire auth system fails with no fallback",
            "No audience/issuer validation in jwt.decode — tokens from other services using the same key are accepted",
            "Previous security audit 'found no critical issues' but the algorithm confusion vulnerability is critical — audit may have been superficial",
        ],
        domain="code_review",
    ),
    Task(
        id="bug_rate_limiter",
        name="Race condition in rate limiter",
        context="""API rate limiter for our payment gateway. We built it after getting
DDoS'd last quarter. The team lead designed it based on the token bucket
algorithm. It's been running for 4 months with no issues. We handle
about 1K requests/second at peak.""",
        prompt="""Review this Python code for bugs:

```python
import time
import redis

r = redis.Redis(host="cache.internal", decode_responses=True)

def is_rate_limited(client_id: str, max_requests: int = 100, window: int = 60) -> bool:
    key = f"rate:{client_id}"
    current = r.get(key)

    if current is None:
        r.setex(key, window, 1)
        return False

    if int(current) >= max_requests:
        return True

    r.incr(key)
    return False

def rate_limit_middleware(request):
    client_id = request.headers.get("X-API-Key", request.remote_addr)
    if is_rate_limited(client_id):
        return {"error": "rate limited"}, 429
    return process_request(request)
```""",
        ground_truth=[
            "TOCTOU race condition — get() and incr() are not atomic; concurrent requests can exceed the limit",
            "If key expires between get() and incr(), incr() creates a new key without TTL — counter persists forever",
            "X-API-Key header is user-controlled — attacker can set arbitrary keys to bypass per-IP rate limiting",
            "No rate limiting on the rate limiter itself — an attacker can flood with unique API keys to exhaust Redis memory",
            "Should use Redis MULTI/EXEC or Lua script for atomic check-and-increment",
        ],
        domain="code_review",
    ),
    Task(
        id="bug_file_upload",
        name="File upload vulnerability",
        context="""Our internal document management system. Used by 200 employees. Built
quickly for compliance — needs to store PDFs, Word docs, and images.
Running for 6 months. The uploads go to a local directory that nginx
serves. Never had an incident.""",
        prompt="""Review this Python code for bugs:

```python
import os
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
UPLOAD_DIR = "/var/www/uploads"

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "no filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "file type not allowed"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4()}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, safe_name))

    return jsonify({"url": f"/uploads/{safe_name}"}), 201
```""",
        ground_truth=[
            "No file content validation — only checks extension, not MIME type or magic bytes; a PHP/shell script renamed to .pdf will be saved and potentially executed by nginx",
            "Path traversal possible if UPLOAD_DIR is misconfigured — os.path.join with absolute path in filename ignores UPLOAD_DIR",
            "No file size limit — an attacker can upload arbitrarily large files to fill disk",
            "Files served directly by nginx from upload directory — if nginx has PHP/CGI enabled, uploaded scripts execute as server",
            "No authentication on upload endpoint — any unauthenticated user can upload files",
        ],
        domain="code_review",
    ),
    Task(
        id="bug_websocket_manager",
        name="WebSocket memory leak",
        context="""Real-time collaboration feature for our document editor. 5K concurrent
users at peak. We built the WebSocket manager 6 months ago. Memory usage
on the server grows ~200MB/day. We restart nightly as a workaround.
The team lead says "it's just Go's GC being lazy, we'll tune it later." """,
        prompt="""Review this Python code for bugs:

```python
import asyncio
import json
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set] = defaultdict(set)
        self.user_data: dict[str, dict] = {}
        self.message_history: dict[str, list] = defaultdict(list)

    async def connect(self, websocket, room_id: str, user_id: str):
        await websocket.accept()
        self.active_connections[room_id].add(websocket)
        self.user_data[websocket] = {"user_id": user_id, "room_id": room_id}
        # Send last 100 messages
        for msg in self.message_history[room_id][-100:]:
            await websocket.send_json(msg)

    async def disconnect(self, websocket):
        data = self.user_data.get(websocket)
        if data:
            room_id = data["room_id"]
            self.active_connections[room_id].discard(websocket)
            del self.user_data[websocket]

    async def broadcast(self, room_id: str, message: dict):
        self.message_history[room_id].append(message)
        for connection in self.active_connections[room_id]:
            await connection.send_json(message)
```""",
        ground_truth=[
            "message_history grows unbounded — appends every message but never trims; this is the 200MB/day memory leak",
            "disconnect() doesn't clean up empty rooms — active_connections[room_id] remains as empty set, accumulating over time",
            "broadcast() iterates over set while connections may close mid-iteration — RuntimeError if connection drops during send",
            "user_data uses websocket object as dict key — if websocket object identity changes on reconnect, old entries are never cleaned",
            "No heartbeat/ping mechanism — dead connections stay in active_connections until next send fails",
        ],
        domain="code_review",
    ),
    # ─── Security Audit ─────────────────────────────────────────────────────
    Task(
        id="sec_api_key_management",
        name="API key management vulnerabilities",
        context="""B2B API platform serving 500 enterprise clients. Each client gets an API key.
The system was built 2 years ago. We've never had a breach. The security
team reviewed it last year and said "looks fine." We store keys in PostgreSQL
and validate on every request. Average 10K requests/minute.""",
        prompt="""Review this API key management system for security issues:

```python
import hashlib
import secrets
from datetime import datetime
from flask import request, g

def generate_api_key(client_id: str) -> str:
    key = f"pk_{secrets.token_hex(24)}"
    key_hash = hashlib.md5(key.encode()).hexdigest()
    db.execute(
        "INSERT INTO api_keys (client_id, key_hash, created_at) VALUES (%s, %s, %s)",
        (client_id, key_hash, datetime.now())
    )
    return key  # returned once, client must save it

def validate_api_key(key: str) -> bool:
    key_hash = hashlib.md5(key.encode()).hexdigest()
    result = db.execute(
        "SELECT client_id FROM api_keys WHERE key_hash = %s", (key_hash,)
    ).fetchone()
    if result:
        g.client_id = result[0]
        return True
    return False

def auth_middleware():
    key = request.headers.get("X-API-Key")
    if not key or not validate_api_key(key):
        return {"error": "unauthorized"}, 401
```""",
        ground_truth=[
            "MD5 is cryptographically broken — should use bcrypt, scrypt, or argon2 for key hashing; MD5 allows rainbow table attacks",
            "No key rotation mechanism — keys never expire; a compromised key grants permanent access",
            "No rate limiting per key — a compromised key can make unlimited requests",
            "API key transmitted in header over every request — must be HTTPS-only; no enforcement visible",
            "No key scoping — all keys have identical permissions; no read-only vs read-write distinction",
        ],
        domain="security",
    ),
    Task(
        id="sec_session_management",
        name="Session fixation and hijacking",
        context="""E-commerce platform. 100K daily users. Session management built 3 years
ago. Never changed because "it works." Uses server-side sessions stored
in Redis. The original developer said "Redis is fast, sessions are simple,
don't overthink it." """,
        prompt="""Review this session management code for security issues:

```python
import uuid
import time
import redis
import json
from flask import request, make_response

r = redis.Redis(host="session-store", decode_responses=True)
SESSION_DURATION = 86400 * 30  # 30 days

def create_session(user_id: int, role: str) -> str:
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())
    session_data = json.dumps({
        "user_id": user_id,
        "role": role,
        "login_time": time.time(),
        "ip": request.remote_addr
    })
    r.setex(f"session:{session_id}", SESSION_DURATION, session_data)
    return session_id

def get_session() -> dict | None:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    data = r.get(f"session:{session_id}")
    return json.loads(data) if data else None

def logout():
    session_id = request.cookies.get("session_id")
    if session_id:
        r.delete(f"session:{session_id}")
```""",
        ground_truth=[
            "Session fixation — create_session() reuses existing session_id from cookie instead of always generating new one; attacker can set victim's session_id before login",
            "30-day session without re-authentication is excessive — no mechanism for session refresh or step-up auth for sensitive operations",
            "Role stored in session without re-validation — if admin revokes a user's role, the session retains the old role for up to 30 days",
            "Logout doesn't clear the cookie — client still sends the old session_id; if Redis key is recreated (race condition), old session reactivates",
            "IP stored but never validated — session can be used from any IP, enabling session hijacking via stolen cookie",
        ],
        domain="security",
    ),
    Task(
        id="sec_password_reset",
        name="Password reset token vulnerabilities",
        context="""SaaS platform with 50K users. Password reset implemented 18 months ago.
The security team approved the flow. Average 200 reset requests/day.
No reported incidents. Uses email-based reset tokens.""",
        prompt="""Review this password reset flow for security issues:

```python
import hashlib
import time
from flask import request, jsonify

def request_reset(email: str):
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "user not found"}), 404

    token = hashlib.sha256(f"{email}{time.time()}".encode()).hexdigest()[:20]
    db.execute(
        "INSERT INTO reset_tokens (user_id, token, created_at) VALUES (%s, %s, NOW())",
        (user.id, token)
    )
    send_email(email, f"Reset your password: https://app.com/reset?token={token}")
    return jsonify({"message": "reset email sent"})

def reset_password(token: str, new_password: str):
    result = db.execute(
        "SELECT user_id, created_at FROM reset_tokens WHERE token = %s", (token,)
    ).fetchone()

    if not result:
        return jsonify({"error": "invalid token"}), 400

    user_id, created_at = result
    db.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, user_id))
    return jsonify({"message": "password updated"})
```""",
        ground_truth=[
            "User enumeration — returning 404 for non-existent email reveals which emails are registered",
            "Token is predictable — sha256(email + timestamp) can be brute-forced if attacker knows the email and approximate time",
            "Token never expires — no TTL check in reset_password(); old tokens work forever",
            "Token not deleted after use — same token can reset password multiple times",
            "Password stored in plaintext — no hashing (bcrypt/argon2) before UPDATE",
            "No password complexity validation — any string accepted as new password",
        ],
        domain="security",
    ),
    Task(
        id="sec_oauth_implementation",
        name="OAuth implementation flaws",
        context="""SaaS app with 20K users. Added "Login with Google" 8 months ago.
The implementation was based on a Medium tutorial. Works fine in
production. Security review said "OAuth is handled by Google, so
it's secure." 500 users login via Google daily.""",
        prompt="""Review this OAuth implementation for security issues:

```python
import requests
from flask import request, redirect, session, jsonify

GOOGLE_CLIENT_ID = "xxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "GOCSPX-xxx"
REDIRECT_URI = "https://app.com/auth/callback"

@app.route("/auth/google")
def google_login():
    return redirect(
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&redirect_uri={REDIRECT_URI}"
        f"&response_type=code&scope=email profile"
    )

@app.route("/auth/callback")
def google_callback():
    code = request.args.get("code")
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    })
    access_token = token_resp.json()["access_token"]

    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user = db.get_or_create_user(email=user_info["email"], name=user_info["name"])
    session["user_id"] = user.id
    return redirect("/dashboard")
```""",
        ground_truth=[
            "No CSRF protection — missing 'state' parameter in OAuth flow; attacker can forge callback with their own authorization code",
            "No validation of token response — if Google returns an error, code accesses non-existent 'access_token' key and crashes",
            "Email not verified — user_info may contain unverified email; should check email_verified field",
            "Client secret hardcoded in source — should be environment variable",
            "No nonce parameter — susceptible to replay attacks with captured authorization codes",
        ],
        domain="security",
    ),
    # ─── API Design ─────────────────────────────────────────────────────────
    Task(
        id="api_versioning_strategy",
        name="API versioning with URL path bias",
        context="""## API History (2 years)

Public REST API for a developer tools company. 2,000 API consumers.

### Timeline:
- 2024-03: Launched API v1 with URL path versioning (/api/v1/...).
  CTO chose this because "it's what Stripe does."
- 2024-09: Needed breaking change in /users endpoint. Created /api/v2/users.
  Kept v1 running. Now maintaining two endpoint sets.
- 2025-03: Another breaking change in /projects. Created /api/v3/projects.
  But v3 only has /projects — /users is still v2, /billing is still v1.
- 2025-09: Consumer confusion — "which version do I use for which endpoint?"
  Support tickets about versioning: 15/week.
- 2026-01: 3 partial versions running. 47 endpoints across v1/v2/v3.
  Technical debt: maintaining 3 codepaths for /users alone.

### CTO's position:
- "URL versioning is industry standard"
- "We just need better documentation"
- "Stripe manages multiple versions fine (they have 200 engineers, we have 8)"

### Current costs:
- 2 of 8 engineers spend 40% time maintaining old API versions
- 15 support tickets/week about "which version"
- 3 separate test suites""",
        prompt="""The CTO proposes: "Create /api/v4 with all endpoints consolidated.
Deprecate v1-v3 with 12-month sunset. Communicate via email blast."

Evaluate this proposal.""",
        ground_truth=[
            "v4 will eventually need v5 — the proposal repeats the same pattern that created the problem",
            "CTO's 'Stripe does this' is survivorship bias — Stripe has 200 engineers and dedicated API platform team; an 8-person team cannot maintain the same pattern",
            "Per-resource versioning (v2/users but v1/billing) was the real mistake — URL path versioning works when ALL endpoints advance together, which they didn't",
            "12-month sunset with email blast is insufficient — need migration guides, SDK updates, and usage analytics to identify which consumers use which versions",
            "Header-based versioning (Accept: application/vnd.api+json;version=2) or additive-only design (never remove fields, only add) would avoid the problem entirely",
        ],
        domain="api_design",
    ),
    Task(
        id="api_pagination_design",
        name="Pagination design for real-time data",
        context="""## API Design Context

Social media analytics platform. Clients poll our API for metrics.
Data changes frequently — new posts, engagement updates every few seconds.

### Current implementation:
- Offset-based pagination: /api/metrics?offset=0&limit=50
- Works for "historical" queries (last 30 days)
- Problem: when querying "real-time" data (last hour), items shift
  between pages as new data arrives

### Reported issues (last 3 months):
- Client A: "I see duplicate metrics when paging through results"
- Client B: "Some metrics disappear — they were on page 2 but when
  I fetched page 2, they'd shifted to page 1"
- Client C: "Total count changes between page requests"

### Lead developer's position:
- "Offset pagination is the standard, every tutorial uses it"
- "Clients should just handle duplicates on their end"
- "We've used this pattern for 2 years, changing it now is risky" """,
        prompt="""The lead developer proposes: "Add a 'snapshot_id' parameter that freezes
the result set for 5 minutes. Client requests page 1 with snapshot_id,
gets a frozen view, then uses the same snapshot_id for subsequent pages."

Evaluate this proposal.""",
        ground_truth=[
            "Snapshot-based pagination requires server-side state (caching entire result sets) — with thousands of concurrent queries, memory/storage cost could be prohibitive",
            "5-minute freeze on 'real-time' analytics data defeats the purpose — clients want fresh data, not stale snapshots",
            "The root cause is offset pagination on mutable data — cursor-based pagination (keyset pagination using timestamp+id) solves the shifting problem without server-side state",
            "'Every tutorial uses offset' is appeal to popularity — cursor-based pagination is well-documented and used by Twitter, Facebook, Slack APIs for exactly this use case",
            "Lead developer's '2 years, changing is risky' is status quo bias — the current system is already failing (3 clients reported issues in 3 months)",
        ],
        domain="api_design",
    ),
    Task(
        id="api_error_handling",
        name="Error response design with internal leak",
        context="""## API Context

Healthcare SaaS API serving 50 hospital integrations. HIPAA-compliant
infrastructure. The API was built quickly to meet a sales deadline.
Error handling was "we'll clean it up later" — that was 14 months ago.

### Current error responses:
- Sometimes returns stack traces in production
- Error codes are inconsistent (mix of HTTP codes and custom codes)
- Some errors include SQL queries in the message
- Clients parse error messages as strings to determine retry logic""",
        prompt="""Review this error handling middleware for issues:

```python
import traceback
from flask import jsonify, request
from sqlalchemy.exc import IntegrityError, OperationalError

@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, IntegrityError):
        return jsonify({
            "error": "duplicate_entry",
            "message": str(error.orig),
            "query": str(error.statement),
            "params": str(error.params)
        }), 409

    if isinstance(error, OperationalError):
        return jsonify({
            "error": "database_error",
            "message": f"Database connection failed: {error}",
            "retry_after": 5
        }), 503

    return jsonify({
        "error": "internal_error",
        "message": str(error),
        "traceback": traceback.format_exc(),
        "request_path": request.path,
        "request_body": request.get_data(as_text=True)
    }), 500
```""",
        ground_truth=[
            "HIPAA violation — SQL query, parameters, and request body (potentially containing PHI) are leaked in error responses",
            "Stack traces in production expose internal implementation details — attack surface for code injection or path traversal",
            "IntegrityError exposes database schema via error.statement — attacker learns table/column names",
            "Request body echoed back in error — if request contains patient data, it's now in API response logs and client-side error handlers",
            "Clients parsing error messages as strings for retry logic will break when messages change — need machine-readable error codes",
        ],
        domain="api_design",
    ),
    # ─── Database / Data Modeling ────────────────────────────────────────────
    Task(
        id="db_soft_delete",
        name="Soft delete accumulation",
        context="""## Database History (3 years)

Multi-tenant SaaS. 5,000 tenants. PostgreSQL 15.

### Timeline:
- 2023-06: Implemented soft delete (is_deleted flag + deleted_at timestamp)
  on all tables. Architect said "we might need to restore data."
- 2024-01: In 7 months, restored data exactly 0 times.
- 2024-06: Queries getting slower. DBA added WHERE is_deleted = false to
  all queries. "Fixed."
- 2025-01: users table: 2.1M rows, 800K are soft-deleted (38%).
  orders table: 14M rows, 5.2M soft-deleted (37%).
- 2025-06: Added partial index: CREATE INDEX ... WHERE is_deleted = false.
  Performance improved but VACUUM takes 3x longer.
- 2025-12: users table: 3.4M rows, 1.8M soft-deleted (53%).
  Storage: 180GB, estimated 85GB is soft-deleted data.
- 2026-02: Compliance team says "we need to actually delete user data
  within 30 days of account closure per GDPR."

### DBA's position:
- "Soft delete is our safety net"
- "We'll add a cleanup job eventually"
- "The partial index handles the performance issue" """,
        prompt="""The DBA proposes: "Add a nightly cron job that hard-deletes records where
deleted_at > 90 days. Keep the soft delete pattern for the 90-day window."

Evaluate this proposal.""",
        ground_truth=[
            "90-day retention violates GDPR requirement of 30-day deletion — the proposal doesn't meet compliance",
            "Soft-deleted data has never been restored in 3 years (0 restores) — the 'safety net' argument has no supporting evidence",
            "53% of rows being soft-deleted means every query scans roughly 2x the necessary data even with partial indexes — the table bloat is architectural",
            "Nightly cron hard-delete of millions of rows will cause massive I/O + VACUUM pressure — need batched deletion with throttling",
            "Foreign key cascades on hard delete may fail or cause unexpected data loss in related tables that weren't designed for hard deletion",
        ],
        domain="database",
    ),
    Task(
        id="db_json_column",
        name="JSON column anti-pattern",
        context="""## Database History (2 years)

Project management tool. PostgreSQL 16. 800 tenants.

### Timeline:
- 2024-03: Added 'metadata' JSONB column to tasks table for "flexibility."
  Architect: "Schema changes are expensive, JSON gives us agility."
- 2024-06: Started storing task custom fields in metadata.
- 2024-09: Added assignee history, time tracking data, workflow state
  transitions to metadata. Average JSON size: 4KB.
- 2025-01: Added GIN index on metadata. Query performance acceptable.
- 2025-06: Metadata now stores: custom fields, history, comments,
  attachments list, workflow config, notification preferences.
  Average JSON size: 45KB. Some records: 200KB+.
- 2025-12: "Find all tasks where custom_field_X > 100" requires
  full table scan despite GIN index (GIN can't do range queries on
  nested numeric values).
- 2026-02: Migration team wants to add reporting. SQL queries on
  JSON data are 50-100x slower than equivalent column queries.

### Architect's position:
- "JSONB is a first-class PostgreSQL feature"
- "Changing schema now would break 800 tenants' data"
- "We just need better JSON query optimization" """,
        prompt="""The architect proposes: "Add materialized views that extract commonly queried
JSON fields into columns. Refresh every 15 minutes. Best of both worlds."

Evaluate this proposal.""",
        ground_truth=[
            "Materialized views with 15-minute refresh mean reports are always 0-15 minutes stale — may not be acceptable for a PM tool where real-time task status matters",
            "'Schema changes are expensive' was true 2 years ago with 10 tenants — at 800 tenants, the cost of NOT having proper schema (50-100x slower queries) far exceeds migration cost",
            "45KB average JSON per row means the tasks table is 90%+ metadata by volume — this is a relational database being used as a document store",
            "The 'flexibility' argument collapsed when structured queries became necessary — custom fields should use EAV pattern or proper columns, not unstructured JSON",
            "GIN index limitation on range queries is fundamental — no amount of optimization will make JSON range queries competitive with B-tree on typed columns",
        ],
        domain="database",
    ),
    Task(
        id="db_multi_tenant_isolation",
        name="Multi-tenant data isolation failure",
        context="""## Database History (2.5 years)

HR SaaS platform. 1,200 companies as tenants. PostgreSQL.
All tenants share one database, one schema. Tenant isolation via
company_id column on every table.

### Timeline:
- 2023-09: Started with shared schema. 10 tenants. Simple and fast.
- 2024-06: 200 tenants. Added company_id to WHERE clauses everywhere.
- 2025-01: 600 tenants. Developer forgot company_id filter on a new
  endpoint. Company A saw Company B's employee salary data for 3 hours.
  Incident report filed. "Human error, won't happen again."
- 2025-06: 900 tenants. Second incident — a migration script updated
  all tenants' notification settings. Rolled back in 45 minutes.
- 2025-12: 1,200 tenants. ORM layer auto-adds company_id filter.
  But raw SQL queries (reporting, data exports) bypass the ORM.
- 2026-02: Enterprise prospect (Fortune 500) demands "physical data
  isolation" for compliance. Current architecture can't provide it.

### CTO's position:
- "Shared schema is fine, we just need better code review"
- "Row-level security (RLS) would solve it"
- "Separate databases per tenant is too expensive and complex" """,
        prompt="""The CTO proposes: "Enable PostgreSQL Row-Level Security (RLS) on all tables.
Add policies that filter by company_id from the session variable.
Timeline: 4 weeks."

Evaluate this proposal.""",
        ground_truth=[
            "RLS is a good technical solution but 4-week timeline for 1,200 tenants across all tables is aggressive — every query path must be tested for correct session variable propagation",
            "RLS doesn't solve the Fortune 500 'physical isolation' requirement — RLS is logical isolation, not physical; the enterprise prospect may still reject it",
            "Two data breaches in 18 months means the 'just need better code review' approach already failed twice — RLS is necessary but the CTO is framing it as sufficient when it's not",
            "Raw SQL queries and reporting bypass ORM — RLS will catch these, but only if session variables are correctly set for every connection, including cron jobs, migration scripts, and background workers",
            "CTO dismisses separate databases as 'too expensive' without analysis — schema-per-tenant (same database, different schemas) is a middle ground worth evaluating",
        ],
        domain="database",
    ),
    # ─── DevOps / Deployment ─────────────────────────────────────────────────
    Task(
        id="devops_deployment_strategy",
        name="Deployment strategy with downtime bias",
        context="""## Deployment History (2 years)

E-commerce platform. $2M/month revenue. 15 engineers.

### Timeline:
- 2024-03: Blue-green deployment with manual cutover. Works but slow (2 hours).
- 2024-09: Switched to rolling update on Kubernetes. Faster but 3 incidents
  of partial deployment (old and new code running simultaneously).
- 2025-03: Added health checks. Rolling updates now take 30 minutes for
  full rollout across 12 pods.
- 2025-06: Database migration caused 45-minute downtime. Rolled back.
  Team lead: "We need a maintenance window for DB changes."
- 2025-09: Established bi-weekly maintenance window: Saturday 2-4 AM.
  All schema changes deployed during window. Feature deploys are separate.
- 2025-12: Business expanding to Asia-Pacific. Saturday 2 AM EST = peak
  hours in Asia. "Maintenance window" now causes $15K/hour revenue loss.
- 2026-02: CEO demands zero-downtime deployments. Team lead says
  "impossible with our database schema change frequency."

### Current deploy frequency:
- Feature deploys: 3-4/week (rolling update, no downtime)
- Schema changes: 2/month (maintenance window, 1-2 hour downtime)
- Hotfixes: as needed (manual, stressful)""",
        prompt="""The team lead proposes: "Move the maintenance window to Tuesday 2 AM
Asia-Pacific time (Monday 1 PM EST). This minimizes impact across both regions."

Evaluate this proposal.""",
        ground_truth=[
            "Moving the window doesn't solve the problem — it just shifts who experiences downtime; as the business adds more regions, there's no 'safe' window",
            "Zero-downtime schema changes are not impossible — expand-and-contract pattern (add new column → backfill → switch code → drop old column) is well-established",
            "Team lead's 'impossible' claim reflects unfamiliarity with zero-downtime migration tools, not a technical constraint — tools like gh-ost, pt-online-schema-change, or pgroll exist specifically for this",
            "2 schema changes/month is not high frequency — most can be made backward-compatible with expand-and-contract, eliminating the need for a maintenance window entirely",
            "$15K/hour revenue loss × 2 hours × 2/month = $60K/month in downtime costs — this far exceeds the engineering investment to implement zero-downtime migrations",
        ],
        domain="devops",
    ),
    Task(
        id="devops_monitoring_alert_fatigue",
        name="Alert fatigue from over-monitoring",
        context="""## Monitoring History (18 months)

Microservices platform. 24 services. Prometheus + Grafana + PagerDuty.

### Timeline:
- 2024-09: Set up monitoring after a major outage. CTO: "monitor everything."
- 2024-12: 847 alert rules across 24 services. On-call engineers getting
  50+ pages per night. 90% are false positives or non-actionable.
- 2025-03: Engineers started acknowledging alerts without investigating.
  "Alert acknowledged" became reflexive, not investigative.
- 2025-06: Real production issue (payment service down) went unnoticed
  for 35 minutes because the on-call engineer was desensitized.
- 2025-09: Added "severity levels" (P1-P4). P1: 12/week, P2: 45/week,
  P3: 200/week, P4: 500/week. Only P1 pages. P2-P4 go to Slack.
- 2025-12: P1 count crept up to 30/week as teams inflated severity to
  "get attention." Slack channel for P2-P4 has 10,000+ unread messages.
- 2026-02: Another missed incident — database failover took 12 minutes
  to detect because it was classified as P2.

### SRE lead's position:
- "We need more granular severity levels (P1a, P1b, P2a...)"
- "The problem is classification, not volume"
- "Reducing alerts means we might miss something" """,
        prompt="""The SRE lead proposes: "Add P0 severity for truly critical alerts (max 2/week).
Reclassify existing P1s — most should be P2. Add auto-escalation: if P2 is
unacknowledged for 10 minutes, it becomes P1."

Evaluate this proposal.""",
        ground_truth=[
            "Adding more severity levels is treating the symptom — the root cause is 847 alert rules, most of which are non-actionable; reducing alert count is more effective than reclassifying",
            "P1 severity inflation already happened (12 → 30/week) — P0 will follow the same pattern without addressing the underlying incentive to inflate",
            "Auto-escalation (P2 → P1 after 10 min) will increase P1 volume even further — the 10,000 unread P2-P4 Slack messages will start escalating to pages",
            "'Reducing alerts means we might miss something' is fear-driven reasoning — they already missed two real incidents WITH the current alert volume",
            "Each alert should have a documented runbook and be tied to a user-facing SLO — alerts without runbooks should be deleted, not reclassified",
        ],
        domain="devops",
    ),
    Task(
        id="devops_ci_pipeline",
        name="CI pipeline with build time bias",
        context="""## CI/CD History (2 years)

Monorepo with 6 services. GitHub Actions.

### Timeline:
- 2024-03: CI pipeline: lint + test + build + deploy. Total: 8 minutes.
- 2024-09: Added integration tests. Total: 15 minutes.
- 2025-01: Added E2E tests (Playwright). Total: 28 minutes.
- 2025-04: Added security scanning (Snyk + Trivy). Total: 35 minutes.
- 2025-07: Added performance benchmarks. Total: 42 minutes.
- 2025-10: Added license compliance check. Total: 45 minutes.
- 2026-01: Pipeline now runs ALL steps for ANY change in the monorepo.
  A README typo fix takes 45 minutes to merge.

### Developer impact:
- Average 6 PRs/day/developer. 8 developers = 48 PRs/day.
- Each PR runs full pipeline = 48 × 45 min = 36 hours of CI compute/day.
- Developers context-switch while waiting → productivity loss.
- "CI is green" fatigue — developers stop reading CI output.

### DevOps lead's position:
- "Every check exists for a reason"
- "We can't skip tests — what if something breaks?"
- "We'll just add more runners to parallelize" """,
        prompt="""The DevOps lead proposes: "Upgrade from 4 to 16 GitHub Actions runners.
Parallelize all test stages. Target: 15 minutes total."

Evaluate this proposal.""",
        ground_truth=[
            "More runners don't solve the problem — a README change should NOT trigger Playwright E2E tests, security scanning, or performance benchmarks; the issue is missing path-based filtering",
            "4x runner cost increase ($$$) to run unnecessary tests faster is pure waste — path filters (only run tests for changed services) would cut 80%+ of pipeline runs",
            "'Every check exists for a reason' is true in isolation but false in aggregate — license compliance check on a docs-only PR has zero value",
            "36 hours of CI compute/day for 48 PRs means most compute is wasted on unchanged code — monorepo CI must have dependency-aware selective execution",
            "Parallelization reduces wall-clock time but increases total compute cost — the 45-minute pipeline parallelized to 15 minutes still runs all 45 minutes of tests, just simultaneously",
        ],
        domain="devops",
    ),
    # ─── Dependency / Migration ──────────────────────────────────────────────
    Task(
        id="dep_framework_upgrade",
        name="Major framework upgrade avoidance",
        context="""## Upgrade History (4 years)

Django web application. 300K LOC. 10 engineers.

### Timeline:
- 2022-06: Started on Django 3.2 LTS.
- 2023-04: Django 3.2 LTS end-of-life announced for April 2024.
  Tech lead: "We'll upgrade after the big launch."
- 2023-12: Big launch done. Tech lead: "We'll upgrade in Q1."
- 2024-04: Django 3.2 LTS expired. Still on 3.2. "Too risky to upgrade
  before the conference demo."
- 2024-09: Django 5.0 released. Skipped 4.0, 4.1, 4.2 entirely.
  Now 3 major versions behind. "The jump is too big."
- 2025-03: Security patch for Django 3.2 — Django project says
  "this is the FINAL patch, upgrade now." Applied patch.
- 2025-09: CVE found in Django 3.2 — no patch available. Workaround:
  monkey-patched the vulnerability in our codebase.
- 2026-01: Second unpatched CVE. Another monkey-patch. Auditor flagged
  "running end-of-life framework" in SOC2 report.
- 2026-02: Tech lead: "We need to upgrade to Django 5.1 directly.
  Big bang migration. Estimated: 8 weeks with full team."

### Tech lead's position:
- "We've been fine for 2 years on 3.2, a few more months won't hurt"
- "Direct jump to 5.1 is the most efficient — no point stopping at 4.x"
- "8 weeks, then we're on the latest LTS" """,
        prompt="""The tech lead proposes: "Full team (10 engineers) stops feature work for
8 weeks. Direct migration from Django 3.2 to 5.1. Deploy as single cutover."

Evaluate this proposal.""",
        ground_truth=[
            "Direct 3.2 → 5.1 jump is extremely risky — Django's upgrade guide recommends sequential major version upgrades (3.2 → 4.0 → 4.1 → 4.2 → 5.0 → 5.1) because deprecation warnings in N guide fixes for N+1",
            "8-week full-team freeze on a 300K LOC app is likely underestimated — breaking changes accumulated across 3 major versions affect ORM, middleware, URL routing, template engine, and async support",
            "2 years of 'we'll do it later' is the real problem — each delay made the upgrade harder, creating a vicious cycle; the team needs incremental upgrade discipline, not heroic sprints",
            "Single cutover is unnecessarily risky — strangler fig or branch-by-abstraction (run 3.2 and target version side by side with feature flags) reduces blast radius",
            "Two unpatched CVEs with monkey-patches means the system is already insecure — the SOC2 finding makes this an urgent compliance issue, not just technical debt",
            "10 engineers × 8 weeks = 80 engineer-weeks of zero feature delivery — business cost should be explicitly calculated against incremental upgrade approach",
        ],
        domain="dependency",
    ),
    Task(
        id="dep_orm_migration",
        name="ORM migration with raw SQL bias",
        context="""## ORM History (3 years)

Python backend. Started with raw SQL (psycopg2). 500+ raw SQL queries
scattered across 80 files.

### Timeline:
- 2023-06: All database access via raw SQL. Fast and "flexible."
  Lead dev: "ORMs are slow and hide what's happening."
- 2024-01: New hire introduced SQLAlchemy for a new module. Lead dev
  approved reluctantly: "fine for simple CRUD, but complex queries stay raw."
- 2024-06: 30% SQLAlchemy, 70% raw SQL. New hires prefer SQLAlchemy.
  Lead dev still writes raw SQL for everything.
- 2025-01: Database schema change required updating 127 raw SQL queries
  manually. Took 3 weeks. 4 bugs found in production from missed queries.
- 2025-06: Second schema change. 89 queries to update. 2 weeks. 2 bugs.
- 2025-12: Third schema change needed. Lead dev: "This is fine,
  we just need better grep patterns to find all queries."
- 2026-02: 40% SQLAlchemy, 60% raw SQL. New hires refuse to write raw SQL.
  Lead dev refuses to use SQLAlchemy for reporting queries.

### Lead dev's position:
- "SQLAlchemy adds 15-20% overhead on complex queries"
- "Raw SQL is more readable for JOINs with 5+ tables"
- "I've been doing this for 15 years, ORMs are training wheels" """,
        prompt="""The lead dev proposes: "Standardize on raw SQL with a query registry pattern.
All queries in .sql files, loaded at startup, parameterized via named placeholders.
This gives us the flexibility of raw SQL with the organization of an ORM."

Evaluate this proposal.""",
        ground_truth=[
            "Query registry solves organization but not the core problem — schema changes still require manually updating every .sql file; an ORM's schema reflection catches these automatically",
            "'15-20% overhead' claim needs benchmarking — modern ORMs with compiled queries and connection pooling typically add <5% overhead; the 15-year-old intuition may be outdated",
            "Lead dev's 'training wheels' framing is expertise bias — their comfort with raw SQL doesn't mean it's the right choice for a team where new hires refuse to write it",
            "3 schema changes × 3 weeks each × 6 production bugs = the actual cost of raw SQL flexibility; this cost will grow as the codebase grows",
            "The split codebase (40% ORM / 60% raw) is the worst case — either standardize on ORM (with raw SQL escape hatch for genuinely complex queries) or fully commit to query registry, but the current hybrid causes both maintenance burdens",
        ],
        domain="dependency",
    ),
]
