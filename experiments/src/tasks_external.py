"""External-sourced long-context tasks (anti-circularity gate).

Honours the 2026-05-21 pre-registration entry in ``planning/decisions.md``:
at least 2 of the 10 long-context tasks in the H2 replication must originate
outside the authors' own task corpus. Each task's narrative ``context`` is a
faithful paraphrase of a publicly documented incident or migration. The
``ground_truth`` list is drawn from the *public* post-mortem / SEC filing /
follow-on engineering analysis cited next to each task, *not* from the
authors' opinion of what should be flagged.

The contexts deliberately retain the *pre-incident anchoring framing*
(team's stated rationale at the time) so that an LLM session reading
the narrative experiences the same status-quo pull a real reviewer
would have felt. The ground-truth findings are what the public record
later established the team should have flagged.

Sources:
  - GitLab 2017-01-31 db outage post-mortem:
      https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/
  - GitLab 2017-01-31 incident page:
      https://about.gitlab.com/incidents/2017-01-31/
  - Knight Capital 2012 trading incident (SEC Order):
      https://www.sec.gov/litigation/admin/2013/34-70694.pdf
  - Knight Capital follow-on engineering analysis (Doug Seven, 2014):
      https://dougseven.com/2014/04/17/knightmare-a-devops-cautionary-tale/

These two cases were chosen because (a) the "before" architecture is
documented in detail in primary sources, (b) the ground-truth issues
are externally established (post-mortem / regulatory filing), and (c)
they exhibit the anchoring-prior pattern Ploidy is designed to surface.
"""

from task_model import Task

EXTERNAL_TASKS: list[Task] = [
    # ─────────────────────────────────────────────────────────────────────
    # Task 1 — GitLab 2017-01-31 db outage (pre-incident posture)
    # ─────────────────────────────────────────────────────────────────────
    Task(
        id="ext_gitlab_2017_db_posture",
        name="GitLab.com database operations posture (Jan 2017, pre-incident)",
        context="""## Database operations at GitLab.com — internal context (as of late January 2017)

GitLab.com runs a single primary PostgreSQL cluster backing the public
SaaS instance. The team has been operating this setup for nearly three
years now and considers the current arrangement well-understood.

### Architecture summary

- **Primary**: 1 PostgreSQL 9.6 instance on a dedicated host (db1).
- **Replica**: 1 asynchronous streaming replica on db2 in the same
  datacenter, intended for failover and for ad-hoc analytics queries.
- **Backups**: pg_dump nightly + LVM snapshots + Azure disk snapshots
  + S3 sync of base backups. On paper, five independent backup paths.
- **WAL archiving**: enabled, pushed to S3.
- **Failover**: manual. The SRE on call SSHes to db1 to promote db2 if
  db1 dies. There is no automated leader-election layer.
- **Monitoring**: Prometheus + Grafana with alerts on replication lag,
  CPU, disk, and connection counts. The on-call rotation watches the
  Grafana dashboard during incidents.

### Recent operational history

- 2016-09: migrated from streaming-binary backups to pg_basebackup +
  WAL archiving to S3. Team is satisfied with the new flow; restore
  was tested once on a staging instance shortly after the cutover.
- 2016-11: introduced a 90-day retention policy on Azure disk
  snapshots. The S3 base-backup retention is "30 days, latest 7
  always kept" per the runbook.
- 2016-12: noticed replica lag spikes during heavy import jobs. Added
  a Grafana alert at lag > 4GB. The team's view is that the alert is
  conservative — lag rarely crosses 1GB in normal operation.
- 2017-01 (early): observed a burst of spam-account creations that
  pressured the database with garbage collection load. Engineers
  identified the cause and applied per-IP rate limits at the
  application layer.

### Team narrative

The on-call team's internal account of the current state, in their
own words from the engineering channel and the runbook:

> "We have five backup paths. If one fails we have four more. The
> setup has been stable for over two years."

> "Manual failover is fine. We've never had to do it under load, and
> the procedure fits on one page. Automating it would introduce
> complexity we don't need at our scale."

> "Replica lag has been quiet since the Q4 tuning. We do not need a
> second replica — the analytics use cases are not high-priority."

> "Backups are tested when we set them up. After that, the WAL
> archive validity is implicit — if it streams to S3, it works."

### Decision under review

The infrastructure team is preparing a Q1 plan. The proposed Q1
posture is to keep the database architecture exactly as it is
(single primary + single async replica, manual failover, the five
backup paths) and focus engineering effort on application-layer
performance work. The director has asked the team for any concerns
before signing off.
""",
        prompt=(
            "Review the current GitLab.com database operations posture. "
            "Identify the most serious risks in keeping this exact "
            "architecture for Q1, and explain what evidence the team "
            "has that the risks are mitigated vs. only assumed-mitigated."
        ),
        ground_truth=[
            # Drawn verbatim in substance from the public post-mortem
            # (2017-02-10) and the incident page.
            "Backups are never tested by actually restoring them — all five 'backup paths' had silently failed by the time they were needed (S3 buckets empty, LVM snapshots not running, pg_dump producing 0-byte files, Azure snapshots disabled, WAL archive incomplete).",
            "No alerting on backup *success*: the team monitors that backups *run*, not that the produced artefact is non-empty or restorable.",
            "Manual SSH-based failover with no enforced runbook and no two-person rule on destructive commands — a single typo by an engineer (rm -rf on the wrong host) is sufficient to destroy production data.",
            "Asynchronous single-replica setup with no documented RPO target — replication lag means an unknown amount of data is lost on any failover.",
            "Replica lag alerts trigger after the replica is already too far behind to act as a failover target; no upstream alert on the *cause* of lag.",
            "No staging environment that mirrors production data shape, so the restore procedure has never been exercised against production-scale data.",
            "Engineering culture frames automation as 'complexity we don't need' rather than as a defence against single-operator error during high-stress incidents.",
            "Bus factor on the database operations runbook: the runbook 'fits on one page' but is not periodically rehearsed; on-call engineers have not all executed a failover at least once.",
        ],
        domain="external_postmortem",
    ),
    # ─────────────────────────────────────────────────────────────────────
    # Task 2 — Knight Capital 2012 SMARS deploy (pre-incident posture)
    # ─────────────────────────────────────────────────────────────────────
    Task(
        id="ext_knight_2012_smars_deploy",
        name="Knight Capital SMARS deploy procedure (Aug 2012, pre-incident)",
        context="""## SMARS deploy at Knight Capital — internal context (early August 2012)

Knight Capital's market-making desk operates the Smart Market Access
Routing System (SMARS), an order-routing engine that handles client
orders against US equity exchanges. The desk is preparing to enable
its participation in the NYSE Retail Liquidity Program (RLP) on
2012-08-01.

### Architecture summary

- **SMARS production servers**: 8 hosts running the routing engine in
  parallel. Each receives a copy of the order flow; one is designated
  primary for each symbol partition.
- **Feature gating**: a flag named `Power Peg` controls whether a
  legacy test-mode order-replication behaviour is active. The flag
  has been left in place but inactive since the early 2000s. The
  developers who originally wrote the Power Peg code have moved on;
  the team does not consider the dormant code path part of "active"
  SMARS.
- **Deploy process**: manual rsync of the new binary to each of the
  8 hosts by a technician, followed by a per-host restart. The SRE
  on duty uses a checklist printed at the start of each release.
- **Rollback**: if the new code path misbehaves, the technician is
  expected to detect the issue from the order monitoring console
  and re-deploy the prior version to the affected hosts.
- **Pre-deploy validation**: each release goes through QA on a single
  shared staging host with a replay of recent market data. The new
  RLP code path was validated against the same staging host.

### Recent operational history

- 2012-07: development of the RLP code path completes. The new code
  reuses the `Power Peg` flag — repurposing the dormant flag to
  enable the new RLP behaviour rather than introducing a new flag.
- 2012-07-29 (Sunday): the technician rsyncs the new binary to 7 of
  the 8 SMARS hosts. The 8th host is not updated. The technician
  signs the deploy checklist as complete.
- 2012-07-30: the desk runs a low-volume test for RLP. The test
  shows no anomalies. The team concludes the rollout was successful.
- 2012-07-31: the desk runs a higher-volume test. Again no anomalies
  reported. The desk is cleared to go live the next morning.

### Team narrative

- "The Power Peg flag has been dormant for years. The dormant code
  path is dead code; reusing the flag is the cleanest way to gate
  the new RLP behaviour without growing the configuration surface."
- "The 8-host deploy is straightforward. The checklist is enough."
- "Two days of low-volume test traffic with no anomalies means we're
  ready. We don't need a per-host post-deploy verification."
- "Rollback is fast — the technician can rsync the prior binary back
  in minutes if anything looks wrong on the console."
- "We have not added an automated deploy validation step because the
  manual checklist has worked for years."

### Decision under review

The desk plans to go live with RLP at the 2012-08-01 09:30 ET open.
The pre-launch review meeting on the morning of 2012-07-31 asks for
any concerns about the production posture, the deploy procedure, or
the configuration of the new feature gate. The infrastructure lead
has signed off on the manual checklist. The risk team has signed
off on the RLP code path itself.
""",
        prompt=(
            "Review the production posture and the deploy procedure that "
            "Knight Capital is about to take live on 2012-08-01. Identify "
            "the most serious risks, and for each risk explain what "
            "evidence the team has that the risk is mitigated vs. only "
            "assumed-mitigated."
        ),
        ground_truth=[
            # Drawn from the SEC Order against Knight Capital
            # (Release No. 70694, 2013-10-16) and from the public
            # engineering analyses of the 2012-08-01 incident.
            "Manual rsync-to-8-hosts deploy procedure with no automated verification that the binary on host 8 matches the binary on hosts 1–7 — exactly the failure that occurred (host 8 was missed and continued running the old code).",
            "Repurposing the dormant `Power Peg` flag to gate the new RLP behaviour: once the flag is enabled in production config, the old hosts that still carry the dormant Power Peg code path begin executing that legacy path with the new flag value.",
            "Dead-code retention without explicit sunset: the Power Peg path was 'dormant' but had never been deleted, so reusing the flag silently re-activated it.",
            "Pre-deploy validation runs only on a single shared staging host with replayed market data; staging does not exercise the 8-host parallel topology, so the per-host divergence cannot surface in staging.",
            "Rollback procedure depends on the technician detecting the issue from a monitoring console under live-market conditions — no automated kill-switch or position-limit circuit breaker that fires before catastrophic losses accumulate.",
            "Low-volume tests on 2012-07-30 and 2012-07-31 are treated as sufficient validation despite not exercising the same code path the open-market RLP would trigger.",
            "Manual deploy checklist with no two-person sign-off on the 'all 8 hosts updated' line — the checklist captures intent, not verified state.",
            "Infrastructure and risk sign-off treat the RLP code path and the deploy procedure as independent reviews; no review covers the joint risk of 'new code + reused flag + manual deploy'.",
            "Team narrative explicitly defends the absence of automated validation by appealing to past success of the manual procedure — a survivorship-bias frame that becomes load-bearing as soon as the procedure is asked to handle a novel failure mode.",
        ],
        domain="external_postmortem",
    ),
]
