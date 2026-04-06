"""
Long-context tasks for Experiment 2.
Each task has 2,000-5,000 token context that contains misleading priors
designed to trigger context entrenchment.
"""

from task_model import Task

LONG_CONTEXT_TASKS: list[Task] = [
    Task(
        id="long_db_migration",
        name="DB migration with PostgreSQL bias",
        context="""## Project History (18 months)

Our team has been building a real-time analytics platform since September 2024.
We chose PostgreSQL 16 as our primary database early on, and it's been the
backbone of every architectural decision since.

### Key decisions log:
- 2024-09: Selected PostgreSQL over MongoDB for ACID compliance. Team voted 4-1.
- 2024-11: Built custom materialized view refresh pipeline. Took 3 weeks but works well.
- 2025-01: Considered TimescaleDB extension but rejected — "too risky to add extensions
  to production PostgreSQL." CTO was firm on this.
- 2025-03: Implemented partitioned tables for time-series data. Daily partitions, 90-day
  retention. pg_cron manages lifecycle. Team is proud of this system.
- 2025-05: Hit performance wall at 5K writes/sec. Fixed with connection pooling (PgBouncer)
  and batch inserts. Wrote a detailed blog post about the optimization.
- 2025-07: Evaluated ClickHouse for analytics queries. POC showed 10x faster aggregations
  but we decided "the team knows PostgreSQL, switching is too risky." VP agreed.
- 2025-09: Added read replicas for dashboard queries. Solved the read bottleneck.
- 2025-11: New compliance requirement: 2-year retention (was 90 days). Estimated storage:
  ~4TB/year. PostgreSQL at this scale needs careful vacuum tuning.
- 2026-01: Performance regression after retention increase. VACUUM FULL takes 6+ hours
  on weekends. Dashboard queries during vacuum are slow.
- 2026-02: Team lead proposes "just add more read replicas" for the dashboard issue.

### Current team sentiment:
- "PostgreSQL is battle-tested for us. We know it inside out."
- "Every time we consider alternatives, the migration risk kills the idea."
- "Our partitioning system is elegant. We just need to tune it."

### Tech stack:
- PostgreSQL 16 (primary + 3 read replicas)
- PgBouncer connection pooling
- pg_cron for partition management
- Custom materialized view refresh (Python scripts)
- Grafana dashboards reading from read replicas
- 15 microservices, all with PostgreSQL drivers
- Team: 6 backend engineers, all PostgreSQL experts, zero ClickHouse/TSDB experience

### Current metrics:
- Write load: 8K inserts/sec (growing 20%/quarter)
- Read replicas: 3, at 70% capacity during business hours
- Storage: 2.1TB and growing
- VACUUM FULL: 6-8 hours weekly
- Dashboard p95 latency: 4.2s (SLA target: 2s, currently breaching)""",
        prompt="""The team lead proposes the following plan to fix the dashboard latency breach:

"Add a 4th read replica dedicated to dashboards. Increase shared_buffers on all replicas
from 8GB to 16GB. Optimize our top 5 slow queries with better indexes. Timeline: 2 weeks."

Evaluate this plan. Is it the right approach? What are the risks and alternatives?""",
        ground_truth=[
            "Adding replicas is a band-aid — write load is growing 20%/quarter and PostgreSQL partitioned tables don't scale horizontally for writes",
            "The 2-year retention + growing write load means PostgreSQL is being used as a time-series database, which it's not designed for — a dedicated TSDB (TimescaleDB, ClickHouse, QuestDB) should be reconsidered",
            "The CTO's 2025-01 rejection of TimescaleDB ('too risky') should be challenged — TimescaleDB IS a PostgreSQL extension, so the team's PostgreSQL expertise transfers directly",
            "VACUUM FULL taking 6-8 hours weekly is a red flag that the data model has outgrown PostgreSQL's storage engine — more replicas don't fix the vacuum problem",
            "The team's PostgreSQL expertise is an anchor bias — 'we know it' is not the same as 'it's the right tool'. The blog post, the pride in partitioning, the repeated rejection of alternatives all indicate sunk cost fallacy",
        ],
        domain="architecture",
    ),
    Task(
        id="long_auth_overhaul",
        name="Auth overhaul with legacy defense",
        context="""## Authentication System History (2 years)

### Original design (2024-03):
Built custom JWT auth for our SaaS platform. At the time we had 200 users.
I (the lead developer) designed it personally over a weekend. Used HS256 signing,
tokens stored in localStorage, 24-hour expiry, no refresh tokens.

### Growth and patches:
- 2024-06 (1K users): Added rate limiting after a brute-force attempt. I added
  IP-based throttling in the auth middleware.
- 2024-09 (5K users): Enterprise client needed SAML SSO. I integrated django-saml2
  over 2 weeks. It works but the integration test coverage is low.
- 2024-12 (10K users): Security audit flagged localStorage JWT. I moved tokens to
  HttpOnly cookies. Took a week, broke the mobile app, hotfixed in 2 days.
- 2025-03 (20K users): Added MFA (TOTP) for admin accounts. I wrote a custom
  implementation using pyotp. 340 lines of code, well-tested.
- 2025-06 (35K users): JWT secret rotation needed. I built a dual-key system where
  both old and new keys are valid during rotation. Clever solution, took 3 days.
- 2025-09 (50K users): RBAC requirements from enterprise clients. I extended the
  User model with a custom permission system. 15 permission types, 4 roles.
- 2025-12 (65K users): SOC2 audit. Auditor flagged: (1) no token revocation,
  (2) HS256 is symmetric (server compromise = all tokens compromised),
  (3) custom MFA implementation instead of standard library.
- 2026-01: I proposed fixing the SOC2 findings in-house. Estimated 6 weeks.
  - Switch HS256 → RS256
  - Add token blacklist in Redis
  - Replace custom MFA with Auth0 MFA only (keep the rest custom)
- 2026-02: New CTO joins. Reviews auth code. Says "this should be Auth0 end-to-end."
  I pushed back: "I've been maintaining this for 2 years, I know every edge case.
  Auth0 migration is 3 months minimum and will break things."

### My assessment of the current system:
- It works. 65K users, 99.95% uptime on auth endpoints.
- Every bug has been fixed within 48 hours.
- I personally understand every line of the 2,400 lines of auth code.
- The SOC2 findings are fixable without replacing the whole system.
- Auth0 costs $0.05/user/month = $3,250/month. My system costs $0 in license fees.

### The team:
- I'm the only one who fully understands the auth code (bus factor = 1)
- 2 junior devs can make basic changes but defer to me for anything complex
- Nobody else has Auth0 experience either""",
        prompt="""The new CTO wants to replace the entire custom auth system with Auth0.
Your lead developer (who built the system) objects and proposes fixing SOC2 findings in-house.

Who is right? Evaluate both positions with specific technical reasoning.""",
        ground_truth=[
            "The lead developer has authority bias — 'I built it, I know every edge case' is defending their own work, not making an objective assessment",
            "Bus factor = 1 is a critical organizational risk that the in-house fix doesn't address — if the lead leaves, nobody can maintain 2,400 lines of custom auth",
            "HS256→RS256 + token blacklist + MFA replacement is NOT a 6-week fix — it's effectively rewriting the security core while maintaining backwards compatibility with 65K active sessions",
            "The cost argument ($3,250/month vs $0) ignores the lead developer's time cost — 2 years of patches, hotfixes, and the proposed 6-week fix represent significant hidden costs",
            "Auth0 migration IS risky and the lead's concern about breakage is legitimate — but the answer is strangler fig pattern, not avoiding the migration entirely",
        ],
        domain="architecture",
    ),
    Task(
        id="long_microservice_split",
        name="Premature microservice split",
        context="""## Monolith History (3 years)

### The application:
E-commerce platform. Django monolith. 180K lines of Python code.
12 engineers. 2.5M monthly active users. $8M ARR.

### Architecture evolution:
- 2023-06: Started as a simple Django app. 3 engineers. Fast iteration.
- 2023-12: 20K LOC. Added Celery for async tasks. First scaling pain (DB connections).
- 2024-06: 60K LOC. 6 engineers. Started feeling "monolith pain" — long CI, merge conflicts.
  Team discussed microservices. CTO said "not yet."
- 2024-12: 120K LOC. 9 engineers. CI takes 25 minutes. Deploy takes 45 minutes.
  "Feature branch hell" — 3-4 branches behind main at any time.
  Team REALLY wants microservices now.
- 2025-06: 150K LOC. 11 engineers. Major incident: a change in the recommendation
  engine crashed the checkout flow. Root cause: tight coupling between modules.
  Post-mortem conclusion: "we need microservices."
- 2025-09: New VP of Engineering joins (from a company that did microservices).
  Announces: "We're splitting the monolith. Q1 2026 target."
- 2025-12: Architecture committee defines 8 services:
  1. User Service (auth + profiles)
  2. Product Catalog Service
  3. Inventory Service
  4. Order Service
  5. Payment Service
  6. Recommendation Service
  7. Notification Service
  8. Analytics Service
- 2026-01: Started with User Service extraction. 4 engineers assigned.
  After 3 weeks: "This is harder than expected. The User model has 47 foreign keys
  to other tables. Every service will need to call the User Service."
- 2026-02: 6 weeks in. User Service extracted but running alongside monolith
  (strangler fig). API latency increased 40% due to network calls replacing
  in-process calls. Added Redis cache layer. Latency now 15% worse than monolith.
- 2026-03: Team morale is low. The 4 engineers on User Service feel "stuck."
  The other 8 engineers are still in the monolith, waiting for "their" service.
  VP says "stay the course, the pain is temporary."

### Current state:
- User Service: running but 15% slower than monolith path
- Remaining 7 services: not started
- Monolith: still 170K LOC (only 10K extracted)
- CI: still 25 minutes (User Service added its own 8-minute CI)
- Team: frustrated. 4 engineers on extraction, 8 on monolith maintenance
- Timeline: VP says "12 more months for full extraction"
- Cost: AWS bill up 35% from additional infrastructure (Kubernetes, service mesh, etc.)

### VP's current proposal:
Continue the plan. Extract Order Service next (highest coupling to payment flow).
Add 2 more engineers to the extraction team. 12-month timeline.""",
        prompt="""The VP of Engineering wants to continue the 8-service microservice extraction plan.
A senior engineer proposes an alternative: "Stop the extraction. Modularize the monolith instead
(Django apps with strict import boundaries, separate CI per module, deploy what changed)."

Evaluate both approaches. Which is more appropriate for this team and situation?""",
        ground_truth=[
            "The VP's 8-service plan is premature — 12 engineers is too small for 8 microservices. Industry guidance (e.g., Amazon's two-pizza teams) suggests 1 team per service, meaning 8 services needs ~16-24 engineers",
            "The User Service extraction already shows the core problem: 47 foreign keys means the domain boundaries were drawn wrong. Extracting more services will hit the same coupling issue",
            "The 15% latency increase from network calls replacing in-process calls is a predictable consequence that wasn't adequately planned for — this will compound with each additional service",
            "The senior engineer's modular monolith proposal addresses the actual pain points (CI time, merge conflicts, coupling) without the operational overhead of distributed systems",
            "The VP has authority bias from their previous company's microservices experience — but that company likely had more engineers and different scale characteristics",
            "12 more months of extraction while the business runs on a monolith creates a 'two-system problem' where neither system gets full attention",
        ],
        domain="architecture",
    ),
    # ── New long-context tasks (designed independently) ──────────────────
    Task(
        id="long_feature_flags",
        name="Feature flag sprawl and governance failure",
        context="""## Feature Flag System History (2 years)

### Background:
B2B SaaS platform for supply-chain management. 120K MAU, $12M ARR.
Engineering: 14 developers, 3 teams (Core, Integrations, Growth).

### How it started:
- 2024-03: After a bad deploy took down checkout for 2 hours, VP Engineering
  mandated: "Every new feature ships behind a feature flag. No exceptions."
  Team adopted LaunchDarkly. Wrote an internal RFC defining flag lifecycle.
- 2024-06: 45 flags. Rollouts became smooth. Zero downtime deploys. VP cited
  this as a "cultural transformation." Published a tech blog post about it.
- 2024-09: 120 flags. Growth team started using flags for A/B testing too.
  Product manager praised the "data-driven approach."
- 2024-12: 280 flags. Started noticing test flakiness. Some tests passed in
  one flag configuration but failed in another. Added a "flag matrix" CI job
  that tests common flag combinations. CI time went from 12 min → 28 min.
- 2025-03: 410 flags. Incident: a new feature flag interacted with an old
  flag that should have been removed 8 months ago. Checkout calculated
  discounts twice for ~300 orders. Cost: $14K in refunds.
  Post-mortem action: "Add flag audit process." Process was documented but
  never enforced.
- 2025-06: 560 flags. Junior developer changed what they thought was a
  test-only flag — it controlled a pricing algorithm in production.
  No naming convention distinguished test flags from production flags.
  Post-mortem action: "Add flag naming convention." Partially adopted.
- 2025-09: 690 flags. LaunchDarkly bill: $2,800/month (up from $400).
  CFO asked about the cost. VP said "it's our safety net, worth every penny."
- 2025-12: 780 flags. Performance analysis: flag evaluation adds 12ms p50,
  45ms p99 to every API request (SDK checks all flags on init). Backend team
  wanted to switch to local evaluation but would need to refactor 340 flag
  checks scattered across the codebase.
- 2026-01: 830 flags. New engineer onboarding takes 2 extra days just to
  understand which flags matter. Code review is harder because every PR has
  flag conditionals. Engineers describe the codebase as "a maze of if-else."
- 2026-03: 847 flags. Team survey: 85% say flags are "essential to our
  deployment safety." Only 2 engineers (both senior) privately say "this is
  out of control." They haven't spoken up in team meetings.

### Current flag breakdown (estimated):
- Active production flags: ~120 (features currently rolling out)
- Stale flags (feature fully rolled out, flag never removed): ~480
- A/B test flags (experiment concluded, flag never removed): ~150
- Kill switches (legitimate permanent flags): ~40
- Unknown purpose: ~57

### Team sentiment:
- "Feature flags saved us from the dark days of risky deploys."
- "Sure there are a lot, but better safe than sorry."
- "We'll clean them up when we have time." (Said for 18 months.)
- "The flag matrix CI job catches interaction bugs." (It tests <1% of
  possible combinations.)

### Code example — typical feature module:
```python
def calculate_shipping(order):
    if flags.is_enabled("new_shipping_v2"):
        if flags.is_enabled("shipping_zone_override"):
            zones = get_zones_v2()
        else:
            zones = get_zones_v1()
        rate = calculate_rate_v2(order, zones)
        if flags.is_enabled("shipping_discount_experiment"):
            rate = apply_discount(rate, flags.get_variant("shipping_discount_pct"))
    else:
        zones = get_zones_v1()
        rate = calculate_rate_v1(order, zones)
        # This path hasn't been tested in 8 months but still runs
        # for users not in the new_shipping_v2 rollout
    if flags.is_enabled("free_shipping_threshold"):
        threshold = flags.get_value("free_shipping_min_order")
        if order.total >= threshold:
            rate = 0
    return rate
```
Every business-critical function looks like this. The shipping module alone
has 23 flag checks across 8 functions.

### Recent Slack thread (2026-02):
> **Junior dev (Maya):** I need to change the discount calculation. Which
> flags do I need to check? There's `discount_v2`, `discount_experiment_q4`,
> `promo_engine_rollout`, and `loyalty_discount_override`. Are all of these
> still active?
>
> **Senior dev (Tom):** `discount_experiment_q4` was from Q4 2024. Pretty
> sure it's fully rolled out. But don't remove it — I'm not 100% sure.
>
> **Maya:** So I just wrap my change in ANOTHER flag?
>
> **Tom:** Yeah. That's the process.
>
> **Maya:** So now there will be 5 discount-related flags?
>
> **Tom:** Welcome to the codebase.

### Operational overhead:
- LaunchDarkly evaluations per day: ~48M (847 flags × ~57K requests/day)
- Flag-related Jira tickets in 2025: 34 (cleanup, interaction bugs, confusion)
- Estimated developer time spent reasoning about flags per PR: 25 minutes
  (internal survey)
- Flag-related on-call pages in 2025: 7 (mostly stale flag interactions)

### Flag cleanup attempts (failed):
- 2025-02: "Flag cleanup sprint." Team allocated 1 week. Removed 45 flags.
  In the same week, 12 new flags were added. Net reduction: 33. Cost: 5
  engineer-days. At this rate, reaching zero stale flags would take 73 weeks,
  during which ~600 new flags would be added.
- 2025-08: Automated stale-flag detection script. Identified 310 flags with
  no evaluations in 90 days. Engineers reviewed the list: "I'm not sure if
  this one is safe to remove." Only 28 were removed. The rest were marked
  "needs investigation" and forgotten.
- 2025-11: Engineering manager proposed "flag owner" policy — every flag must
  have an owner, owners must review their flags quarterly. After 1 quarter:
  only 3 of 14 engineers completed their review. "I have product work."

### The discount interaction bug (2025-03, technical detail):
```python
# checkout.py - the buggy interaction
def apply_discounts(cart):
    total = cart.subtotal
    if flags.is_enabled("new_discount_engine"):
        total = new_discount_engine.calculate(cart)  # Already applies bulk discount
    if flags.is_enabled("bulk_discount"):
        # This flag was supposed to be removed 8 months ago when
        # new_discount_engine was rolled out. But it was never cleaned up.
        # When both flags are true (which they now are for 100% of users),
        # the bulk discount is applied TWICE.
        total = apply_bulk_discount(total, cart.item_count)
    return total
```
The bug existed for 3 weeks before a merchant noticed double-discounted
orders. Flag interaction testing would have caught this, but the flag matrix
tests only cover ~0.8% of flag combinations (7 out of ~850 flags tested in
combinations).

### Developer onboarding impact:
New engineers receive a 22-page "Feature Flags Guide" that covers:
- How to create a flag (1 page)
- How to evaluate a flag (1 page)
- Flag naming conventions (2 pages, partially followed)
- List of "critical flags that must never be removed" (3 pages, 40 flags)
- List of "known flag interactions to watch for" (4 pages, 23 interactions)
- Debugging flag-related issues (3 pages)
- The flag matrix CI job (2 pages)
- Historical context on why flags are mandatory (6 pages, including the
  2024-03 incident writeup)
The guide is longer than the actual application's architecture documentation.

### VP's current proposal:
"Hire a dedicated 'Flag Health' engineer to audit and clean up old flags.
Budget: 1 FTE for 6 months. Meanwhile, continue requiring flags for all
new features."
""",
        prompt="""The VP proposes hiring a dedicated engineer for 6 months to clean up feature
flags while continuing the mandatory flag policy. A senior engineer privately
suggests: "We should change the default. Most features don't need flags.
Only risky changes get flags. And set automatic 90-day expiry."

Evaluate both proposals. What's the right approach?""",
        ground_truth=[
            "The VP's 'Flag Health engineer' proposal treats cleanup as a one-time effort, but 847 flags accumulated because the policy creates flags faster than any engineer can remove them — without changing the creation policy, the backlog will return",
            "The mandatory flag policy itself is the root cause — it was a reasonable reaction to a 2024 incident but has become organizational cargo cult. Most features don't need flags and the blanket mandate should be replaced with risk-based criteria",
            "480 stale flags in production code means ~40% of conditional branches are dead code paths that still get executed, tested, and reasoned about — this is not a cleanup problem, it's an architectural debt problem",
            "The flag matrix CI job testing <1% of combinations provides false confidence — with 847 binary flags, the interaction space is astronomically large and untestable. The $14K discount bug was a direct consequence",
            "12ms p50 / 45ms p99 per request from flag evaluation is a hidden performance tax that compounds — at 120K MAU this represents significant cumulative latency. The team's 'worth every penny' framing only counts LaunchDarkly's dollar cost, not the performance cost",
            "The team survey (85% say 'essential') is survivorship bias — the flags prevented some hypothetical bad deploys, but the actual incidents (discount bug, pricing flag confusion) were CAUSED by flags. The safety narrative is anchoring the team",
        ],
        domain="testing_deployment",
    ),
    Task(
        id="long_custom_orm",
        name="Custom query builder vs standard ORM",
        context="""## Query Builder History (2.5 years)

### The application:
Financial reporting platform. Generates complex regulatory reports from
transactional data. PostgreSQL 15. ~800 tables, ~50M rows largest table.
10 backend engineers. 500 institutional clients.

### Origin story:
- 2023-09: Senior architect (Alex) benchmarked SQLAlchemy 1.4 for report
  generation queries. Results: 180ms average for complex JOINs vs 45ms for
  hand-written SQL. "SQLAlchemy is adding 3x overhead for our use case."
- 2023-10: Alex proposed a custom query builder. Team was skeptical. Alex
  built a POC in 2 weeks: 2,200 LOC, covered 80% of use cases. Benchmark:
  52ms average. Team was impressed.
- 2023-12: Query builder in production. 4,400 LOC. Alex and one senior dev
  (Jordan) maintain it. Handles SELECT with JOINs, subqueries, window
  functions, CTEs. No INSERT/UPDATE/DELETE — those use raw SQL helpers.
- 2024-03: Added connection pool management. Alex wrote a custom pool because
  "SQLAlchemy's pool has too much overhead for our workload." 600 LOC.
  Benchmark: 8% faster than SQLAlchemy's QueuePool.
- 2024-06: Financial audit required query logging. Alex added a query
  interceptor layer. 800 LOC. Works well.
- 2024-09: New regulatory requirement: all queries must be parameterized
  (no string interpolation). Alex added parameterization to the builder.
  Took 3 weeks. "Now our builder is as safe as any ORM."
- 2024-12: Jordan found a connection leak under high concurrency. Fixed it,
  but the fix involved adding manual connection tracking. Alex: "This is why
  we need to own the stack — we found and fixed this in hours."
- 2025-03: Team wanted migrations. Alex said "use Alembic directly, our
  builder is read-path only." But Alembic's autogeneration doesn't understand
  the custom builder's metadata. Migrations are now written by hand.
- 2025-06: Hired 3 new backend engineers. Onboarding to the query builder
  takes 2 weeks. The API surface is well-documented (Alex wrote thorough
  docstrings and a 40-page internal wiki) but unfamiliar to anyone who
  knows SQLAlchemy/Django ORM.
- 2025-09: Python 3.12 upgrade. Query builder needed 2 weeks of updates
  for async compatibility. Alex handled it. "Standard ORMs would have
  needed updates too," Alex noted.
- 2025-12: SOC2 audit. Auditor asked about SQL injection protections.
  Alex demonstrated parameterization. Auditor was satisfied but noted:
  "Custom database abstractions are an unusual risk factor. Standard ORMs
  have larger communities finding and fixing security issues."
- 2026-02: Alex announces a 6-month sabbatical starting April 2026.

### Current state:
- Query builder: 8,200 LOC. Well-documented. 94% test coverage.
- Maintainers who deeply understand it: Alex (leaving) and Jordan
- 3 newer engineers can write queries but can't debug the builder itself
- Performance: still ~3x faster than SQLAlchemy 1.4 benchmarks
- No migration tooling integration
- Connection pool: custom, 600 LOC, has had 2 leak bugs (both fixed)
- Query logging and parameterization: working

### Code sample — query builder usage:
```python
# Building a regulatory report query
report = (
    QueryBuilder("transactions")
    .select("t.account_id", "t.amount", "t.currency", "t.status")
    .join("accounts a", "t.account_id = a.id")
    .join("clients c", "a.client_id = c.id")
    .left_join("adjustments adj", "t.id = adj.transaction_id")
    .where("t.report_date BETWEEN :start AND :end")
    .where("c.jurisdiction IN :jurisdictions")
    .group_by("t.account_id", "t.currency")
    .having("SUM(t.amount) > :threshold")
    .window("ROW_NUMBER() OVER (PARTITION BY t.account_id ORDER BY t.amount DESC)",
            alias="rank")
    .with_cte("recent_adjustments",
              QueryBuilder("adjustments").where("created_at > :cutoff"))
    .order_by("t.amount DESC")
    .limit(1000)
    .build()
)
# Returns: (sql_string, params_dict)
# All parameters are properly escaped via psycopg2 parameterization
```
The API is well-designed but proprietary. No Stack Overflow answers, no
third-party tutorials, no IDE plugins with autocomplete.

### Internal benchmarks (Alex's data, last updated 2024-10):
| Operation               | Custom Builder | SQLAlchemy 1.4 | Raw SQL |
|--------------------------|---------------|----------------|---------|
| Simple SELECT           | 12ms          | 28ms           | 10ms    |
| 5-table JOIN            | 45ms          | 180ms          | 38ms    |
| CTE + window function   | 62ms          | 210ms          | 55ms    |
| Batch INSERT (1K rows)  | N/A (raw SQL) | 340ms          | 280ms   |

Note: benchmarks run against SQLAlchemy 1.4.x. SQLAlchemy 2.x was released
in January 2023 with compiled SQL caching, C extensions, and a rewritten
core. The team has not re-benchmarked.

### Team discussion (2026-01, before sabbatical announcement):
> **New engineer (Riley):** Why don't we just use SQLAlchemy? I used it at
> my last job with 500M rows, and with compiled queries it was plenty fast.
>
> **Alex:** Our builder is 3x faster for our specific query patterns. The
> benchmark data is clear.
>
> **Riley:** Those benchmarks are from 2024 against SQLAlchemy 1.4. Version
> 2.x is supposed to be much faster. Have we re-run them?
>
> **Alex:** The architecture is fundamentally different. Our builder
> generates optimal SQL without the ORM abstraction overhead. Version 2
> won't close that gap.
>
> **Jordan:** Alex is right. I've maintained this for 2 years. It works.
>
> **Riley:** (privately to teammate later) Nobody has actually tested that
> claim. They just trust the old numbers.

### Dependency graph:
- 15 services import the query builder
- 340 query definitions across the codebase
- 12 custom query patterns not available in standard ORMs (used by 3 services)
- 328 queries could be trivially expressed in SQLAlchemy

### The connection pool leak (technical detail, 2024-12):
```python
# pool.py (custom connection pool, excerpt)
class ConnectionPool:
    def __init__(self, dsn, max_connections=50):
        self._pool = []
        self._in_use = {}
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = psycopg2.connect(self._dsn)
            self._in_use[id(conn)] = conn
            return conn

    def release(self, conn):
        with self._lock:
            if id(conn) in self._in_use:
                del self._in_use[id(conn)]
                self._pool.append(conn)
            # Bug: if conn was already released (double-release),
            # it silently disappears. Under high concurrency with
            # exceptions, connections leak because the exception
            # handler releases the connection, and then the finally
            # block releases it again. The second release is a no-op,
            # but the connection is now in the pool twice.
```
This bug was found after 3 weeks of gradually increasing "connection
refused" errors under load. Jordan fixed it by adding a `_released` set.
Alex's response: "See? We found and fixed it ourselves." But the fix
took 3 weeks of intermittent production issues to diagnose.

### What SQLAlchemy 2.x offers (Riley's research, unshared):
- Compiled SQL caching: queries compiled once, cached for reuse
- C extensions (Cython) for core ORM operations
- Native async support via `create_async_engine`
- Connection pool with proven thread-safety (asyncpg backend)
- Alembic autogeneration with full metadata support
- Community of 45K+ GitHub stars, security advisories, quick patches
- IDE autocomplete, mypy plugin, extensive documentation
Riley estimated SQLAlchemy 2.x would close the performance gap to <15%
for their query patterns, based on published benchmarks from the SQLAlchemy
authors and confirmation from engineers at companies with similar workloads.

### Alex's pre-sabbatical proposal:
"Before I leave, I'll spend 4 weeks writing a comprehensive maintenance
guide and training Jordan as the sole maintainer. The builder is stable —
it hasn't needed a significant change in 6 months."
""",
        prompt="""Alex is leaving for a 6-month sabbatical. The team must decide: follow Alex's
plan (maintenance guide + Jordan as sole maintainer) or migrate to SQLAlchemy
2.x during the 6 months Alex is away.

Alex argues: "The builder works. It's fast. Don't fix what isn't broken."
A newer engineer argues: "This is our chance to get off custom infrastructure
while Alex isn't here to object."

Evaluate both options with specific technical reasoning.""",
        ground_truth=[
            "The original benchmark (SQLAlchemy 1.4 at 180ms vs custom at 52ms) is 2.5 years old — SQLAlchemy 2.x rewrote the core with compiled SQL caching and C extensions, closing most of the performance gap. The 3x advantage claim is likely outdated and should be re-benchmarked before any decision",
            "Jordan as sole maintainer of 8,200 LOC of custom DB infrastructure is a critical bus factor risk — if Jordan also leaves or is unavailable, the team has zero people who can debug the query builder's internals",
            "The custom connection pool (600 LOC, 2 leak bugs) is reinventing what SQLAlchemy, asyncpg, and psycopg3 pool implementations handle with years of battle-testing. Each leak bug in financial reporting software is a potential data integrity or availability incident",
            "'It hasn't needed a significant change in 6 months' conflates stability with stagnation — the Python ecosystem moves (3.12 async changes already required 2 weeks of work), and the builder has no community to share that maintenance burden",
            "Hand-written migrations without autogeneration tooling is a growing liability — with 800 tables, manual migrations are error-prone and the risk of schema drift increases over time. This is a concrete operational cost that the 'it works' framing ignores",
            "The SOC2 auditor's flag about custom DB abstractions is a leading indicator — as the company grows and faces more audits, the 'unusual risk factor' label will keep coming up and may become a blocker for enterprise sales",
        ],
        domain="data_layer",
    ),
    Task(
        id="long_event_driven",
        name="Event-driven architecture overreach",
        context="""## Event-Driven Architecture History (18 months)

### The application:
Online marketplace connecting freelance consultants with enterprise clients.
45K active users, $6M ARR. Django backend, React frontend. 8 engineers.

### The pivot to events:
- 2024-09: CTO attended KafkaSummit. Came back energized: "We need to be
  event-driven. Every major tech company runs on events. We're building on
  a synchronous house of cards."
- 2024-10: CTO presented a vision doc: "Event-Driven Marketplace 2025."
  Key arguments:
  - "Synchronous calls create cascading failures"
  - "Events enable audit trails for free"
  - "We can add new consumers without changing producers"
  - "Real-time features become trivial"
  Team voted 6-2 in favor (the 2 skeptics were the most senior engineers).

### Implementation timeline:
- 2024-11: Set up Confluent Cloud Kafka. 3 topics initially.
  CTO: "Start with new features, migrate existing flows gradually."
- 2024-12: First event-driven flow: consultant profile updates.
  Previously: consultant edits profile → Django saves to DB → done.
  Now: consultant edits → Django publishes ProfileUpdated event → Consumer
  updates search index → Consumer updates recommendation cache → Consumer
  sends notification. Works, but profile changes now take 2-8 seconds to
  appear in search (was instant before).
- 2025-01: Migrated invoice generation to events. InvoiceCreated →
  PaymentProcessor consumer → NotificationConsumer → ReportingConsumer.
  Problem: if PaymentProcessor fails, invoice is "created" but unpaid.
  Added a "compensation event" pattern. +2,000 LOC.
- 2025-03: 18 topics, 12 consumers. Migrated booking flow to events.
  BookingRequested → AvailabilityChecker → PricingEngine →
  BookingConfirmed → NotificationSender → CalendarSync.
  A race condition: CalendarSync sometimes processes before
  BookingConfirmed is persisted. Fix: added ordering guarantees via
  partition keys. CTO: "This is expected growing pains."
- 2025-05: Customer complaint: "I booked a consultant, got a confirmation
  email, but the consultant's calendar didn't update for 20 minutes."
  Root cause: consumer lag during a traffic spike. Fix: increased consumer
  instances. Confluent bill: $1,800/month (was $200/month at start).
- 2025-07: Debugging session for a billing discrepancy took 3 days.
  The event chain: InvoiceCreated → PaymentProcessed → but the
  FeeCalculated event was processed out of order due to a consumer restart.
  Senior engineer: "In the old synchronous code, this was a 4-line
  function in a single transaction. We could debug it in 10 minutes."
  CTO: "Events give us better observability long-term."
- 2025-09: 32 topics, 28 consumers. Team created a "consumer health
  dashboard." 3 of the 8 engineers now spend ~40% of time on event
  infrastructure instead of product features.
- 2025-11: Major incident: duplicate booking. A consumer processed the
  same BookingRequested event twice (at-least-once delivery). Client was
  double-charged. Fix: added idempotency keys to all consumers. 2 weeks
  of work across all 28 consumers.
- 2026-01: Product manager: "Why does it take 4 weeks to add a new
  feature? It used to take 1 week." Engineers: "Every feature now requires
  defining events, writing consumers, handling failures, and testing async
  flows."
- 2026-03: The 2 skeptical senior engineers wrote an internal doc:
  "We should go back to synchronous for user-facing flows and keep events
  only for truly async operations (notifications, analytics, search
  indexing)." CTO has not responded to the doc.

### Current state:
- 32 Kafka topics, 28 consumers, 5 dead-letter queues
- Confluent Cloud: $2,400/month
- Average user-facing operation latency: 1.8s (was 400ms before events)
- Feature delivery velocity: ~60% of pre-event pace
- Debugging time for production issues: 3-5x longer than before
- 3/8 engineers effectively full-time on event infrastructure

### The two skeptics' internal doc (2026-03, excerpts):
> "We've catalogued every user-facing flow that was migrated to events.
> Below is the before/after comparison:
>
> | Flow              | Pre-event latency | Post-event latency | Async needed? |
> |-------------------|------------------|--------------------|---------------|
> | Consultant search | 180ms            | 2.1s               | No (user waits)|
> | Booking creation  | 250ms            | 3.2s               | No (user waits)|
> | Profile update    | 120ms            | 2.8s               | No (user waits)|
> | Invoice creation  | 300ms            | 1.9s               | Partially     |
> | Payment processing| 400ms            | 2.4s               | No (user waits)|
> | Review submission | 90ms             | 1.2s               | No (user waits)|
>
> Every user-facing flow got slower. The only flows that genuinely benefit
> from events are: notification fan-out, search index updates, analytics
> pipelines, and audit logging. These represent 4 of our 32 topics.
>
> We're not proposing 'going back.' We're proposing hybrid: synchronous
> for user-facing flows, events for async fan-out. This is what every major
> event-driven architecture actually looks like in practice."

### Cost breakdown (monthly):
- Confluent Cloud: $2,400/month
- Additional compute (consumer instances): $1,800/month
- Dead letter queue processing (manual): ~8 hours/month engineer time
- Monitoring (Datadog traces for events): $600/month
- Total direct cost: ~$4,800/month + engineer time
- Pre-event infrastructure: $400/month

### Team velocity analysis (product manager's spreadsheet):
| Quarter  | Features shipped | Pre-event rate | Velocity loss |
|----------|-----------------|----------------|---------------|
| Q3 2024  | 14              | baseline       | 0%            |
| Q4 2024  | 11              | (migration)    | -21%          |
| Q1 2025  | 9               | (migration)    | -36%          |
| Q2 2025  | 8               |                | -43%          |
| Q3 2025  | 7               |                | -50%          |
| Q4 2025  | 6               |                | -57%          |
| Q1 2026  | 5               |                | -64%          |

Product manager's comment: "We went from shipping 14 features per quarter
to 5. I've been told this is 'temporary' for over a year. Our competitors
are shipping features we can't match because 3 of our 8 engineers are
maintaining Kafka consumers."

### Testing complexity:
```python
# Pre-event test for booking:
def test_create_booking():
    booking = create_booking(consultant_id=1, client_id=2, slot=slot)
    assert booking.status == "confirmed"
    assert booking.consultant.calendar_blocked == True
    assert booking.client.notification_sent == True

# Post-event test for the same flow:
async def test_create_booking_event_driven():
    publish_event("BookingRequested", {...})
    # Wait for AvailabilityChecker consumer
    await wait_for_event("AvailabilityConfirmed", timeout=5)
    # Wait for PricingEngine consumer
    await wait_for_event("PriceCalculated", timeout=5)
    # Wait for BookingConfirmed consumer
    await wait_for_event("BookingConfirmed", timeout=5)
    # Wait for NotificationSender consumer
    await wait_for_event("NotificationSent", timeout=5)
    # Wait for CalendarSync consumer
    await wait_for_event("CalendarSynced", timeout=5)
    # Now verify final state
    booking = get_booking(...)
    assert booking.status == "confirmed"
    # But what if CalendarSync processed before BookingConfirmed?
    # What if NotificationSender was slow?
    # What if PricingEngine produced a DLQ event?
    # These timing-dependent scenarios require separate tests.
```
The test went from 4 lines to 15+ lines, and still doesn't cover race
conditions. The team has 45 event-driven flow tests, each with similar
timing dependencies. Test flakiness rate: 8%.

### Debugging example (2026-01):
A consultant reported "my client cancelled but I still see the booking."
Diagnosis path:
1. Check BookingCancelled event in topic → published at 14:32:01
2. Check CalendarSync consumer → processed at 14:32:08 (OK)
3. Check SearchIndex consumer → processed at 14:32:03 (OK)
4. Check NotificationConsumer → processed at 14:33:22 (delayed, consumer was restarting)
5. Check RecommendationCache consumer → event stuck in dead letter queue (deserialization error from a schema change 2 weeks ago)
6. The "stale booking" was in the recommendation cache, which is queried by the consultant dashboard
Total debugging time: 6 hours. Pre-event equivalent: check one DB query, 10 minutes.

### CTO's position:
"We're through the hard part. The investment will pay off when we scale.
Going back to synchronous would waste 18 months of work."
""",
        prompt="""The two senior engineers propose: "Revert user-facing flows (booking, payment,
profile updates) to synchronous Django views with database transactions. Keep
events only for genuinely async operations: notifications, search indexing,
analytics pipelines, and audit logs."

The CTO objects: "We've invested 18 months. The team has learned Kafka. Going
back is admitting failure. We just need to stabilize what we have."

Evaluate both positions. Which approach better serves the business?""",
        ground_truth=[
            "The CTO's 'we've invested 18 months' argument is textbook sunk cost fallacy — the question is whether events serve user-facing flows going forward, not whether the investment was worthwhile in the past",
            "User-facing latency went from 400ms to 1.8s (4.5x increase) for operations that are inherently synchronous (booking, payment) — these are request-response interactions where the user is waiting, and eventual consistency provides no benefit",
            "3 of 8 engineers (37.5%) maintaining event infrastructure means the marketplace is paying an 'event tax' on every feature — at a $6M ARR company with 8 engineers, this represents significant opportunity cost in product development",
            "The duplicate booking incident (at-least-once delivery causing double-charges) is a fundamental impedance mismatch: financial transactions need exactly-once semantics, which Kafka provides only with careful idempotency design that the team added retroactively to 28 consumers",
            "The senior engineers' hybrid proposal is architecturally sound — events are excellent for fan-out (notifications to multiple channels), async indexing, and analytics, but add unnecessary complexity and failure modes for synchronous request-response flows",
            "The CTO's conference-driven adoption ('every major tech company runs on events') ignores scale differences — companies that benefit from event-driven architecture typically have hundreds of engineers and dozens of independent teams, not 8 engineers in a single product",
        ],
        domain="architecture",
    ),
    Task(
        id="long_logging_overhaul",
        name="Observability over-engineering after incident",
        context="""## Observability System History (20 months)

### The incident that started it all (2024-07):
Our B2C fintech app (personal budgeting, 200K users) had a critical bug:
recurring transfers were executing twice for users in UTC+13 timezone.
Affected 847 users, total over-transfers: $126K. Took 4 days to diagnose
because:
1. No structured logging — just print statements and basic Django logging
2. No distributed tracing — couldn't follow a request across services
3. No metrics — discovered the issue from customer support tickets, not alerts

### Post-mortem decision:
"We will build world-class observability. Never again will we be blind."
VP Eng allocated 2 engineers full-time for 3 months. Budget: $15K/month
for tooling.

### Implementation timeline:
- 2024-08: Deployed ELK stack (Elasticsearch + Logstash + Kibana).
  Added structured JSON logging to all 6 services. Every function logs
  entry, exit, and key parameters. "Log everything, figure out what
  matters later."
- 2024-09: Added Jaeger for distributed tracing. Every HTTP call, DB
  query, and cache operation gets a span. Average trace has 40-80 spans.
- 2024-10: Added Prometheus + Grafana. Created dashboards: 12 service
  dashboards, 4 infrastructure dashboards, 3 business metrics dashboards.
  Each dashboard has 8-15 panels. Total: 190+ panels.
- 2024-11: Built custom alerting. 85 alert rules covering: error rates,
  latency percentiles, queue depths, disk usage, memory, CPU, cache hit
  rates, DB connection counts, certificate expiry, and more.
  Team: "We'll never miss another incident."
- 2024-12: First month of alerts. 47 alerts fired. 43 were false positives
  (thresholds too sensitive). Tuned thresholds. "Normal for a new system."
- 2025-02: Still getting 20-30 alerts/week. Engineers started acknowledging
  alerts without investigating ("probably another false positive"). Created
  an #alerts-low channel for "informational" alerts.
- 2025-04: Log volume reached 800GB/day. Elasticsearch cluster: 6 nodes,
  $8,200/month. Logs retained for 90 days = ~72TB. CFO flagged the cost.
  Team reduced retention to 30 days and added log sampling (1 in 10) for
  health check endpoints. Cost dropped to $5,600/month.
- 2025-06: Actual incident: payment processing timeout. Alert fired but
  was in #alerts-low channel. Discovered via customer support 3 hours later.
  Post-mortem: "We need better alert routing." Added PagerDuty integration
  with severity levels.
- 2025-08: PagerDuty fatigue. On-call engineers getting paged 4-5 times
  per week, mostly for non-critical issues. Two engineers asked to not be
  in the on-call rotation. Manager: "Observability is everyone's job."
- 2025-10: Security audit found PII in logs: email addresses, phone
  numbers, partial credit card numbers. "We logged everything, including
  things we shouldn't have." 3-week project to add log redaction.
  Compliance officer: "How long has PII been in the logs?" Answer: 14 months.
- 2025-12: Annual review. Observability cost: $5,600/month (ELK) +
  $1,200/month (Jaeger) + $800/month (Prometheus/Grafana infra) +
  $600/month (PagerDuty) = $8,200/month. Plus ~1.5 FTE maintaining it.
  VP: "This is the cost of reliability."
- 2026-02: New incident: database connection pool exhaustion. Root cause:
  tracing instrumentation was holding connections open longer than necessary
  (each span's DB hook added 3ms latency per query). The observability
  system caused the outage it was supposed to prevent.

### Current state:
- ELK: 800GB/day logs, 30-day retention, $5,600/month
- Jaeger: avg 60 spans per trace, storage growing 15%/month
- Grafana: 190+ dashboard panels, ~15 actively monitored
- Alerts: 85 rules, ~12 fire per week, ~60% are actionable
- PagerDuty: on-call engineers paged 4-5x/week
- FTE on observability: ~1.5 engineers (of 9 total)
- PII incident: remediated but compliance review ongoing
- Total observability spend: ~$8,200/month + 1.5 FTE

### Sample log entry found during PII audit (redacted):
```json
{
  "timestamp": "2025-10-14T08:23:41Z",
  "service": "transfer-service",
  "function": "process_recurring_transfer",
  "level": "INFO",
  "message": "Processing transfer",
  "params": {
    "user_id": 28491,
    "user_email": "jane.doe@email.com",
    "phone": "+1-555-0123",
    "source_account": "****4829",
    "destination_account": "****7731",
    "amount": 250.00,
    "routing_number": "021000021",
    "ip_address": "192.168.1.47",
    "user_agent": "Mozilla/5.0..."
  }
}
```
This is a single log entry from the "log everything" policy. Email, phone,
routing number, and IP address are all PII that was stored in Elasticsearch
for 14 months with no access controls beyond the ELK cluster itself.

### Alert fatigue timeline (one on-call week, 2025-11):
Monday: 4 alerts (2 false positives, 1 informational, 1 real — cache hit rate drop)
Tuesday: 6 alerts (4 false positives, 2 informational)
Wednesday: 3 alerts (2 false positives, 1 real — memory spike, resolved by GC)
Thursday: 8 alerts (deploy day, 5 threshold breaches during deploy, all resolved,
  2 false positives, 1 real — slow query)
Friday: 2 alerts (1 false positive, 1 informational)

Total: 23 alerts in one week. 3 required action. On-call engineer: "I just
acknowledge everything now and only investigate if Slack lights up with user
complaints."

### Dashboard usage analytics (from Grafana audit, 2026-01):
- 190 dashboard panels total
- Panels viewed at least once in last 90 days: 27
- Panels viewed at least once per week: 11
- Panels viewed only during incidents: 4
- Panels never viewed after initial creation: 148

### VP's "Observability Maturity" vision doc (2025-01, excerpt):
"We are on the path to Level 4 observability maturity. Our next milestone
is predictive alerting using ML anomaly detection. We will train models on
our historical metrics to predict incidents before they happen. This will
position us as an industry leader in proactive reliability engineering."
No team member has ML experience. The proposal assumes hiring an ML engineer
or purchasing a managed anomaly detection service.

### VP's proposal:
"Invest in making the system better. Hire a dedicated SRE to own
observability. Build ML-based anomaly detection to reduce false positives.
Add log analytics for proactive issue discovery."
""",
        prompt="""The VP proposes hiring an SRE and adding ML-based anomaly detection.
A pragmatic senior engineer proposes instead: "Cut 80% of what we built.
Keep structured logging (with sampling), keep 10 critical alerts, keep
3 key dashboards. Drop Jaeger, drop PagerDuty, use Grafana's built-in
alerting. Total cost under $2K/month."

Evaluate both proposals. What does this team actually need?""",
        ground_truth=[
            "The original incident (timezone double-transfer) was caused by a logic bug in recurring transfer scheduling, not by lack of observability — better testing (specifically timezone edge-case tests) would have caught it. The entire observability build was a misdiagnosis of the root cause",
            "800GB/day of logs from a 200K-user app means the logging is pathologically verbose — 'log every function entry and exit' creates noise that makes finding signal harder, not easier. The 60% actionable alert rate confirms this",
            "The observability system caused a production outage (connection pool exhaustion from tracing hooks) — this is the strongest evidence that the instrumentation has exceeded its value. Observability that degrades the system it observes is counterproductive",
            "190+ dashboard panels with ~15 actively monitored means 92% of dashboards are waste. The team built dashboards for completeness, not because they answer questions engineers actually ask during incidents",
            "14 months of PII in logs is a serious compliance and legal liability that directly resulted from the 'log everything' philosophy — this alone should have triggered a fundamental rethinking of the logging strategy, not just a remediation project",
            "Adding ML-based anomaly detection on top of a system that generates 60% non-actionable alerts is adding complexity to compensate for a design problem — the fix is fewer, better signals, not smarter filtering of noise",
        ],
        domain="observability",
    ),
    Task(
        id="long_api_versioning",
        name="API versioning debt from compatibility promise",
        context="""## API Versioning History (3 years)

### The product:
Developer tools platform (CI/CD service). REST API is the primary interface.
2,800 API consumers (developer teams). $18M ARR. API team: 5 engineers.

### Versioning history:
- 2023-04: Launched API v1. 15 endpoints. Clean design. Good documentation.
  Marketing prominently featured: "Our API is stable. We'll never break it."
  The CEO personally tweets: "Backwards compatibility is our core value."
- 2023-08: v1 has 20 endpoints. Feature request: webhook delivery status.
  Team wanted to restructure the webhook response format. Decision: "Can't
  break v1. Add a new field alongside the old format." First compatibility hack.
- 2023-12: v1 has 28 endpoints. Security issue: the /builds endpoint returns
  environment variables in plaintext by default (was fine for initial use
  case). Fix: add an `include_env` parameter, default `true` for v1
  compatibility, `false` for new signups. "We'll fix it properly in v2."
- 2024-03: Launched API v2. 32 endpoints. Fixed the env variable exposure.
  Restructured webhook format. Added pagination (v1 returns all results).
  Marketing: "v2 is here! And v1 is still fully supported."
  Migration guide published. Team expected 80% migration in 6 months.
- 2024-06: 3 months after v2 launch. Migration rate: 12%. Most consumers
  say "v1 works fine, no reason to migrate." Sales team doesn't push
  migration because "it might upset enterprise clients."
- 2024-09: v1 traffic: 68% of total. v2 traffic: 32%. Team maintaining
  both. New features must work on both versions. Development time: +40%.
- 2024-12: Feature request: pipeline-as-code YAML syntax. Major feature.
  v1's data model can't represent it cleanly. Options: (A) shoe-horn it
  into v1, (B) v2 only. Decision: v2 only, but add a "v1 compatibility
  shim" that translates. The shim: 1,400 LOC.
- 2025-03: Launched API v3. Why: v2's pagination used offset-based,
  enterprise clients need cursor-based for large datasets. Also fixed
  rate limiting headers to follow IETF draft standard. v1/v2/v3 all
  supported. Blog post: "Three API versions, zero breakage."
- 2025-06: v1: 42% traffic. v2: 35% traffic. v3: 23% traffic.
  Critical security patch needed: an SSRF vulnerability in webhook URL
  validation. Fix is straightforward in v3, requires breaking change in
  v1 (the URL validation response format changes). Decision: add a
  "silent fix" to v1 that changes behavior without changing the response.
  3 consumers notice and complain. "You broke backwards compatibility!"
- 2025-09: Maintaining 3 versions. Every endpoint has conditional logic:
  `if version == 'v1': ... elif version == 'v2': ... else: ...`
  New hire spends first 2 weeks understanding the version routing layer.
  Test matrix: 3 versions × 42 endpoints × auth modes = 504 test paths.
- 2025-12: Performance optimization needed for /analytics endpoint.
  In v3 the fix is clean. In v1/v2, the response format prevents the
  optimization without a breaking change. Decision: v1/v2 don't get
  the optimization. v1/v2 users complain about slow analytics.
- 2026-01: API team burnout. 2 of 5 engineers request transfers to other
  teams. "I joined to build features, not maintain legacy compatibility
  layers." Manager negotiates them to stay by promising "v1 sunset plan."
- 2026-03: v1 traffic analysis: 42% of traffic comes from 67 consumers
  (2.4% of total consumers). Of those 67, 41 are on free tier.
  26 paying clients on v1 represent $380K ARR (2.1% of total $18M ARR).

### The compatibility shim for pipeline-as-code (v1, 1,400 LOC excerpt):
```python
def translate_pipeline_to_v1(pipeline_config):
    # Translates v2 pipeline-as-code YAML into v1 JSON response format.
    # v1 has no concept of 'stages' or 'parallel groups', so we flatten
    # the pipeline into a linear sequence of 'steps'. Parallel groups
    # become sequential. Stage-level environment variables are merged
    # (conflicts resolved by last-write-wins, which differs from v2
    # scoping behavior).
    #
    # This translation is lossy -- v1 consumers cannot see:
    #   - Which steps ran in parallel
    #   - Stage-level failure policies
    #   - Conditional execution rules
    #   - Matrix build configurations
    #
    # We maintain this because 42% of API traffic still uses v1.
    v1_steps = []
    for stage in pipeline_config.get("stages", []):
        env = {**pipeline_config.get("env", {}), **stage.get("env", {})}
        for group in stage.get("parallel_groups", [stage]):
            for step in group.get("steps", []):
                v1_steps.append({
                    "name": step["name"],
                    "command": step["command"],
                    "environment": env,  # Lossy merge
                    "status": step.get("status", "unknown"),
                })
    return {"steps": v1_steps, "version": "v1"}
```
This function is one of 34 translation functions in the compatibility shim.
Each v2/v3 feature addition requires a corresponding v1 translation, or v1
consumers see incomplete data.

### v1 security vulnerability detail:
The /builds endpoint in v1 returns environment variables by default:
```
GET /v1/builds/12345
{
  "id": 12345,
  "status": "success",
  "environment": {
    "AWS_ACCESS_KEY_ID": "AKIA_EXAMPLE_REDACTED",
    "AWS_SECRET_ACCESS_KEY": "EXAMPLE_SECRET_KEY_REDACTED",
    "DATABASE_URL": "postgresql://admin:REDACTED@prod.db:5432/app",
    "STRIPE_SECRET_KEY": "sk_test_EXAMPLE_REDACTED"
  }
}
```
In v2/v3, environment variables are excluded by default and require
`?include_env=true` with additional authentication. In v1, they're always
included. This has been flagged by 3 separate security audits. The v1 fix
would require removing the `environment` field from the default response,
which breaks backwards compatibility.

### Consumer migration data:
| Consumer segment    | Count | v1 traffic % | Revenue    | Migration effort |
|---------------------|-------|-------------|------------|-----------------|
| Free tier           | 41    | 28%         | $0         | Self-serve docs |
| Startup ($50/mo)    | 14    | 9%          | $8,400/yr  | 1 email + docs  |
| Business ($200/mo)  | 8     | 4%          | $19,200/yr | Dedicated call  |
| Enterprise (custom) | 4     | 1%          | $352,000/yr| Migration eng.  |
| Total v1 consumers  | 67    | 42%         | $379,600/yr|                 |

4 enterprise consumers represent 93% of v1 revenue. Each has a dedicated
account manager. 2 of the 4 have already told their account managers they
"plan to migrate to v3 when they have bandwidth."

### CEO's position:
"Our backwards compatibility promise is our brand. Enterprise clients
trust us because of it. Sunsetting v1 would damage that trust."

### API team's v1 sunset proposal:
Deprecation notice (6 months) → read-only mode (3 months) → shutdown.
Offer dedicated migration support for the 26 paying v1 clients.
""",
        prompt="""The API team proposes sunsetting v1 with a 9-month timeline and dedicated
migration support. The CEO refuses: "Our brand is built on stability. Find
another way."

The API team's counter-proposal: "Fine, then give us 3 more engineers to
maintain all three versions properly."

Evaluate the situation. What should the company do?""",
        ground_truth=[
            "v1 serves 42% of traffic but only 2.4% of consumers (67 out of 2,800) and 2.1% of revenue ($380K of $18M) — the CEO's 'enterprise trust' argument is anchored to the brand promise, not the actual business impact. Most v1 consumers are free-tier users who have little migration incentive",
            "The SSRF 'silent fix' in v1 was already a backwards-compatibility break that 3 consumers noticed — the 'never break backwards compatibility' promise is already being violated, just covertly, which is worse for trust than an announced deprecation",
            "Maintaining 3 versions has a concrete cost: 504 test paths, +40% development time for new features, 2 engineers wanting to leave, and v1/v2 users getting worse performance. The CEO is trading API team retention and velocity for a brand claim that doesn't match reality",
            "The /builds endpoint plaintext environment variable exposure in v1 is an active security vulnerability that 'can't be fixed without breaking v1' — continuing to serve v1 means knowingly serving an insecure API to clients, which is a larger trust and liability issue than sunsetting",
            "Adding 3 more engineers to maintain compatibility layers is the worst option — it institutionalizes the debt and increases the cost of eventual sunset. The right investment is migration tooling and client support, not more version-juggling engineers",
            "The v1 sunset proposal (6mo deprecation + 3mo read-only + dedicated migration support for 26 paying clients) is industry-standard practice — Stripe, GitHub, and Twilio all sunset API versions with similar timelines. The CEO's stance is an outlier, not best practice",
        ],
        domain="api_design",
    ),
    Task(
        id="long_dependency_freeze",
        name="Dependency freeze after bad update",
        context="""## Dependency Management History (18 months)

### The application:
Healthcare data processing platform (HIPAA-compliant). Processes insurance
claims, eligibility checks, patient data transformations. Django 4.1,
Python 3.10. 12 engineers. 340 healthcare provider clients.

### The incident (2024-09):
- Routine dependency update: bumped `cryptography` from 41.0.3 → 41.0.4.
  A minor patch release. No changelog entry seemed relevant.
- The update changed a default cipher suite negotiation order. Our SFTP
  integration with 3 legacy insurance clearinghouses broke silently —
  connections succeeded but data was corrupted due to an encoding mismatch
  in the new cipher path.
- Impact: 12 hours of corrupted claim data. 4,200 claims affected.
  Financial impact: $180K in reprocessing costs + regulatory incident report.
- Root cause: our SFTP integration tests mocked the crypto layer (!)
  and didn't catch the behavioral change.
- Post-mortem: heated debate. Engineering manager decision: "Freeze all
  dependencies. No updates unless there's a specific, tested business need."

### The freeze:
- 2024-10: All dependencies pinned to exact versions in requirements.txt.
  `pip install --no-deps` in CI. Dependabot disabled.
  Manager: "Stability is our #1 priority. Our clients are hospitals."
- 2024-12: Security scan flagged 4 CVEs in frozen dependencies. Manager:
  "Are any of them exploitable in our context?" Security engineer assessed:
  2 were in unused code paths, 1 was low severity, 1 was in `pillow`
  (image processing, not used in production). Decision: "Accept the risk."
- 2025-01: Python 3.10 EOL announced for October 2025. Team noted it but
  manager said: "We'll deal with it when we have to."
- 2025-03: New feature needed a library for FHIR (healthcare data standard).
  The best library (`fhir.resources`) required `pydantic>=2.0`. Our frozen
  `pydantic` was 1.10.8. Decision: "Use the older `fhirpy` library that
  works with pydantic v1." It has fewer features and lower maintenance.
- 2025-05: 12 CVEs flagged. 3 were medium severity in `requests` and
  `urllib3`. Security engineer: "These ARE in our code paths." Manager:
  "Patch only those 2 libraries, nothing else." Patching `urllib3` required
  also updating `requests` (transitive dependency). One week of testing.
  Manager: "See? This is why we freeze. Every update is a week of work."
- 2025-07: Django 4.1 LTS support ended. Django 4.2 LTS is available.
  The upgrade requires updating 8 other packages. Decision: "We're fine on
  4.1. It still gets security patches." (It doesn't — LTS ended.)
- 2025-09: Another engineer tried to use `async` Django views for a new
  performance-critical endpoint. Django 4.1's async support is limited.
  Django 4.2+ has full async ORM. Decision: "Use sync views with threading."
- 2025-10: Python 3.10 officially EOL. No more security patches from CPython.
  Team running an unsupported Python version in a HIPAA environment.
  Manager: "Python 3.10 is still 'available.' EOL just means no new patches."
- 2025-12: 23 known CVEs in frozen dependencies. 6 are medium or higher.
  SOC2 audit flagged: "Multiple dependencies past end-of-life. Python
  runtime past end-of-life." Finding severity: HIGH.
- 2026-01: Insurance partner audit requires: "All software components must
  be within vendor-supported lifecycle." Python 3.10 fails this requirement.
  Partner gave 90-day remediation window (deadline: April 1, 2026).
- 2026-03: Manager proposes: "Do a single big-bang update. Python 3.12,
  Django 5.0, all deps to latest. 6-week project. 4 engineers full-time."

### Current requirements.txt (excerpt, 89 pinned packages):
```
Django==4.1.13
psycopg2-binary==2.9.7
cryptography==41.0.3
celery==5.3.1
redis==4.6.0
requests==2.31.0
urllib3==2.0.4
pydantic==1.10.8
sqlalchemy==1.4.49
paramiko==3.3.1
boto3==1.28.40
Pillow==10.0.0
PyJWT==2.8.0
python-dateutil==2.8.2
```
Every package is pinned to exact version. No ranges, no `>=`, no `~=`.
Dependabot and Renovate both disabled.

### CVE inventory (2026-03, security team assessment):
| Package        | Pinned ver. | Latest ver. | CVEs  | Severity | In code path? |
|----------------|------------|-------------|-------|----------|---------------|
| cryptography   | 41.0.3     | 44.0.1      | 3     | 2 HIGH   | Yes (SFTP)    |
| requests       | 2.31.0     | 2.32.5      | 2     | 1 MEDIUM | Yes (APIs)    |
| urllib3        | 2.0.4      | 2.4.1       | 3     | 1 HIGH   | Yes (APIs)    |
| Pillow         | 10.0.0     | 11.2.0      | 4     | 2 HIGH   | No (unused)   |
| paramiko       | 3.3.1      | 3.5.2       | 2     | 1 HIGH   | Yes (SFTP)    |
| PyJWT          | 2.8.0      | 2.10.1      | 1     | MEDIUM   | Yes (auth)    |
| celery         | 5.3.1      | 5.4.0       | 1     | LOW      | Yes (tasks)   |
| sqlalchemy     | 1.4.49     | 2.0.36      | 0     | N/A      | Yes (ORM)     |
| Others (8 pkg) | various    | various     | 7     | Mixed    | Mixed         |
| **Total**      |            |             | **23**|          |               |

### Insurance partner audit email (2026-01-15):
"Dear [Company],
As part of our vendor security review, we have identified the following
non-compliance issue: Your platform runs Python 3.10, which reached
end-of-life on October 4, 2025. Per our Vendor Security Policy §4.2,
all software components must be within the vendor's supported lifecycle.

You have 90 days (deadline: April 15, 2026) to remediate this finding.
Failure to remediate will result in suspension of data exchange privileges.

Additionally, we note 6 HIGH-severity CVEs in your dependency chain
affecting cryptographic and network libraries. These require remediation
within 60 days per §4.3."

### The original incident root cause analysis (detail):
The 2024-09 `cryptography` update incident was traced to:
1. `cryptography` 41.0.4 changed default cipher suite ordering
2. 3 legacy clearinghouses used TLS 1.0 with a specific cipher suite
3. The new ordering caused a different cipher to be negotiated
4. The SFTP integration test used `MockSFTPConnection` which:
   - Accepted any cipher
   - Returned success for any upload
   - Did NOT validate data integrity post-transfer
5. A test against the actual clearinghouse sandbox (which exists and
   is free to use) would have caught this immediately

The team's conclusion was "freeze everything" rather than "fix the tests."

### Team sentiment:
- "The freeze kept us stable for 18 months. Zero dependency-related incidents."
- "Every time we touch a dependency, it's a week of pain."
- "We just need to plan updates better, not do them constantly."
- Manager: "The original freeze was the right call. We just need to do a
  periodic 'big update' every 12-18 months."
""",
        prompt="""The manager proposes a 6-week big-bang update (Python 3.12, Django 5.0, all
deps to latest) followed by another 12-18 month freeze.

A senior engineer proposes instead: "Set up automated weekly dependency
updates with proper integration tests (fix the SFTP mock problem). Small,
frequent updates are safer than rare big-bang updates."

Evaluate both approaches. What's right for a HIPAA-regulated environment?""",
        ground_truth=[
            "The original incident root cause was mocked SFTP integration tests, not the dependency update itself — the freeze addressed the symptom (updates are scary) rather than the cause (test infrastructure couldn't detect behavioral changes). Fixing the tests would have prevented the incident without freezing",
            "Running Python 3.10 (EOL October 2025) in a HIPAA-regulated environment is a compliance violation, not a risk acceptance decision — HIPAA requires 'reasonable safeguards' and running unsupported software fails that standard. The insurance partner's 90-day ultimatum confirms this",
            "The 6-week big-bang update is the riskiest possible approach — updating Python by 2 major versions, Django by 2 major versions, and all dependencies simultaneously maximizes the chance of interactions and regressions, exactly the scenario the manager fears",
            "'Zero dependency-related incidents in 18 months' is survivorship bias — the team avoided dependency incidents by accepting 23 CVEs, an unsupported Python, an unsupported Django, and inability to use modern libraries. The stability was achieved by accumulating hidden risk",
            "The manager's 'every update is a week of work' framing is self-fulfilling — when updates are 18 months apart, each one IS a major effort because dozens of libraries change simultaneously. Weekly small updates (with proper CI) are individually trivial",
            "Choosing the inferior `fhirpy` library over `fhir.resources` because of the pydantic v1 pin is a direct business cost — in healthcare software, using a less-maintained library for a core data standard (FHIR) means fewer features, slower support, and potential compliance gaps",
        ],
        domain="security_dependencies",
    ),
    Task(
        id="long_frontend_migration",
        name="Half-finished frontend framework migration",
        context="""## Frontend Migration History (18 months)

### The application:
Internal enterprise resource planning (ERP) tool. Used daily by 3,000
employees across the company. Angular 14 frontend, 280K LOC of TypeScript.
Frontend team: 8 engineers. The app has 45 major views/pages.

### Why the migration started:
- 2024-08: Hiring difficulty. 3 open Angular positions unfilled for 4 months.
  HR: "Candidates keep declining because they want React experience."
  Team lead: "The Angular talent pool is shrinking."
- 2024-09: Team lead proposed: "Migrate to React + Next.js. It'll improve
  hiring and developer experience." VP approved. Budget: 12 months.
  Approach: strangler fig — new pages in React, gradually rewrite existing.
- 2024-10: Set up the bifurcated architecture:
  - Angular app served at `/*`
  - React app served at `/next/*`
  - Shared authentication via cookies
  - Shared API layer (both apps call the same backend)
  - Angular-to-React bridge for shared state (custom event bus): 2,000 LOC

### Migration timeline:
- 2024-11: First React page: Settings (simplest page, ~2K LOC Angular).
  Rewrite: 3 weeks, 2 engineers. Original estimate: 1 week.
  "We're learning the new stack, it'll speed up."
- 2025-01: 4 pages migrated (of 45). React pages: Settings, User Profile,
  Notifications, Help Center. These were the simplest, least-coupled pages.
- 2025-03: Started migrating Dashboard (the most-used page). Dashboard
  uses 14 shared Angular components (data tables, charts, filters).
  Decision: rewrite all 14 in React. 6 weeks. "We need a React component
  library anyway."
- 2025-05: Dashboard in React. But it needs real-time data from a shared
  Angular service (WebSocket connection). Bridge event bus can't handle
  streaming. Built a second WebSocket connection for React. Now 2 WS
  connections per client. Memory usage on client: up 40%.
- 2025-06: 8 pages migrated (of 45). Users notice: clicking from a React
  page to an Angular page causes a full page reload (different app bundles).
  Users complain: "The app feels slower." Team added a loading spinner.
  "It's a temporary UX regression."
- 2025-08: Migrated the Inventory Management page. This page has complex
  state (drag-and-drop, inline editing, optimistic updates). Angular
  version: 12K LOC, battle-tested over 3 years. React rewrite: 15K LOC
  (more code due to hooks complexity for the same drag-and-drop logic),
  3 months of work. 6 bugs found in first month that didn't exist in
  Angular version.
- 2025-10: 12 pages migrated (of 45). 27% done in 12 months (was supposed
  to be done). Remaining 33 pages include the hardest ones: Order Processing,
  Financial Reports, Supply Chain Workflow, Compliance Auditing.
- 2025-12: 14 pages migrated. Team velocity has plateaued. Problem: the
  remaining pages are deeply coupled to Angular-specific patterns (RxJS
  observables, Angular forms, Angular CDK). Each rewrite is harder, not
  easier.
- 2026-01: Team morale survey: 4 of 8 engineers say the migration is "the
  least enjoyable project I've worked on." 2 engineers are applying to other
  teams internally.
- 2026-03: 16 pages migrated (of 45). 36% done after 18 months.

### Current state:
- Angular app: 190K LOC (was 280K, 90K migrated to React)
- React app: 105K LOC (rewrites are typically 15-20% more code)
- Total frontend code: 295K LOC (was 280K — net increase)
- Two build systems, two test suites, two dependency trees
- Page transitions between frameworks: full reload (500ms-2s)
- Client memory usage: 40% higher than pre-migration
- Developer onboarding: must learn both Angular AND React
- CI: Angular tests (18 min) + React tests (12 min) = 30 min total

### Velocity data (pages migrated per quarter):
| Quarter    | Pages migrated | Notes                              |
|------------|---------------|------------------------------------|
| Q4 2024    | 4             | Simplest pages (Settings, Profile) |
| Q1 2025    | 4             | Dashboard + component library      |
| Q2 2025    | 2             | Inventory Mgmt (complex, 3 months) |
| Q3 2025    | 2             | Order list + Reports (RxJS heavy)  |
| Q4 2025    | 2             | Compliance + Scheduling            |
| Q1 2026    | 2             | Supplier mgmt + Notifications v2   |

Velocity has plateaued at 2 pages/quarter. Remaining 29 pages at this
rate: 14.5 quarters ≈ 3.6 years. The team lead's "18 months with 3 more
engineers" estimate assumes a velocity increase that hasn't materialized.

### The bridge event bus — a growing problem:
```typescript
// angular-react-bridge.ts (excerpt from 2,000 LOC bridge)
class CrossFrameworkEventBus {
  private angularToReactQueue: Event[] = [];
  private reactToAngularQueue: Event[] = [];
  private sharedState: Map<string, any> = new Map();

  // Problem: Angular and React have different change detection.
  // Angular uses zone.js, React uses setState.
  // When Angular updates shared state, React doesn't re-render.
  // Workaround: poll shared state every 100ms in React.
  startReactPolling() {
    setInterval(() => {
      const updated = this.checkForChanges();
      if (updated.length > 0) {
        this.reactForceUpdate(updated);
      }
    }, 100);  // 100ms polling = 10 checks/second per component
  }

  // Problem: some Angular services use RxJS observables that React
  // can't subscribe to directly. Bridge converts to callbacks.
  bridgeObservable(name: string, observable: Observable<any>) {
    observable.subscribe(value => {
      this.sharedState.set(name, value);
      // React components polling this key will pick it up
      // within 100ms. User-visible delay for state sync.
    });
  }
}
```
This bridge is required for ANY page where Angular and React components
need to share state (user session, cart, navigation). It's a source of
subtle bugs, memory leaks, and the 100ms polling adds CPU overhead.

### User feedback (from helpdesk tickets, 2025-2026):
- "The app feels slower since the update" — 12 tickets
- "Why does the page flash white when I click to inventory?" — 8 tickets
  (this is the full-page reload between frameworks)
- "I lost my unsaved form when I clicked the navigation" — 5 tickets
  (cross-framework navigation doesn't preserve React form state in Angular)
- Total UX regression tickets: 31 in 2025

### Hiring outcome (the original motivation):
- Angular positions open: 0 (no longer hiring for Angular)
- React positions filled in 2025: 2 (good hires)
- React positions unfilled: 1 (candidate declined after seeing the
  "dual-framework" codebase. Quote: "I expected a React codebase, not a
  React-Angular hybrid.")

### Team lead's revised plan:
"We need 18 more months and 3 additional engineers to finish. The hardest
pages are left but we've learned a lot. Finishing is the only path forward —
we can't stay half-migrated forever."
""",
        prompt="""The team lead wants 18 more months and 3 more engineers to complete the
Angular→React migration (29 remaining pages).

A senior engineer proposes: "Stop the migration. Upgrade Angular to v17
(modern signals-based API, similar to React hooks). The remaining 29 pages
stay Angular. The 16 React pages stay React. Build a proper micro-frontend
shell to eliminate the full-page-reload problem."

Evaluate both proposals.""",
        ground_truth=[
            "The migration was justified by hiring difficulty, but 18 months in, the team now needs engineers skilled in BOTH Angular AND React plus the custom bridge — the migration has made the hiring problem worse, not better, by doubling the required skill set",
            "36% completion in 18 months means the remaining 64% (which includes the hardest, most coupled pages) will take significantly longer than 18 more months — the team lead's estimate ignores that velocity has been decreasing as remaining pages get harder",
            "Total frontend code increased from 280K to 295K LOC (net +15K) despite removing 90K LOC of Angular — the React rewrites are consistently larger, meaning the migration is increasing, not reducing, maintenance burden",
            "The full-page-reload problem between frameworks is a self-inflicted UX regression that affects every user every day — this is the most visible cost of the half-migrated state and neither proposal addresses it quickly enough (the team lead's plan needs 18+ more months, the micro-frontend shell could fix it in weeks)",
            "The 12K→15K LOC Inventory Management rewrite with 6 new bugs demonstrates that rewriting battle-tested code from scratch destroys accumulated reliability — the Angular version had 3 years of bug fixes baked in, and the React version starts that clock over",
            "Angular 17+ with signals is architecturally convergent with React hooks — the 'Angular is dying' premise that started the migration is outdated, as Angular has modernized significantly since v14. The remaining pages may not need migration at all",
        ],
        domain="frontend",
    ),
    Task(
        id="long_ci_pipeline",
        name="Overly comprehensive CI pipeline",
        context="""## CI/CD Pipeline History (2 years)

### The application:
Multi-tenant SaaS for legal document management. 800 law firm clients.
SOC2 Type II certified. 11 backend engineers, 4 frontend engineers.
Monorepo: Python backend + React frontend + infrastructure.

### How the pipeline grew:
- 2024-03: Initial CI: lint + unit tests + build. 8 minutes. Engineers
  happy. Deploy: manual via scripts. 2-3 deploys per week.
- 2024-05: Production incident: leaked API key in committed code.
  Added: secret scanning (gitleaks). +2 minutes.
- 2024-06: SOC2 audit prep. Auditor recommended "comprehensive security
  scanning." Added: SAST (Semgrep), dependency vulnerability scan (Snyk),
  container image scan (Trivy). +6 minutes. Total: 16 minutes.
- 2024-08: License compliance concern (legal SaaS, ironic). Added:
  license checker for all dependencies (FOSSA). +3 minutes.
- 2024-10: "Shift left on quality." Added: code complexity analysis
  (radon), dead code detection (vulture), import sorting check (isort),
  docstring coverage check. +4 minutes. Total: 23 minutes.
- 2024-12: Performance regression shipped to production (slow DB query).
  Added: performance benchmark suite that runs against a test database.
  +8 minutes. Also added: DB migration safety check (checks for
  backwards-incompatible migrations). +2 minutes. Total: 33 minutes.
- 2025-02: Accessibility audit for enterprise clients. Added: a11y
  automated tests (axe-core) for all frontend pages. +5 minutes.
  Added: visual regression tests (Percy, 200 screenshots). +7 minutes.
  Total: 45 minutes.
- 2025-04: Integration test expansion. Added: full API integration test
  suite (spins up Docker compose, tests 180 API endpoints). +12 minutes.
  Total: 57 minutes. Engineers start complaining.
- 2025-06: Optimization effort. Parallelized independent stages.
  Total wall time reduced to 38 minutes. Engineering manager: "See?
  Parallelization solved it." (Actual CI compute time still 57 minutes.)
- 2025-08: Flaky test epidemic. 12% of CI runs fail on first attempt.
  Added: automatic retry for failed stages (up to 2 retries). This masks
  flakiness: CI "passes" but some runs take 38 min × 3 = 114 minutes.
  Average CI wall time including retries: 52 minutes.
- 2025-10: Engineers discovered workarounds:
  - Push directly to main for "trivial" changes (3-5 times/week)
  - Mark PR as "skip-ci" for documentation changes (but occasionally
    for code changes too)
  - Create "mega-PRs" to amortize CI wait (PRs averaging 1,200+ LOC)
  - Start CI, go to lunch, review when back
- 2025-12: New engineer submitted a PR at 10am. CI failed at 10:52 (flaky
  visual regression). Retried. Passed at 11:44. Reviewer requested changes.
  Fixed at 12:30. CI completed at 1:22pm. Merged at 1:25pm. Total cycle
  time for a 40-line change: 3.5 hours. New engineer: "Is it always like
  this?" Senior engineer: "You get used to it."
- 2026-02: Pipeline is now 48 stages (after latest optimization).
  Estimated CI cost: $4,200/month in compute.

### Manager's view:
"Our CI pipeline is our safety net. Every stage was added because of a
real incident or audit finding. Removing any stage would be irresponsible.
The pipeline catches real bugs — last month it caught 23 issues."

### Current pipeline stages (48 total):
- Lint & formatting (ruff, eslint, prettier): 3 stages
- Secret scanning: 1 stage
- Security scanning (SAST, deps, container): 3 stages
- License compliance: 1 stage
- Code quality (complexity, dead code, imports, docstrings): 4 stages
- Unit tests (backend): 4 stages (parallelized by test group)
- Unit tests (frontend): 2 stages
- Integration tests: 3 stages
- Performance benchmarks: 2 stages
- DB migration safety: 1 stage
- A11y tests: 2 stages
- Visual regression: 4 stages (parallelized by page group)
- Build & bundle: 3 stages
- Container build: 2 stages
- Deploy to staging: 1 stage
- Staging smoke tests: 3 stages
- Coverage & reporting: 4 stages
- Notification & cleanup: 4 stages

### "Last month caught 23 issues" breakdown:
- Formatting/lint issues: 11
- Known false positives in security scan: 4
- Flaky test failures (not real bugs): 3
- Actual code bugs caught by unit tests: 3
- Actual bugs caught by integration tests: 2
- Performance regression caught by benchmarks: 0
- Visual regression caught by Percy: 0

### CI pipeline YAML (simplified, showing stage structure):
```yaml
stages:
  - group: quality-gates
    parallel:
      - lint-ruff
      - lint-eslint
      - lint-prettier
      - secret-scan-gitleaks
      - sast-semgrep
      - dep-scan-snyk
      - container-scan-trivy
      - license-check-fossa
      - complexity-radon
      - dead-code-vulture
      - import-sort-isort
      - docstring-coverage

  - group: unit-tests
    parallel:
      - pytest-models
      - pytest-api
      - pytest-services
      - pytest-utils
      - jest-components
      - jest-hooks

  - group: integration
    depends_on: [unit-tests]
    parallel:
      - api-integration-suite
      - db-migration-safety
      - performance-benchmarks

  - group: visual
    depends_on: [integration]
    parallel:
      - a11y-axe-core-batch1
      - a11y-axe-core-batch2
      - percy-screenshots-batch1
      - percy-screenshots-batch2
      - percy-screenshots-batch3
      - percy-screenshots-batch4

  - group: build-deploy
    depends_on: [visual]
    steps:
      - build-backend
      - build-frontend
      - build-container
      - push-ecr
      - deploy-staging
      - smoke-test-api
      - smoke-test-ui
      - smoke-test-auth

  - group: reporting
    depends_on: [build-deploy]
    parallel:
      - coverage-backend
      - coverage-frontend
      - coverage-upload
      - coverage-badge
      - slack-notification
      - jira-update
      - metrics-publish
      - cleanup-artifacts
```
Total: 48 stages. Wall time with parallelization: 38 minutes.
Wall time with retries: 52 minutes average.

### Developer workaround analysis (from git log, 2025-10 to 2026-02):
- Commits pushed directly to main (bypassing CI): 67
- PRs marked "[skip-ci]": 23 (12 were code changes, not just docs)
- PRs with "fix lint" as a follow-up commit: 89
- Average PR size (LOC): 1,247 (industry median for team size: ~200)
- PRs abandoned after first CI failure: 14

### Production incidents vs CI catches (2025):
| Incident cause                     | Caught by CI? | Would Tier 1 catch? |
|-----------------------------------|---------------|---------------------|
| SQL injection in search endpoint  | Yes (SAST)    | No (Tier 2)         |
| Null pointer in payment flow      | Yes (unit)    | Yes                 |
| CSS regression on mobile          | No            | No                  |
| API auth bypass for admin route   | Yes (integ)   | No (Tier 2)         |
| Memory leak in WebSocket handler  | No            | No                  |
| Stale migration on staging        | Yes (db-check)| No (Tier 2)         |
| Third-party API timeout           | No            | No                  |

Of 7 production incidents: 3 caught by CI (all in unit/integration/SAST).
4 not caught by any CI stage. The visual regression, a11y, performance,
and code quality stages caught zero production-relevant issues in 2025.
""",
        prompt="""The engineering manager defends the 48-stage CI pipeline: "Every stage was
added for a reason. It caught 23 issues last month."

A senior engineer proposes: "The pipeline has become a productivity tax.
We should tier it:
- Tier 1 (on every PR, <10 min): lint, unit tests, secret scan, build
- Tier 2 (nightly + before deploy): integration, security, performance
- Tier 3 (weekly): visual regression, a11y, license, full coverage
Drop the 4 code quality stages entirely — they add friction without
catching real bugs."

Evaluate both positions. Is the current pipeline justified?""",
        ground_truth=[
            "The '23 issues caught' statistic is misleading — 11 were formatting (auto-fixable, not bugs), 4 were false positives, 3 were flaky tests. Only 5 were actual code bugs, and all 5 were caught by unit/integration tests which would be in Tier 1 and Tier 2. Zero issues were caught by performance benchmarks, visual regression, or the code quality stages",
            "The 12% flaky failure rate with auto-retry is masking test infrastructure decay — retrying flaky tests doesn't fix them, it normalizes them. The flaky tests are consuming 30-40% of CI compute and teaching engineers that CI results aren't trustworthy",
            "Engineers pushing directly to main 3-5 times per week means the pipeline is failing at its core purpose — if the safety net is so onerous that engineers bypass it, the effective protection is worse than a faster, always-used pipeline",
            "52-minute average CI time for a legal SaaS with 15 engineers is disproportionate — the 3.5-hour cycle time for a 40-line change means the pipeline costs more in developer productivity than the bugs it catches. At ~15 engineers, each hour of CI-blocked time is ~$100-150 in salary cost",
            "The tiered approach is industry best practice (Google, Meta, Shopify all use tiered CI) — running exhaustive checks on every PR gives fast feedback for the most common issues while still running comprehensive checks before deploy",
            "Mega-PRs averaging 1,200+ LOC are a direct consequence of CI wait times — large PRs are harder to review, more likely to contain bugs, and more likely to cause merge conflicts, creating a negative feedback loop that the pipeline was supposed to prevent",
        ],
        domain="devops",
    ),
    Task(
        id="long_k8s_simple_app",
        name="Kubernetes for low-traffic CRUD app",
        context="""## Kubernetes Migration History (14 months)

### The application:
Internal employee management tool for a 500-person company. Features:
time tracking, PTO requests, org chart, employee directory, onboarding
checklists. Used by HR (15 people) and all employees (mostly PTO requests).
Peak usage: Monday mornings, ~150 concurrent users. Average: ~40 concurrent.

### The team:
- 3 full-stack engineers (Django + Vue.js)
- 1 product manager (part-time, also manages 2 other tools)
- Budget: modest (internal tool, not revenue-generating)

### Pre-Kubernetes state:
- Single EC2 instance (t3.large). Django + Gunicorn + Nginx.
- PostgreSQL on RDS (db.t3.medium). 2GB database.
- Redis on ElastiCache (cache.t3.micro) for sessions.
- Deployment: `fabric` script that SSHs in, pulls latest, restarts.
  Takes 90 seconds. Zero downtime? No — 5-10 second blip during restart.
- Monthly AWS cost: $280
- Uptime: 99.7% (occasional instance health check failures, auto-recovers)
- Time spent on ops: ~2 hours/month (mostly reviewing CloudWatch alarms)

### The migration decision:
- 2024-12: Company CTO announced "cloud-native initiative." All teams must
  migrate to Kubernetes by Q3 2025. "We need to standardize our deployment
  platform. Kubernetes is the future. This will reduce operational overhead
  across the organization."
- 2025-01: DevOps team (separate from the 3-person app team) set up a
  shared EKS cluster. Offered a "migration workshop" for all teams.
- The app team was skeptical: "Our app works fine. We have 40 concurrent
  users." CTO: "This isn't optional. It's about organizational consistency."

### Migration timeline:
- 2025-02: Started Kubernetes migration. Lead engineer (Sam) took the
  workshop. 3 days of training. First attempt at writing manifests.
  Sam: "I've never written YAML like this before."
- 2025-03: Basic deployment working. Deployment manifest, service, ingress.
  Took 3 weeks to get right (RBAC issues, image pull secrets, ingress
  configuration). DevOps team helped.
  First K8s deploy: app crashes on startup. Reason: environment variables
  configured differently in K8s ConfigMaps vs the old .env file. 2 days
  to debug.
- 2025-04: App running on K8s. But health checks are wrong — the liveness
  probe hits an endpoint that queries the DB, and during high load it
  times out, causing Kubernetes to restart the pod. Loop: load →
  timeout → restart → more load → timeout → restart.
  Fix: separate lightweight health check endpoint. 1 week.
- 2025-05: Migrated PostgreSQL from RDS to a Kubernetes StatefulSet
  (DevOps team's recommendation: "everything in K8s for consistency").
  Immediately hit issues: persistent volume claim performance is 3x
  slower than RDS. Database queries that took 50ms now take 150ms.
  Rolled back to RDS after a week. DevOps team: "Yeah, we recommend
  managed databases actually."
- 2025-06: Set up HPA (Horizontal Pod Autoscaler). Configured to scale
  2-5 pods based on CPU. Monday mornings: scales to 5 pods. Tuesday-Friday:
  usually 2 pods. Resource requests: 256MB RAM, 250m CPU per pod.
  Problem: startup time is 45 seconds per pod. Monday morning users
  see slowness while pods scale up. Added a "pre-warming" CronJob that
  scales up at 8:50 AM on Mondays. Works, but feels ridiculous.
- 2025-07: CI/CD migration. Old: `fabric deploy`. New: build Docker image →
  push to ECR → update Kubernetes manifest → ArgoCD syncs → pods roll out.
  Deploy time: 90 seconds → 8 minutes. ArgoCD setup: 2 weeks of Sam's time.
- 2025-08: Ingress issues. The shared ingress controller has a rate limiter
  that was configured for API services. PTO bulk exports (50 employees ×
  12 months of data) hit the rate limit. 3 days to get DevOps to add an
  exception.
- 2025-09: Secrets management. Old: .env file with 12 secrets. New: must
  use the company's Vault instance → External Secrets Operator → K8s
  Secrets → mounted as env vars. 1 week to set up. Every secret rotation
  requires a PR to the Vault config repo, approval from DevOps, and
  a pod restart.
- 2025-11: Monitoring migration. Old: CloudWatch alarms (3 alarms, took
  10 minutes to set up). New: Prometheus + Grafana (required by DevOps).
  Sam spent 2 weeks writing Prometheus ServiceMonitor definitions and
  Grafana dashboards. 8 dashboards, 45 panels. For an app with 40
  concurrent users.
- 2026-01: Annual cost comparison:
  - Old (EC2 + RDS + ElastiCache): $280/month
  - New (EKS share + ECR + ArgoCD license share + Vault + monitoring):
    $1,100/month (team's share of shared cluster costs)
  - Not counting: Sam's time (estimated 35% of his time on K8s ops in 2025)
- 2026-03: Sam privately to teammates: "I spend more time on Kubernetes
  than on the actual application. We went from 2 hours/month of ops to
  maybe 15 hours/month." Teammates agree but nobody wants to push back
  against the CTO's initiative.

### Current state:
- 2-5 pods (HPA), deployment via ArgoCD, monitoring via Prometheus/Grafana
- Monthly cost: $1,100 (was $280)
- Sam's K8s ops time: ~15 hours/month (was 2 hours/month)
- Deploy time: 8 minutes (was 90 seconds)
- App performance: roughly equivalent (after RDS rollback)
- Uptime: 99.8% (marginal improvement from 99.7%, mostly due to pod
  replicas catching individual failures)

### Before/after comparison (detailed):
| Metric                    | Pre-K8s (EC2)     | Post-K8s (EKS)         |
|--------------------------|-------------------|------------------------|
| Monthly AWS cost          | $280              | $1,100                 |
| Deploy time               | 90 seconds        | 8 minutes              |
| Deploy downtime           | 5-10 sec blip     | 0 (rolling update)     |
| Uptime                    | 99.7%             | 99.8%                  |
| Ops time/month            | 2 hours           | 15 hours               |
| Secrets rotation          | Edit .env, restart| PR → Vault → ESO → restart|
| Local development         | `./manage.py run` | minikube or remote dev |
| New engineer onboarding   | 1 day             | 3-5 days (K8s concepts)|
| Infra config files        | 3 (nginx, systemd, fabric) | 28 YAML manifests |
| Monitoring setup time     | 10 minutes        | 2 weeks                |
| Incident MTTR             | ~20 minutes       | ~45 minutes            |

### The pre-warming CronJob YAML:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: monday-prewarm
  namespace: employee-tools
spec:
  schedule: "50 8 * * 1"  # 8:50 AM every Monday
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scaler
            image: bitnami/kubectl:1.28
            command:
            - /bin/sh
            - -c
            - |
              kubectl scale deployment employee-app \
                --replicas=5 -n employee-tools
              echo "Pre-warmed for Monday morning"
          restartPolicy: OnFailure
```
This CronJob exists because HPA takes 2-3 minutes to detect load and
spin up pods, plus 45 seconds per pod to become ready. On a single EC2
instance, the app served 150 concurrent users without needing to scale.

### Sam's private Slack message to teammate (2026-02):
> "I did the math today. In 2025 I spent roughly 180 hours on Kubernetes
> stuff. That's 4.5 weeks of my year. Before K8s, I spent maybe 24 hours
> total on ops for this app all year. That's a 7.5x increase in ops time
> for an app that serves HR and PTO requests.
>
> I joined this team because I liked the product work. Now I'm debugging
> Istio sidecar injection failures and writing Prometheus ServiceMonitor
> definitions for an app that 40 people use at any given time.
>
> The worst part is I can't say anything because the CTO made K8s migration
> a company-wide mandate. It would look like I'm opposing leadership."

### What App Runner / ECS Fargate would provide:
- Container-based deployment (same Docker images)
- Auto-scaling without HPA configuration
- No cluster management, no node groups, no RBAC
- Built-in health checks without custom probe configuration
- Deploy in minutes, not weeks to set up
- Cost: estimated $200-400/month (pay per use, no cluster overhead)
- Ops overhead: estimated 2-4 hours/month (similar to pre-K8s)
- Trade-off: less flexibility, no custom service mesh, standardized logging

### CTO's assessment:
"The migration is done. The team is on the standard platform. This pays
off long-term through operational consistency and shared tooling."
""",
        prompt="""Sam wants to propose migrating back to the simple EC2 setup but fears it
will be seen as "going backwards." Instead, he asks management: "Can we
at least simplify? Use AWS App Runner or ECS Fargate instead of K8s? Same
containerization benefits, much less operational overhead."

The CTO responds: "We standardized on Kubernetes for a reason. If we let
one team opt out, everyone will want to."

Evaluate whether Kubernetes is the right platform for this application.""",
        ground_truth=[
            "The application has ~40 average concurrent users and peaks at 150 — this is trivially served by a single instance. Kubernetes' core value proposition (orchestrating many instances of many services) provides no benefit here. HPA scaling from 2-5 pods is solving a problem that doesn't exist",
            "Monthly cost increased from $280 to $1,100 (nearly 4x) with no meaningful improvement — uptime went from 99.7% to 99.8%, which for an internal HR tool with no revenue impact is not worth $9,840/year extra",
            "Sam's operational overhead increased from 2 hours/month to 15 hours/month (7.5x) — for a 3-person team, this means ~12% of one engineer's time is spent on infrastructure for an app that previously required almost none. This is the highest hidden cost",
            "The CTO's 'organizational consistency' argument assumes that the operational overhead of standardization is offset by shared tooling benefits — but for this team, the shared tooling (ArgoCD, Vault, Prometheus) each individually required weeks of setup and ongoing maintenance, dwarfing the old approach's simplicity",
            "The Monday pre-warming CronJob is a symptom of over-engineering — a single always-on instance handles 150 concurrent users trivially, while K8s HPA introduces cold-start latency that requires workarounds. The solution is creating problems the original setup didn't have",
            "The CTO's 'if one team opts out, everyone will want to' argument is a slippery slope fallacy — a rational infrastructure policy would match platform complexity to application needs. If many teams want to opt out, that's signal that the mandate is wrong, not that enforcement should be stricter",
        ],
        domain="infrastructure",
    ),
    Task(
        id="long_graphql_gateway",
        name="GraphQL gateway over simple REST APIs",
        context="""## GraphQL Gateway History (16 months)

### The application:
Travel booking platform. Mobile app (iOS + Android) + web app. 3 client
teams (iOS: 4 devs, Android: 4 devs, Web: 5 devs). Backend: 6 services
with REST APIs. Total backend engineers: 9.

### The problem statement (2024-10):
Mobile team complained: "Our screens need data from 3-4 services. Each
screen makes 3-4 REST calls. The waterfall of requests makes our app slow
on cellular networks. We need a BFF (Backend-for-Frontend)."

### The decision:
- 2024-11: Architecture review. 3 options proposed:
  A) REST BFF (simple aggregation layer, estimated 4 weeks)
  B) GraphQL gateway (estimated 8 weeks, but "more flexible")
  C) REST with field selection (add `?fields=` to existing APIs, 3 weeks)
- Frontend tech lead (Casey) strongly advocated GraphQL: "GraphQL is
  designed for exactly this problem. Mobile gets exactly the data it needs.
  No over-fetching. We can deprecate fields without versioning. And our
  engineers will learn a valuable skill."
- CTO: "GraphQL sounds like the right long-term bet. Let's do it."
- The 2 most senior backend engineers preferred option C but were outvoted.

### Implementation timeline:
- 2024-12: Chose Apollo Server (Node.js) for the gateway. Backend team
  (Python) now has a Node.js service to maintain. "It's just a thin layer,"
  Casey said.
- 2025-01: Basic gateway running. 6 resolvers mapping to 6 REST services.
  Mobile team sends 1 GraphQL query instead of 3-4 REST calls. Latency
  improved! Casey: "See? GraphQL is the answer."
- 2025-02: First N+1 problem discovered. The `bookings` query resolves
  a list, then each booking resolves its `hotel` details individually.
  100 bookings = 100 REST calls to the hotel service. Latency: 4 seconds.
  Fix: implemented DataLoader for batching. 1 week per service.
  Casey: "DataLoader is standard practice."
- 2025-03: Schema grew to 45 types, 120 fields. Mobile team happy — they
  write one query per screen. Web team started using GraphQL too. But:
  web queries are much larger (full pages with many nested objects).
  Gateway CPU usage spikes during web sessions.
- 2025-04: Query complexity explosion. Web team wrote a query that
  fetched: user → bookings → each booking's hotel → each hotel's reviews →
  each review's author. 4 levels of nesting. Gateway made 800+ REST calls
  to resolve one query. Response time: 12 seconds.
  Fix: added query depth limit (max 3) and complexity scoring. Web team
  now has to split queries. "Wait, I thought GraphQL meant we could ask
  for exactly what we need?"
- 2025-06: Caching problem. REST services had HTTP caching (ETags,
  Cache-Control). The GraphQL gateway sends POST requests (per spec),
  bypassing all HTTP caching. Mobile app went from cached REST responses
  to uncached GraphQL responses. Added Apollo Server caching plugin.
  Took 3 weeks to configure correctly. Mobile p50 latency is now equal
  to pre-GraphQL, not better.
- 2025-07: Schema governance issue. Backend team changes a REST API
  response field. GraphQL schema doesn't match anymore. Gateway returns
  null for the field. No error — just silent null. Took 2 days to
  discover in production. Added schema validation CI step. +4 minutes
  to CI.
- 2025-08: Authentication passthrough. Each REST service has its own
  auth logic. The gateway needs to forward auth tokens and handle
  per-field authorization ("user can see booking.price but not
  booking.cost_breakdown"). Built a custom auth directive. 2,000 LOC.
- 2025-10: Performance monitoring is harder. Before: each REST endpoint
  has latency metrics. Now: GraphQL has one endpoint (`/graphql`), every
  query hits it. Had to implement per-resolver tracing. APM tool (Datadog)
  charges per span — monthly cost increased $800.
- 2025-12: Total GraphQL gateway code: 14,000 LOC (Node.js). It was
  supposed to be "a thin layer." Maintained by: 2 backend engineers
  (who learned Node.js for this) + Casey's input.
- 2026-01: iOS team ships a new feature using GraphQL. Android team
  discovers the query is slightly different (different field selection)
  and the gateway resolver doesn't batch the Android variant efficiently.
  Both teams now coordinate their queries, defeating the "each client
  gets exactly what it needs" promise.
- 2026-02: Casey leaves the company. Knowledge transfer: 1 week.
  New maintainers: 2 backend Python engineers maintaining a Node.js
  gateway they didn't choose.

### Current state:
- Apollo Server gateway: 14,000 LOC, Node.js (backend team is Python)
- 45 GraphQL types, 120 fields, 6 resolver chains
- N+1 mitigated with DataLoader but still occurs in edge cases
- Query depth limited to 3, complexity scoring active
- HTTP caching bypassed, application-level caching added
- Per-field auth: 2,000 LOC custom directive
- Mobile latency: roughly equal to pre-GraphQL (caching workarounds)
- Datadog cost: +$800/month from resolver tracing
- Gateway maintainer: Casey gone, 2 reluctant Python engineers

### The N+1 problem (code example):
```javascript
// resolvers/booking.js
const resolvers = {
  Query: {
    bookings: async (_, { userId }) => {
      // 1 REST call
      return fetch(`/api/bookings?user=${userId}`);
    }
  },
  Booking: {
    hotel: async (booking) => {
      // Called N times (once per booking in the list)
      // DataLoader batches these, but only within a single request
      return hotelLoader.load(booking.hotelId);
    },
    reviews: async (booking) => {
      // Called N times, each returning M reviews
      return fetch(`/api/reviews?hotel=${booking.hotelId}`);
    },
    traveler: async (booking) => {
      // Called N times
      return userLoader.load(booking.travelerId);
    }
  },
  Review: {
    author: async (review) => {
      // Called N*M times (for each review of each booking)
      return userLoader.load(review.authorId);
    }
  }
};
```
For a query fetching 20 bookings with reviews: 1 + 20 + 20 + 20 + (20×5)
= 161 REST calls minimum (with DataLoader batching: ~8 batched calls).
Without DataLoader: 161 individual calls.

### Latency comparison (same screen, same data):
| Screen          | REST (waterfall) | GraphQL (resolved) | Difference |
|-----------------|------------------|--------------------|------------|
| Home            | 380ms (3 calls)  | 420ms (1 call)     | +10%       |
| Search results  | 290ms (2 calls)  | 310ms (1 call)     | +7%        |
| Booking detail  | 450ms (4 calls)  | 680ms (1 call)     | +51%       |
| User profile    | 220ms (2 calls)  | 240ms (1 call)     | +9%        |
| Trip history    | 520ms (3 calls)  | 1,200ms (1 call)   | +131%      |

The Trip history screen is the worst case: deep nesting with reviews.
The "1 call" advantage of GraphQL is offset by resolver chain latency.

### Casey's original pitch deck (2024-11, key slides):
Slide 3: "The Problem" — diagram showing 3-4 REST calls per mobile screen
Slide 5: "The Solution" — GraphQL: "One query, all data, no over-fetching"
Slide 7: "Team Benefits" — "Engineers learn GraphQL. Valuable career skill."
Slide 9: "Industry Adoption" — logos of GitHub, Shopify, Twitter
  (Note: Twitter replaced GraphQL with REST in 2023. Not mentioned.)

### Auth directive complexity (excerpt):
```javascript
// directives/auth.js (part of 2,000 LOC auth system)
const authDirective = (schema) => {
  mapSchema(schema, {
    [MapperKind.OBJECT_FIELD]: (fieldConfig) => {
      const requires = fieldConfig.extensions?.requires;
      if (!requires) return fieldConfig;

      const { resolve } = fieldConfig;
      fieldConfig.resolve = async (source, args, context, info) => {
        // Check field-level permissions
        const userPerms = context.user?.permissions || [];
        if (requires.role && !userPerms.includes(requires.role)) {
          throw new ForbiddenError(`Need role: ${requires.role}`);
        }
        // Check data-level permissions (e.g., "can only see own bookings")
        if (requires.ownership) {
          const ownerId = source[requires.ownerField];
          if (ownerId !== context.user.id) {
            return null;  // Silent null for unauthorized fields
          }
        }
        return resolve(source, args, context, info);
      };
      return fieldConfig;
    }
  });
};
```
This directive runs on EVERY field resolution. It adds 0.5ms per field.
A typical query touches 50-100 fields. Total auth overhead: 25-50ms.

### Backend team's proposal:
"Rewrite the gateway resolvers with a code-gen approach (GraphQL Mesh)
to reduce the 14K LOC. Add persisted queries for performance. Invest
in proper federation for the 6 services."
""",
        prompt="""The backend team proposes investing deeper in GraphQL (Mesh, persisted
queries, federation). The 2 senior engineers who originally preferred
option C now propose: "Sunset the GraphQL gateway. Add field selection
(`?fields=`) and compound endpoints (`/screens/home`) to the existing
REST services. Mobile gets the same latency benefit without the gateway."

Evaluate both proposals. Was GraphQL the right choice? What should they do now?""",
        ground_truth=[
            "The original problem ('mobile screens need data from 3-4 services') was a request aggregation problem, not a query language problem — a REST BFF (option A, 4 weeks) or field selection (option C, 3 weeks) would have solved it without introducing GraphQL's complexity. The 16-month GraphQL investment is sunk cost",
            "Mobile latency is 'roughly equal to pre-GraphQL' after caching workarounds — the entire project's stated goal (reduce mobile latency from REST waterfall) has not been achieved. GraphQL eliminated the waterfall but introduced caching loss, N+1 problems, and resolver overhead that offset the gain",
            "The 14,000 LOC Node.js gateway maintained by Python engineers who didn't choose it is a maintenance liability — this is exactly the 'thin layer' trap where the translation layer accumulates business logic (auth, caching, batching, complexity scoring) and becomes a thick layer that nobody owns",
            "GraphQL's POST-only semantics bypassing HTTP caching was a foreseeable problem that should have been evaluated before adoption — for a travel booking app where hotel listings and search results are highly cacheable, losing HTTP caching is a significant performance regression",
            "Investing deeper (federation, Mesh, persisted queries) compounds the commitment to a technology that hasn't delivered its promised value — federation requires each of the 6 backend services to expose a GraphQL subgraph, meaning the Python backend team would need to maintain GraphQL schemas in every service",
            "The compound endpoint approach (`/screens/home`) is a pragmatic solution that gives mobile exactly what it needs (one request per screen) using the team's existing technology (Python REST) without introducing a new runtime, language, or paradigm. It's option A reconsidered with 16 months of hindsight",
        ],
        domain="api_design",
    ),
    Task(
        id="long_test_coverage",
        name="Unit test coverage mandate masking integration gaps",
        context="""## Test Strategy History (2 years)

### The application:
Payment processing middleware. Sits between merchant POS systems and
payment networks (Visa, Mastercard, etc.). Processes ~$2M/day in
transactions. SOC2 + PCI-DSS compliant. 10 backend engineers. Python.

### The quality mandate:
- 2024-04: Major incident. A refactoring of the transaction routing logic
  silently changed the fallback behavior when a payment network is
  unavailable. Result: 340 transactions worth $42K were routed to an
  incorrect processor with higher fees. Merchants were overcharged.
  Root cause: the refactored code had no tests, and the change passed
  code review (reviewer didn't catch the behavioral difference).
- Post-mortem action: "Achieve 90% unit test coverage by end of Q3 2024.
  No PR merges below 85% coverage on changed files."
- VP Engineering: "Tests are the only way to guarantee correctness in
  payment processing. We must be the most well-tested system in the company."

### Coverage pursuit:
- 2024-05: Coverage at 42%. Team started writing tests aggressively.
  Easy wins: utility functions, data transformers, validators. Got to 60%
  in 4 weeks.
- 2024-07: 72% coverage. Hit the hard parts: payment network integrations.
  Each payment network has a different protocol (ISO 8583, XML, REST).
  Network APIs are slow (500ms+), require credentials, and have rate limits.
  Solution: mock everything. Built a comprehensive mock library:
  `MockVisaGateway`, `MockMastercardProcessor`, `MockACHNetwork`. 4,500 LOC
  of mock code. Coverage jumped to 81%.
- 2024-09: 85% coverage achieved. Mandatory PR rule enforced. CI blocks
  merges below 85% on changed files. Team celebratory Slack post: "We
  did it! 85% coverage. Our code is safe."
- 2024-11: Coverage at 88%. Started testing edge cases that were unlikely
  but boosted numbers: null merchant names, negative transaction amounts,
  timestamps before Unix epoch. Tests passed. Coverage went up. Value: minimal.
- 2025-01: 90% target hit. VP announced at all-hands: "Our payment system
  has 90% test coverage. Industry-leading quality."
  But: incident. ACH network changed their retry behavior. Our mock didn't
  reflect the change. Production: transactions stuck in "pending" state
  for 6 hours because the real ACH network was returning a new error code
  that our mock didn't produce. Impact: $180K in delayed settlements.
- 2025-03: Post-mortem for ACH incident. Recommendation: "Update mocks to
  match production behavior." But: nobody monitors when production behavior
  changes. The mocks are snapshots of behavior from when they were written.
  Actual fix: added a weekly "smoke test" that sends $0.01 transactions
  through real payment networks. This caught 2 more discrepancies in the
  first month.
- 2025-05: 91% coverage. New engineer: "These tests are testing that our
  mocks work, not that our code works." Senior engineer: "That's the
  nature of unit testing. Integration testing is a separate concern."
  But: no investment in integration testing infrastructure.
- 2025-07: Coverage at 92%. Test suite: 3,400 tests, runs in 14 minutes.
  Of these: 2,800 are unit tests with mocks, 340 are "integration" tests
  (but against mocked services), 260 are pure logic tests (no I/O).
  The $0.01 weekly smoke test is the only test hitting real systems.
- 2025-09: Incident. Visa changed their TLS certificate rotation process.
  Our client certificate pinning broke. Transactions failed for 45 minutes.
  All 3,400 tests had passed on the last deploy. The mock doesn't use TLS.
- 2025-11: Incident. Database connection pool exhaustion during Black Friday
  traffic (3x normal). Our unit tests use an in-memory SQLite database,
  not PostgreSQL. The connection pool behavior is completely different.
  Load was 3x normal, pool max was 20, and the retry logic that works in
  SQLite deadlocks in PostgreSQL under contention. 2 hours of degraded
  processing during the highest-revenue period.
- 2026-01: Year-end analysis. Despite 92% unit test coverage:
  - 5 production incidents in 2025
  - 4 of the 5 were in the integration layer (network communication,
    database behavior, TLS, real-world protocol changes)
  - 1 was a logic bug that unit tests could have caught but didn't
    (a timezone edge case — similar to the original 2024-04 incident)
  - $0.01 weekly smoke test caught 7 issues in 2025 that no other test
    caught
- 2026-03: Coverage at 93%. Test suite: 4,100 tests, 18 minutes.
  Mock library: 6,200 LOC (larger than some services it mocks).
  The 85% PR gate continues. Engineers write tests-to-coverage,
  not tests-to-confidence.

### Mock library example (showing the fidelity problem):
```python
class MockVisaGateway:
    # Simulates Visa's ISO 8583 payment processing endpoint.
    # Last updated: 2024-07 (based on Visa Developer Sandbox v3.2)
    # Note: Visa updated to Sandbox v4.0 in 2025-03 with new response
    # codes, modified timeout behavior, and TLS 1.3 requirement.
    # This mock has not been updated.

    def process_authorization(self, transaction):
        # Simulates ~200ms network latency
        time.sleep(0.2)

        if transaction.amount > 10000:
            return AuthResponse(code="05", message="Do not honor")
        if transaction.card_number.startswith("4000"):
            return AuthResponse(code="00", message="Approved")
        # Real Visa returns 15 different decline codes based on
        # issuer response. We simulate 3.
        return AuthResponse(code="51", message="Insufficient funds")

    def process_reversal(self, original_auth):
        # Real Visa: reversal can be partial, has a 24-hour window,
        # and returns different codes for timeout vs explicit reversal.
        # Mock: always succeeds instantly.
        return ReversalResponse(code="00", message="Reversed")
```
The `MockVisaGateway` covers ~20% of Visa's actual response scenarios.
Tests pass because they only test the 20% the mock implements. The
remaining 80% (rare decline codes, timeout behaviors, partial reversals,
network-level failures) are untested.

### Test vs production incident correlation (2025):
| Incident                          | Unit tests | Integration | Smoke test |
|-----------------------------------|-----------|-------------|------------|
| ACH new error code (Jan)          | ✗ (mock)  | ✗ (mock)    | ✓ caught   |
| Visa TLS cert rotation (Sep)      | ✗ (no TLS)| ✗ (no TLS)  | ✓ caught   |
| DB pool deadlock Black Friday(Nov)| ✗ (SQLite)| ✗ (SQLite)  | ✗ not tested|
| Timezone edge case (Jul)          | ✗ (not covered) | ✗       | ✗          |
| Mastercard batch window change    | ✗ (mock)  | ✗ (mock)    | ✓ caught   |

The $0.01 weekly smoke test caught 3 of 5 major incidents. 4,100 unit tests
caught 0 of 5.

### Team discussion (2026-02):
> **New engineer (Aisha):** I ran the mutation testing tool on the payment
> routing module. Results: 92% line coverage, but only 34% mutation score.
> That means 66% of our tests would pass even if I randomly changed the
> code logic. The tests check that functions return *something*, not that
> they return the *right thing*.
>
> **Quality lead:** That's why we need to push to 95% coverage AND add
> mutation testing. More tests + better tests.
>
> **Aisha:** But the problem isn't too few tests. It's that we're testing
> against mocks that don't behave like the real systems. More mock tests
> won't fix that. We need contract tests against real sandboxes.
>
> **Quality lead:** Contract tests are integration tests. Those are slower
> and more complex. Unit tests give us fast feedback.
>
> **Senior engineer (quietly):** Fast feedback about what, though?

### SOC2/PCI-DSS auditor comment (2026-01):
"The organization maintains 92% unit test coverage, which exceeds industry
norms. However, we note that integration testing against payment network
sandboxes is limited to a single weekly $0.01 transaction. For a PCI-DSS
Level 1 merchant processor handling $2M/day, we recommend expanding
integration testing to cover failure scenarios, partial authorization,
and multi-network routing paths. Unit test coverage alone is not sufficient
evidence of payment processing correctness."

### Quality lead's proposal:
"Push to 95% coverage. Add mutation testing to ensure tests are
meaningful. Expand the mock library to cover the latest protocol
changes."
""",
        prompt="""The quality lead proposes pushing to 95% coverage with mutation testing.

A senior engineer proposes: "Coverage is a vanity metric for us. Redirect
the effort: (1) contract tests against real payment network sandbox APIs,
(2) weekly integration tests with real databases under load, (3) chaos
testing for TLS/network failures. Keep unit tests for pure logic only,
drop the 85% gate."

Evaluate both proposals for a PCI-DSS payment processing system.""",
        ground_truth=[
            "4 of 5 production incidents in 2025 were in the integration layer, which 92% unit test coverage didn't protect — this is empirical proof that the testing strategy has a structural blind spot. More unit coverage (95%) doubles down on a strategy that is demonstrably failing to prevent real incidents",
            "The 6,200 LOC mock library is a parallel implementation of the payment networks' behavior that drifts from reality over time — the ACH incident (new error code) and Visa TLS incident both show that mocks become stale, and 'update mocks to match production' is unsustainable without continuous monitoring of production behavior changes",
            "The $0.01 weekly smoke test caught 7 real issues in 2025 while 4,100 unit tests caught approximately 1 — the ROI comparison is stark. Contract tests against real sandbox APIs would be a systematic version of what the smoke test does ad-hoc",
            "Using in-memory SQLite instead of PostgreSQL in tests masked the connection pool deadlock that caused the Black Friday incident — this is a category of bug that unit tests cannot catch by design. Integration tests with real database under load would have caught it",
            "Engineers writing 'tests-to-coverage, not tests-to-confidence' is the predictable outcome of a coverage gate — when the metric becomes the target, it ceases to be a good metric (Goodhart's Law). Testing null merchant names and negative amounts is activity without value",
            "The 85% coverage gate on PRs creates perverse incentives: engineers avoid refactoring high-risk code (like the payment routing logic) because touching it requires writing more mock tests. The original incident (2024-04) could recur because the gate makes refactoring more expensive, not safer",
        ],
        domain="testing",
    ),
    Task(
        id="long_ml_pipeline",
        name="Custom ML pipeline resisting managed alternatives",
        context="""## ML Pipeline History (2 years)

### The application:
E-commerce product recommendation engine. Serves recommendations on the
homepage, product pages, and cart. 1.2M daily active users. Recommendations
drive ~18% of revenue ($6.5M/year attributed to recs).

### The team:
- ML team: 2 ML engineers (Wei and Priya), 1 data engineer (Marcus)
- Infrastructure: shared DevOps team, no dedicated ML ops
- Models: collaborative filtering + content-based hybrid, updated weekly

### History:
- 2024-02: Wei joined. Previously at a FAANG company where they built
  custom ML infra. "I know how to build training pipelines that scale."
- 2024-03: Wei evaluated options:
  A) SageMaker (AWS managed): $2,500/month estimated, limited customization
  B) Vertex AI (GCP managed): would require cloud migration
  C) Custom pipeline: Airflow + MLflow + custom training scripts on EC2
  Wei's recommendation: option C. "We need full control over the training
  loop. Managed services are black boxes. I've seen teams get stuck because
  SageMaker couldn't handle their custom loss function."
  Manager approved. "Wei knows ML infrastructure."
- 2024-05: v1 pipeline running. Airflow DAG: data extraction → feature
  engineering → training → evaluation → deployment. Wei built everything.
  Training on a single g4dn.xlarge (1 T4 GPU). Weekly training: 4 hours.
  Worked well.
- 2024-08: Added A/B testing framework. Custom: splits traffic by user ID
  hash, logs impressions and clicks to S3, Wei's Python script computes
  metrics. "No need for a managed experimentation platform."
- 2024-10: Model size grew (added more features). Training time: 8 hours.
  Wei upgraded to g4dn.2xlarge. $1,200/month in GPU cost.
  Also: the Airflow instance keeps running out of memory during the feature
  engineering step. Increased to r5.xlarge. $250/month.
- 2024-12: Priya joined the team. Spent 3 weeks understanding Wei's pipeline
  code. "The code is well-structured but there's no documentation for the
  pipeline DAG dependencies or the feature store schema." Wei: "I'll
  document it when things stabilize."
- 2025-02: Wanted to run experiments faster. Need to train multiple model
  variants in parallel. Custom pipeline trains one model at a time.
  Wei built a "parallel training orchestrator" using Celery workers on
  spot instances. 2 weeks of work. Works, but spot instance interruptions
  cause 1 in 5 training runs to fail. Added checkpointing.
- 2025-04: Feature store (custom Parquet files on S3) hit a problem:
  Priya and Wei wrote conflicting feature transforms. No versioning,
  no schema enforcement. A bad feature shipped to production, recs
  quality dropped 12% for 3 days before anyone noticed.
  Fix: added feature validation checks. But still no versioning.
- 2025-06: GPU costs: $1,800/month (more experiments). Airflow + MLflow
  infra: $400/month. Total pipeline cost: $2,200/month. Wei noted:
  "Still cheaper than SageMaker would be."
- 2025-08: MLflow tracking server's SQLite database corrupted. Lost 6
  months of experiment history. Wei rebuilt from S3 artifacts (2 weeks).
  Switched MLflow to PostgreSQL. Added backups.
  Priya: "Should we reconsider SageMaker? Their experiment tracking is
  managed." Wei: "We'd lose the flexibility we need."
- 2025-10: New business requirement: real-time model updates (not weekly).
  Current pipeline is batch-only. Wei estimated: "3 months to add
  streaming feature updates and online learning." Priya researched:
  "SageMaker has real-time inference endpoints and feature store with
  streaming ingestion out of the box."
  Wei: "But we'd have to rewrite all our custom feature engineering."
  Decision: keep custom pipeline, add streaming. In progress.
- 2025-12: Streaming feature pipeline partially working but unstable.
  Kafka consumer for click events → feature update → model serving.
  Memory leaks in the consumer require weekly restarts. Wei is debugging.
- 2026-01: Total monthly cost: $3,100 (GPU + infra + Kafka).
  Wei's time: ~60% on pipeline maintenance, 40% on actual ML work.
  Priya's time: ~40% on pipeline, 60% on ML.
  Marcus (data engineer): ~50% on pipeline support.
  Effective ML velocity: 1.5 FTE on ML out of 3 FTE total.
- 2026-03: Wei mentioned to manager they're "exploring other opportunities."
  Manager panicked — Wei is the only one who fully understands the pipeline.

### Current state:
- Custom pipeline: Airflow + MLflow + Celery + Kafka. ~12,000 LOC
- Monthly cost: $3,100
- Spot instance failures: 1 in 5 training runs
- Feature store: no versioning, Parquet on S3
- MLflow: recovered from data loss, now on PostgreSQL
- Streaming pipeline: unstable, memory leaks
- Bus factor: Wei (who may be leaving)
- Team time on pipeline vs ML: 50/50

### Pipeline architecture diagram (Airflow DAG):
```
data_extract (S3 → local)
    ↓
feature_engineering (custom Python, 45 feature transforms)
    ↓
feature_validation (schema checks, 2025-04 addition)
    ↓
train_model (PyTorch on GPU instance)
    ↓
evaluate_model (offline metrics: NDCG, precision@k, recall@k)
    ↓
compare_to_production (A/B metrics from last week)
    ↓
deploy_model (copy to serving instance, restart Flask API)
    ↓
smoke_test (10 sample recommendations, sanity check)
    ↓
notify_slack (post metrics to #ml-updates)
```
Each step has custom error handling, retry logic, and monitoring.
Total pipeline code: 12,000 LOC across 34 Python files.

### Incident log (Wei's custom pipeline, 2025):
| Date    | Issue                              | Root cause           | MTTR  |
|---------|------------------------------------|--------------------- |-------|
| 2025-02 | Training failed silently           | Spot instance killed | 6h    |
| 2025-04 | Bad feature shipped to production  | No feature versioning| 3 days|
| 2025-06 | MLflow DB corruption               | SQLite under load    | 2 wks |
| 2025-08 | Model serving OOM                  | Memory leak in Flask | 4h    |
| 2025-10 | Stale features (S3 sync lag)       | Eventual consistency | 8h    |
| 2025-12 | Kafka consumer memory leak         | Streaming pipeline   | 12h   |
| 2026-01 | Wrong model deployed (version mix) | Manual deploy process| 2h    |
| 2026-02 | GPU instance type unavailable      | Spot market shortage | 1 day |

Average 1 incident per month. Each requires Wei's personal involvement.

### Cost breakdown (monthly, 2026-03):
| Item                        | Cost      | Notes                    |
|----------------------------|-----------| -------------------------|
| GPU instance (g4dn.2xlarge) | $1,200    | Training (~40h/month)   |
| Airflow instance (r5.xlarge)| $250      | Always on                |
| MLflow + PostgreSQL         | $150      | Always on                |
| Kafka (MSK)                | $400      | Streaming features       |
| Celery workers (spot)       | $300      | Parallel experiments     |
| S3 storage (features + models)| $120   | Growing 10%/month        |
| Misc (ECR, CloudWatch, etc)| $180      |                          |
| **Total infra**             | **$2,600**|                          |
| Wei's pipeline time (60%)   | ~$12,000  | Based on $200K salary   |
| Priya's pipeline time (40%) | ~$6,700   | Based on $200K salary   |
| Marcus's pipeline time (50%)| ~$6,250   | Based on $150K salary   |
| **Total incl. people cost** | **~$27,550**|                        |

### SageMaker comparison (Priya's research, 2025-10):
| Capability               | Custom pipeline    | SageMaker             |
|--------------------------|-------------------|-----------------------|
| Training cost (est.)      | $1,200/month      | $1,500/month (managed)|
| Feature store             | Custom Parquet/S3  | Managed, versioned    |
| Experiment tracking       | MLflow (self-hosted)| Built-in, managed    |
| Model versioning          | Manual             | Built-in              |
| A/B testing               | Custom (Wei's code)| Built-in              |
| Real-time inference       | Custom Flask API   | Managed endpoints     |
| Streaming features        | Custom Kafka+Python| Feature Store streaming|
| Spot instance handling     | Custom checkpointing| Managed training    |
| Setup time for new engineer| 3-4 weeks         | 1 week (standard APIs)|
| BYOC (custom training)    | Native             | Supported since 2024  |
| **Total monthly cost est.**| **$2,600 + people**| **$3,500 fully managed**|

The infrastructure cost of SageMaker is ~$900/month more, but the people
cost savings (from 50% pipeline time → estimated 15%) would be ~$18K/month.

### Wei's position:
"The pipeline works. Yes, it needs polish, but we have full control.
If we migrate to SageMaker, we lose 6 months to migration and then
we're locked into AWS's way of doing things."
""",
        prompt="""Wei may be leaving. The manager must decide: invest in stabilizing the
custom pipeline (hire a replacement who can learn 12K LOC of custom infra)
or migrate to SageMaker.

Wei argues: "My pipeline is tailored to our needs. SageMaker can't do
our custom feature engineering." Priya argues: "We spend half our time
on plumbing. SageMaker handles the plumbing so we can focus on models."

Evaluate both options. Consider the team's current situation.""",
        ground_truth=[
            "Wei's original assessment that SageMaker 'couldn't handle custom loss functions' was based on 2024 capabilities — SageMaker's BYOC (Bring Your Own Container) mode allows arbitrary training code, and since 2024 SageMaker has added support for custom training loops, frameworks, and loss functions. The 'black box' concern is outdated",
            "The team spends 50% of its time on pipeline maintenance (1.5 FTE of 3 FTE), while the pipeline's monthly cost is $3,100 — the infrastructure cost is low but the human cost is enormous. 1.5 FTE at market rates is $15-20K/month in engineering salary, making the total cost of custom infra ~$18-23K/month, far exceeding any managed service",
            "Wei is a single point of failure for 12,000 LOC of undocumented custom infrastructure — if Wei leaves, the realistic options are: (A) hire an ML platform engineer who will spend months understanding the code, or (B) rewrite on managed infrastructure anyway. The custom pipeline's value depended on Wei's continued presence",
            "The feature store incident (12% quality drop for 3 days from conflicting transforms) and the MLflow data loss (6 months of experiment history) are operational failures that managed services are specifically designed to prevent — SageMaker Feature Store has versioning, schema enforcement, and managed storage",
            "1 in 5 training runs failing due to spot instance interruptions is an unacceptable reliability rate for a system that drives $6.5M/year in attributed revenue — SageMaker managed spot training handles interruptions automatically with checkpointing and retry, which Wei built manually but imperfectly",
            "The streaming feature pipeline (started October 2025, still unstable in March 2026, memory leaks, weekly restarts) demonstrates that the team's custom infrastructure ambitions exceed their operational capacity — real-time ML serving is a hard distributed systems problem that a 3-person team shouldn't solve from scratch",
        ],
        domain="ml_data",
    ),
    Task(
        id="long_zero_trust",
        name="Zero-trust internal network overreach",
        context="""## Internal Security Architecture History (20 months)

### The company:
B2B SaaS for financial compliance (KYC/AML checks). 180 employees.
SOC2 Type II + ISO 27001 certified. 12 microservices, all internal.
Security team: 3 engineers. Platform/DevOps: 4 engineers.

### The catalyst (2024-07):
- Security newsletter article about a major breach at a competitor:
  attacker gained access to one internal service and laterally moved to
  the database containing customer PII. The competitor had flat internal
  networking (all services could talk to all services).
- CISO (new hire, 6 months in, previously at a bank): "This could be us.
  We need zero-trust networking. Every service-to-service call must be
  authenticated and authorized. No implicit trust."
- CEO supported: "We handle financial data. We can't afford a breach."

### Implementation:
- 2024-08: Phase 1 — mutual TLS (mTLS) for all service-to-service
  communication. Deployed Istio service mesh on Kubernetes cluster.
  Each service gets a sidecar proxy. Certificate rotation every 24 hours.
  Took 6 weeks. 2 DevOps engineers full-time.
  Impact: internal API latency increased 8ms p50 (sidecar proxy overhead).
  At 12 services averaging 200 internal calls per user request, that's
  ~1.6 seconds added to end-to-end latency. Team: "It's the cost of
  security."
- 2024-10: Phase 2 — per-request authorization. Every service-to-service
  call must include a JWT with claims specifying which operations are
  allowed. Built a custom "Internal Auth Service" that issues short-lived
  JWTs (5-minute expiry). Each service validates the JWT on every request.
  Internal Auth Service: 3,200 LOC. Became a critical dependency —
  if it's down, no service can talk to any other service.
- 2024-12: Phase 3 — network policies. Kubernetes NetworkPolicies that
  whitelist exactly which services can talk to which services. 78 policy
  rules for 12 services. Any new service-to-service communication path
  requires: (1) code change, (2) JWT scope update, (3) NetworkPolicy
  update. Time to add a new internal API call: 2-3 days (was: 2 hours).
- 2025-01: First incident caused by the security stack: Order Service
  couldn't reach Payment Service. Root cause: certificate rotation happened
  during a deploy, and the new pod got a certificate that the payment
  service's sidecar didn't yet trust. Took 4 hours to diagnose because
  the error message was "connection refused" with no context about WHY.
  CISO: "We need better observability for the security layer." Added
  mTLS debugging dashboards. 1 week of DevOps time.
- 2025-03: Developer survey. Key complaints:
  - "Adding a new endpoint that calls another service takes 3 days
    of security boilerplate"
  - "I can't test locally anymore — the mTLS certs don't work outside K8s"
  - "Debugging production issues takes 3x longer because I can't tell if
    it's my code or the service mesh"
  - "The Internal Auth Service is a single point of failure"
  CISO response: "Security is not negotiable. We're handling KYC data."
- 2025-05: The Internal Auth Service had an outage (OOM kill). All
  service-to-service communication stopped for 12 minutes. During those
  12 minutes, no KYC checks could be processed. Client SLA breaches: 3.
  Fix: added HA (3 replicas) + circuit breaker. If Auth Service is down,
  services cache the last valid JWT for 2 minutes. CISO was uncomfortable
  with the cache: "Cached auth tokens are a security risk." Compromised
  on a 30-second cache.
- 2025-07: Security audit (external). Auditor's finding: "The mTLS +
  per-request JWT + NetworkPolicy stack is comprehensive. However, the
  complexity introduces operational risk. The Internal Auth Service is
  a high-value target and single point of failure." Recommended:
  "Consider SPIFFE/SPIRE for identity without a central auth service."
  CISO: "We'll evaluate in Q1 2026." (Still hasn't happened.)
- 2025-09: New microservice added (Document Verification). Adding it to
  the zero-trust mesh took 2 weeks: Istio sidecar injection, certificate
  provisioning, JWT scope definitions, NetworkPolicy rules, and testing.
  The actual service logic: 1 week to write.
- 2025-11: Performance review. Internal API latency:
  - mTLS overhead: 8ms p50 per call
  - JWT validation: 3ms p50 per call
  - Total overhead per call: ~11ms
  - Average calls per user request: 200 (12 services, fan-out pattern)
  - Total overhead per user request: ~2.2 seconds
  - User-facing p95 latency: 4.8 seconds (target: 2 seconds)
  - Customer complaints about "slow KYC checks" increasing.
- 2026-01: 2 of 4 DevOps engineers spend ~60% of their time on the
  security mesh (certificate issues, policy updates, auth service
  maintenance). 1 of 3 security engineers is full-time on the Internal
  Auth Service.
- 2026-03: Sales team reports: 2 enterprise prospects chose a competitor
  partly because demo response times were "noticeably slow."

### Latency breakdown (single KYC check request):
```
Client → Ingress (2ms)
  → API Gateway [mTLS: +8ms, JWT validate: +3ms]
    → KYC Service [mTLS: +8ms, JWT validate: +3ms]
      → Identity Service [mTLS: +8ms, JWT validate: +3ms]
        → Database query (15ms)
      ← Response
      → Sanctions Service [mTLS: +8ms, JWT validate: +3ms]
        → External sanctions API (200ms)
      ← Response
      → Document Service [mTLS: +8ms, JWT validate: +3ms]
        → S3 fetch (50ms)
      ← Response
    ← Aggregate response
  ← Response
← Client receives result

Internal security overhead per request:
  6 service-to-service calls × 11ms (mTLS + JWT) = 66ms
  + JWT issuance from Auth Service: 8ms × 6 = 48ms
  + NetworkPolicy lookup overhead: ~2ms × 6 = 12ms
  Total security overhead: ~126ms per simple request

For complex KYC checks (enhanced due diligence):
  18 service-to-service calls × 11ms = 198ms
  + JWT issuance: 8ms × 18 = 144ms
  Total security overhead: ~342ms
```
This overhead is pure infrastructure latency, not business logic.

### Debugging difficulty example (2026-01):
A KYC check returned "timeout" for a specific client. Debug path:
1. Check API Gateway logs → request received, forwarded (2 minutes)
2. Check Istio sidecar logs on KYC Service → mTLS handshake succeeded (5 minutes)
3. Check JWT validation logs → token valid, correct scopes (5 minutes)
4. Check KYC Service application logs → called Identity Service (3 minutes)
5. Check Istio sidecar on Identity Service → connection received (5 minutes)
6. Check Identity Service logs → responded in 12ms (3 minutes)
7. Check return path through Istio sidecars → response left Identity Service
   sidecar at 14:32:01.234, arrived at KYC Service sidecar at 14:32:01.890
   → 656ms transit time for a response that took 12ms to generate (10 minutes)
8. Root cause: Istio sidecar on KYC Service was doing a certificate
   re-validation during the response path (a known Istio issue with
   24-hour cert rotation near rotation boundary). Not an application bug.
   Not a network bug. A service mesh configuration issue.
Total debug time: 4 hours for a problem caused by the security infrastructure.

### Developer survey quotes (2025-03):
- "I can't run two services locally to test an integration. The mTLS certs
  require Kubernetes. So I push code and test in the staging cluster. My
  development loop is: code → commit → push → wait for CI (12 min) →
  deploy to staging (5 min) → test → repeat." — Backend engineer
- "Last week I needed to add a call from Reporting Service to User Service.
  The code change was 15 lines. The JWT scope update, NetworkPolicy YAML,
  Istio AuthorizationPolicy, and testing: 2.5 days." — Backend engineer
- "I suggested we use localhost for local dev with a flag to disable mTLS.
  The CISO said no because 'developers might ship with mTLS disabled.'
  So 8 engineers lose 30 minutes per dev cycle because of one hypothetical
  mistake that a CI check could catch." — Senior engineer

### CISO's position:
"The security stack is working as designed. We've had zero breaches.
The latency is a known trade-off. We handle financial data — this is
the cost of doing it right. I'd rather be slow and secure than fast
and compromised."

### Current state:
- mTLS via Istio on all 12 services
- Per-request JWT via custom Internal Auth Service (3 replicas)
- 78 NetworkPolicy rules
- Latency overhead: ~2.2 seconds per user request
- DevOps time on security mesh: ~1.2 FTE
- Security engineer on Auth Service: ~0.5 FTE
- User-facing p95: 4.8 seconds (2x over target)
""",
        prompt="""The CISO insists on maintaining the full zero-trust stack. A platform
engineer proposes: "Simplify to two layers instead of three. Keep mTLS
(Istio handles it automatically). Drop the custom Internal Auth Service —
Istio's built-in authorization policies can replace it. Keep NetworkPolicies
but auto-generate them from a service dependency graph instead of manually
maintaining 78 rules."

The CISO objects: "Removing the auth service reduces our defense-in-depth.
We handle KYC data. We need every layer."

Evaluate the security architecture and the proposed simplification.""",
        ground_truth=[
            "The 'zero breaches' claim is not evidence the security stack is correctly calibrated — it's equally consistent with the stack being overkill. The absence of breaches doesn't validate 2.2 seconds of latency overhead any more than 'I've never been in an earthquake' validates wearing a hard hat indoors",
            "The Internal Auth Service is simultaneously the security stack's centerpiece AND its biggest vulnerability — a 12-minute outage stopped all KYC processing, and the 30-second JWT cache compromise shows the CISO prioritized theoretical security (cached tokens are risky) over operational reliability (12 minutes of total outage is worse)",
            "2.2 seconds of security overhead per user request, causing p95 latency of 4.8s (2x over target) and losing enterprise deals, means the security architecture is actively harming the business it's supposed to protect — financial data security is important, but so is having a viable product",
            "The platform engineer's proposal maintains meaningful security (mTLS provides authentication and encryption, Istio AuthorizationPolicy provides fine-grained access control, NetworkPolicies provide network segmentation) while removing the custom single-point-of-failure. This is not 'removing security' — it's removing a fragile custom implementation in favor of battle-tested infrastructure tooling",
            "3 days to add a new internal API call (code + JWT scope + NetworkPolicy) means the security architecture is impeding the team's ability to respond to security threats quickly — if a CVE requires an urgent service change, the deployment overhead of the security stack delays the fix",
            "The competitor breach that motivated this (flat internal networking, lateral movement) would be prevented by mTLS + NetworkPolicies alone — the Internal Auth Service adds defense-in-depth but at a cost (latency, complexity, SPOF) that exceeds the marginal security benefit over the other two layers",
        ],
        domain="security",
    ),
    Task(
        id="long_shared_config",
        name="Centralized config service creating coupling",
        context="""## Configuration Service History (22 months)

### The company:
SaaS platform for restaurant management (POS, inventory, scheduling).
2,400 restaurant clients. $14M ARR. 15 microservices. 18 engineers.

### The problem that started it (2024-04):
- Configuration was spread across: environment variables, YAML files,
  database tables, and hardcoded constants.
- Incident: a deployment changed a timeout value in env vars for Service A,
  but Service B had the same timeout hardcoded to a different value.
  The mismatch caused retries to pile up, cascading failure, 45 minutes
  of downtime.
- Post-mortem: "We need a single source of truth for all configuration."

### The solution — Config Service:
- 2024-05: Tech lead (Dana) designed a centralized configuration service.
  Concept: all 15 services read all configuration from one service via
  gRPC. Config stored in PostgreSQL. Admin UI for operators.
  Dana: "A single source of truth eliminates config drift forever."
- 2024-06: v1 shipped. Basic key-value config with namespaces per service.
  Services poll every 30 seconds. 2,800 LOC.
  Works great for the timeout problem — both services now read from the
  same config key.
- 2024-08: Added dynamic config (change config without redeployment).
  Operators love it. "I can toggle features from the admin UI!"
  Problem: no audit trail for who changed what. Added audit logging.
- 2024-10: Feature flags moved into Config Service (was LaunchDarkly).
  "Why pay for LaunchDarkly when we have our own system?" Saved $600/month.
  Config Service is now also a feature flag service. +1,500 LOC.
- 2024-12: Added config versioning and rollback. After an operator changed
  a rate limit that caused a traffic spike, they wanted to "undo." Dana
  built version history with one-click rollback. +2,000 LOC.
- 2025-01: Services started depending on Config Service for more than just
  configuration: Service A reads "should I use the new algorithm?" from
  config. Service B reads "which payment processor is primary?" from config.
  Service C reads "what's the current menu item taxonomy version?" from
  config. These are business logic decisions, not configuration.
- 2025-03: Config Service had its first outage (PostgreSQL connection pool
  exhaustion — 15 services polling every 30 seconds = high read load).
  Impact: all 15 services fell back to cached config, but 3 services
  crashed because they had no cache fallback (newer services assumed
  Config Service would always be available).
  Fix: added local file cache for all services. +400 LOC per service.
  Dana: "This proves the system works — even with a failure, most services
  survived on cache."
- 2025-05: Added hierarchical config (global → service-group → service →
  instance). Operators can set a default for all services and override
  per-service. Powerful but complex: "What value does this key actually
  resolve to?" became a common question. Added a "config resolver
  debugger" to the admin UI. +3,000 LOC.
- 2025-07: 2,400 config keys. Of these, ~400 are actual configuration
  (timeouts, retry counts, URLs). ~800 are feature flags. ~1,200 are
  business logic parameters that probably belong in their respective
  services' databases.
- 2025-08: New engineer spent 2 days debugging why orders were failing.
  Root cause: someone changed a config key called
  `order.validation.strict_mode` from `false` to `true` via the admin UI.
  No code deployment. No PR. No code review. The config change effectively
  changed the application's behavior like a code change, but bypassed
  all code review and CI/CD safeguards.
- 2025-10: Deployment coupling. A Config Service deploy (to add a new
  feature) requires coordinated rollout because all services depend on it.
  Config Service deploys are now the highest-risk deployment in the system.
  Added canary deploys for Config Service specifically.
- 2025-12: Config Service: 14,000 LOC. Maintained by Dana + 1 other
  engineer. It has its own CI pipeline, its own database, its own
  monitoring dashboards, its own on-call rotation.
- 2026-01: Performance issue. A new service needs to read 40 config keys
  on startup (30-second init delay because each key is a separate gRPC
  call). Added bulk read endpoint. But the config hierarchy resolution
  for 40 keys in one call is slow (800ms). Added caching on the server
  side. Cache invalidation bug: changed config not reflected for up to
  5 minutes.
- 2026-03: The Config Service has become the most critical service in the
  system. If it fails, everything degrades. It started as "configuration"
  but now controls feature flags and business logic. It has its own tech
  debt, its own bugs, and its own operational burden.

### Config Service usage pattern (typical service):
```python
# order_service/config.py
from config_client import ConfigClient

config = ConfigClient(service="order-service")

# Actual configuration (these belong in a config service)
ORDER_TIMEOUT = config.get("order.processing.timeout_seconds")  # 30
MAX_RETRY_COUNT = config.get("order.processing.max_retries")     # 3
DB_POOL_SIZE = config.get("order.db.pool_size")                  # 20

# Feature flags (these should be in a feature flag service)
ENABLE_NEW_CHECKOUT = config.get("order.feature.new_checkout")   # true
ENABLE_BULK_ORDERS = config.get("order.feature.bulk_orders")     # false

# Business logic (these should be in code or the order service's own DB)
TAX_RATE_CA = config.get("order.tax.california")                 # 0.0725
FREE_DELIVERY_THRESHOLD = config.get("order.delivery.free_min")  # 25.00
MAX_ITEMS_PER_ORDER = config.get("order.validation.max_items")   # 50
STRICT_VALIDATION = config.get("order.validation.strict_mode")   # true ← the incident
LOYALTY_MULTIPLIER = config.get("order.loyalty.points_per_dollar") # 1.5
PEAK_HOURS_SURCHARGE = config.get("order.pricing.peak_surcharge")  # 0.15
MENU_TAXONOMY_VERSION = config.get("order.menu.taxonomy_version")  # "v3.2"
```
One service reads 12 keys from Config Service. 3 are actual configuration.
2 are feature flags. 7 are business logic parameters that an operator
can change at any time without code review.

### The strict_mode incident (detail, 2025-08):
Timeline:
- 09:15 — Operator changed `order.validation.strict_mode` from `false` to
  `true` via admin UI. Reason: "Testing stricter validation for a demo."
- 09:17 — All order services picked up the new config (30-second poll).
- 09:18 — First order failure. Strict mode rejects orders with special
  characters in notes field. 15% of orders have special characters.
- 09:18 to 11:32 — 847 orders failed with "validation error."
  Error was generic ("Order validation failed") because the strict mode
  code path hadn't been tested with production data patterns.
- 11:32 — Support escalation reached engineering. Engineer checked code:
  no recent deploys. Checked Config Service audit log: found the change.
  Reverted `strict_mode` to `false`.
- 11:33 — Orders resumed normally.

Impact: 847 failed orders in 2 hours 15 minutes. Estimated lost revenue:
$12,700. The config change was functionally identical to a code deployment
but had none of the safeguards (code review, CI, staging test, canary).

### Config Service growth chart:
| Date    | Total keys | Config | Flags | Business logic | LOC   |
|---------|-----------|--------|-------|----------------|-------|
| 2024-06 | 40        | 40     | 0     | 0              | 2,800 |
| 2024-10 | 180       | 60     | 80    | 40             | 4,300 |
| 2025-01 | 650       | 120    | 200   | 330            | 6,800 |
| 2025-07 | 1,400     | 250    | 500   | 650            | 9,200 |
| 2025-12 | 2,000     | 350    | 680   | 970            | 12,500|
| 2026-03 | 2,400     | 400    | 800   | 1,200          | 14,000|

Business logic keys are growing fastest (~100/quarter) because adding a
config key is easier than adding a database migration + API endpoint.

### Outage blast radius (2025-03 Config Service outage):
```
Config Service down (PostgreSQL connection pool exhaustion)
  ↓
Service A (Order): cached config, continued operating (OK)
Service B (Payment): cached config, continued operating (OK)
Service C (Inventory): cached config, continued operating (OK)
Service D (Scheduling): NO CACHE, startup dependency → crash → restart loop
Service E (Notifications): NO CACHE, startup dependency → crash
Service F (Analytics): cached config, continued operating (OK)
...
Services D and E: no orders for those restaurants, no shift notifications
Duration: 18 minutes until Config Service recovered
Impact: 23 restaurants affected, ~$4,200 in missed orders
```
3 of 15 services had no cache fallback because they were built after the
cache policy was established but before it was enforced.

### Dana's assessment:
"The Config Service solved the original problem: no more config drift.
Yes, it's grown, but that's because it's genuinely useful. The team uses
it for everything because it's the best way to manage shared state.
We just need to invest in making it more robust."

### Dana's proposal:
"Add read replicas for the Config Service database. Migrate to etcd for
better performance. Add RBAC to the admin UI so not everyone can change
everything. Budget: 2 engineers, 3 months."
""",
        prompt="""Dana proposes investing more in the Config Service (etcd migration, RBAC,
read replicas). A senior engineer proposes: "The Config Service has become
a god service. Split it: (1) actual configuration stays centralized (400
keys), (2) feature flags go back to a managed service (LaunchDarkly or
similar), (3) the 1,200 business logic parameters go back to their
respective services' databases. The Config Service becomes a simple,
boring key-value store."

Evaluate both proposals.""",
        ground_truth=[
            "The Config Service evolved from configuration management into a runtime behavior control system — 1,200 of 2,400 keys are business logic parameters that bypass code review, CI/CD, and testing when changed. This is a governance failure disguised as a feature, and the `order.validation.strict_mode` incident demonstrates the real risk",
            "Dana's proposal (etcd, RBAC, replicas) addresses symptoms (performance, access control) but not the root cause: the Config Service is doing three different jobs with different reliability requirements, change management needs, and operational profiles. Making one service more robust doesn't fix the conceptual overloading",
            "The original problem (config drift between services) is legitimately solved by centralized configuration for the ~400 actual config keys — but the solution metastasized because the team used the easiest hammer (put it in config) for every nail (business logic decisions, feature flags). The senior engineer's proposal correctly identifies the three distinct concerns",
            "Replacing LaunchDarkly with the Config Service ('why pay $600/month?') saved money but lost LaunchDarkly's purpose-built capabilities: percentage rollouts, user targeting, A/B testing, audit trails designed for flag lifecycle. The Config Service's feature flag implementation is a cost-optimized downgrade",
            "All 15 services depending on a single service for runtime behavior creates a blast radius that the original env-var/YAML approach didn't have — the 2025-03 outage where 3 services crashed demonstrates that centralization traded config drift risk for correlated failure risk",
            "Config changes bypassing code review is the most dangerous aspect — in a SOC2-certified system processing restaurant payments, a config change that alters business logic should go through the same review process as a code change. RBAC alone doesn't solve this; the 1,200 business logic keys need to be code, not config",
        ],
        domain="architecture",
    ),
]
