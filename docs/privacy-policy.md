# Privacy Policy — Ploidy MCP Server

> **Status: pre-legal-review draft.** Structurally aligned with
> GDPR (Art. 13/14), CCPA/CPRA, Korean PIPA, and the Claude.ai
> Connectors Directory submission requirements. Specific wording,
> jurisdictional thresholds, and enforceability must be validated
> by qualified counsel before publication.

**Effective date: 2026-04-23**  ·  **Version: 1.0-draft**

---

## 0. Scope

This policy covers:

- The **upstream open-source Ploidy MCP server** (the software).
- A **specific deployment** run by the maintainer at the URL
  listed in [`directory-submission.md`](directory-submission.md)
  once published.

Third-party deployments of the same software are operated under
those operators' own privacy notices; this document describes the
software's data flows, not any particular operator's practices.

## 1. Controller identity (GDPR Art. 13)

- **Controller**: the maintainer listed in `pyproject.toml`
  (`heznpc`).
- **Contact**: see [`SECURITY.md`](../SECURITY.md) for security
  incidents; general privacy enquiries via the repository's GitHub
  Issues with the `privacy` label, or the email listed in the
  maintainer's Zenodo record.
- **Representative / DPO**: a Data Protection Officer has **not**
  been designated. The service's scale (pre-commercial research
  tool) is below mandatory-DPO thresholds in GDPR Art. 37, PIPA,
  and LGPD. This is re-evaluated on each material change.

## 2. Data we collect and store

Persisted locally in a SQLite database (path `PLOIDY_DB_PATH`,
default `~/.ploidy/ploidy.db`, created with `0o700` owner-only
permissions):

| Category | Field(s) | Source | Purpose | Legal basis (GDPR) |
|---|---|---|---|---|
| **Debate content** | `debates.prompt`, `sessions.context_documents`, `sessions.compressed_summary` (Semi-Fresh derived summary), `messages.content` (positions + challenges), `convergence.synthesis`, `convergence.points_json`, `convergence.meta_analysis` | Submitted by you | Execute the debate; serve it back from `ploidy-history` / dashboard | Contract performance (Art. 6(1)(b)) |
| **Debate metadata** | `debates.id`, `debates.status`, `debates.config_json`, `debates.created_at/updated_at`, `sessions.role/delivery_mode/metadata_json/model/effort` | Generated | Routing, diagnostics, reproducibility | Legitimate interests (Art. 6(1)(f)) |
| **Tenant identifier** | `debates.owner_id` — resolves to the OAuth `client_id` or bearer-token tenant label | OAuth flow / bearer map | Authorise access to your own debates; multi-tenant isolation | Contract (Art. 6(1)(b)) |
| **OAuth state** (only when `PLOIDY_AUTH_MODE=oauth`) | `oauth_clients` (client_id, redirect_uris, grant_types, client_name), `oauth_codes` (opaque 5-min single-use), `oauth_tokens` (opaque random strings, 1 h access / rotated refresh) | OAuth registration | Implement RFC 6749 authorisation server | Contract (Art. 6(1)(b)) |
| **Aggregate metrics** | Prometheus counters (e.g. `ploidy_debate_started_total{tenant=...}`) | Derived | Operations / capacity planning | Legitimate interests |

Outside the SQLite DB, the server process may emit stdout logs
that contain request paths, status codes, and — via the ASGI
framework's defaults — client IP addresses. These logs are not
written to the database by Ploidy. Operators who configure log
shipping are separate controllers for those logs.

## 3. Data we do NOT collect

- Names, email addresses, phone numbers, physical addresses, or
  billing information.
- Demographic, biometric, precise geolocation, or **health data**
  of any kind.
- Data about children under 13 (COPPA) / 14 (Korean PIPA) — the
  service is not directed at children.
- Model-provider credentials. `PLOIDY_API_KEY` / `ANTHROPIC_API_KEY`
  live in process environment variables and are never written to
  the database by Ploidy.
- Behavioural-advertising signals. Ploidy uses no analytics, ad
  networks, cookies, fingerprinting, or cross-site trackers.

## 4. Third-party data flows

Ploidy forwards the text you submit to one LLM provider chosen by
the operator via `PLOIDY_API_BASE_URL`. By default this is
Anthropic's OpenAI-compatible endpoint at
`https://api.anthropic.com/v1/openai`.

Outbound data to the provider: the debate prompt, context
documents, and system-prompt metadata necessary to elicit a
response. The provider's data policy governs that text once it
leaves Ploidy — most notably Anthropic's
[commercial terms](https://www.anthropic.com/legal/commercial-terms)
and [privacy policy](https://www.anthropic.com/legal/privacy).

Ploidy does not share, sell, or rent personal information to any
other third party. There are no advertising partners, data
brokers, or analytics processors.

## 5. International transfers (GDPR Art. 44-50)

The default provider endpoint is hosted in the United States. If
you are in the EEA, UK, or another jurisdiction with
cross-border-transfer rules, data you submit is transferred to
the US. Anthropic publishes Standard Contractual Clauses for EU
customers; confirm your own eligibility before use. The operator
may point `PLOIDY_API_BASE_URL` at a regional endpoint if one
becomes available.

For Korean users (PIPA Art. 28-8), the prompt and context you
submit are transferred to the model provider identified above.
Using the service with the default configuration constitutes
consent to this transfer for the purpose of debate execution.
If this is unacceptable, use a deployment whose operator has
configured a Korea-resident endpoint.

## 6. Retention

| Data | Default retention |
|---|---|
| Debates (complete / cancelled) | Kept indefinitely until the user or operator deletes them, or `PLOIDY_RETENTION_DAYS` (default 0 = disabled) triggers automatic purge |
| Active / paused debates | Never purged by retention (until completed / cancelled) |
| OAuth authorisation codes | 5 minutes or one use, whichever first |
| OAuth access tokens | 1 hour |
| OAuth refresh tokens | Rotated on each use; revoked immediately on explicit `/revoke` |
| Prometheus counters | In-memory; reset on server restart |

Deletion hooks:

- `ploidy-history delete <id>` (CLI, planned) / `debate_delete` MCP tool — single debate.
- Deleting `PLOIDY_DB_PATH` — all Ploidy data.
- OAuth revocation endpoint — specific token.

## 7. Your rights

Rights apply whether you are in the EEA (GDPR Art. 15-22), the UK
(UK GDPR), California (CCPA/CPRA), Korea (PIPA Art. 35-37, 39),
Brazil (LGPD Art. 18), or another jurisdiction that grants
equivalent rights.

| Right | How to exercise |
|---|---|
| **Access / confirm processing** | `ploidy-history show <id>` for a self-hosted install; for a hosted deployment, contact the operator (Section 1) |
| **Correction** | Ploidy stores debate outputs as a record of what the model produced; there is no "correction" of model output. You may delete and re-run. For OAuth `client_name` or redirect URIs, re-register the client |
| **Deletion / erasure** | Single debate via `debate_delete`; full wipe via deleting the DB file |
| **Restriction of processing** | Revoke your OAuth tokens via `/revoke`; stop submitting new debates |
| **Portability** | The SQLite database is a standard file any SQLite client can read |
| **Objection (GDPR Art. 21)** | Email the controller; we will stop processing your tenant's data for legitimate-interest purposes on request |
| **Automated decision-making (GDPR Art. 22)** | Ploidy assists human decisions; it does not make legally- or similarly-significant automated decisions on your behalf |
| **California "Do Not Sell / Share"** | Not applicable — Ploidy does not sell or share personal information for cross-contextual behavioural advertising |
| **Right to complain** | EEA: your local supervisory authority. UK: ICO. Korea: Personal Information Protection Commission. California: Attorney General |

For hosted deployments, operators must provide a request channel
for these rights. Upstream deployments respond within 30 days
(GDPR Art. 12(3)) where feasible.

## 8. Security

- Default bearer-token auth (`PLOIDY_TOKENS`) uses
  `hmac.compare_digest` for constant-time comparison.
- OAuth 2.0 mode (`PLOIDY_AUTH_MODE=oauth`) enforces PKCE S256,
  single-use authorisation codes, and refresh-token rotation.
- Database file is created with `0o700` (owner-only) permissions.
- Per-tenant rate limiting is available (`PLOIDY_RATE_CAPACITY`,
  `PLOIDY_RATE_PER_SEC`).
- Access tokens are opaque random 256-bit secrets stored in the
  access-controlled SQLite DB; they are neither hashed nor signed
  — revocation is the defence.

No software is perfectly secure. Report vulnerabilities privately
via [`SECURITY.md`](../SECURITY.md).

## 9. Children

Ploidy is not directed at children under 13 (COPPA) / 14 (Korean
PIPA Art. 22-2) / 16 (GDPR Art. 8 default). The service does not
knowingly collect personal information from children. Operators
who discover such collection must delete it on notification.

## 10. Regional notices

### 10.1 California (CCPA / CPRA)

- **Categories collected**: Identifiers (OAuth `client_id`,
  debate ids), Internet / electronic network activity (prompt
  text, generated outputs), Inferences (convergence points,
  meta-analysis).
- **Sources**: Directly from you.
- **Business / commercial purposes** (CCPA §1798.140): providing
  the service you requested, maintaining security, debugging.
- **Sharing / selling**: Ploidy does **not** sell personal
  information and does not share it for cross-contextual
  behavioural advertising. No "Do Not Sell or Share My Personal
  Information" link is required because the activity that would
  trigger it does not occur.
- **Right to correct**: exercised by deleting and re-running the
  debate; OAuth client metadata is replaced via re-registration.
- **Right to limit sensitive personal information**: Ploidy does
  not collect sensitive personal information as defined in
  §1798.140(ae).

### 10.2 European Economic Area / UK (GDPR / UK GDPR)

- **Legal bases** per processing are listed in Section 2.
- **International transfers**: see Section 5.
- **No automated decision-making** under Art. 22 as defined in
  Section 7.
- **Supervisory authority**: contact your member-state DPA (UK:
  ICO). Article-6-legitimate-interests assessment available on
  request.

### 10.3 Korea (개인정보보호법 / PIPA)

- **Collection purpose / retention / items collected** are
  itemised in Sections 2, 3, and 6.
- **Cross-border transfer**: Section 5. Anthropic's OpenAI-
  compatible endpoint in the United States is the default.
- **Data subject rights** (Art. 35-37, 39): enumerated in
  Section 7. Contact via the channel in Section 1.
- **DPO (개인정보보호책임자)**: not designated while the service
  remains below mandatory-appointment thresholds. Maintainer
  handles privacy enquiries in the interim.
- **Korean-language notice**: a translated version of this policy
  will be published at `docs/ko/privacy-policy.md` before Korean
  users are directed to the service; using the English version in
  the interim for a Korean audience is a documented gap pending
  translation.

### 10.4 Brazil (LGPD)

A Portuguese translation is not currently maintained. LGPD Art.
18 rights mirror those in Section 7; exercise via the Section 1
channel.

### 10.5 Other jurisdictions

The rights and bases in Sections 2-7 are written to the common
denominator of the above regimes. If your jurisdiction (e.g.
India DPDP Act, China PIPL, Canada PIPEDA) grants additional
rights, we honour them on reasonable request per Section 7.

## 11. Children / sensitive-category safeguards

Ploidy performs no profiling for behavioural advertising, no
biometric inference, no health diagnosis, and no automated legal
or medical advice. Submitting medical, legal, or financial
content is at the user's own risk and outside the service's
intended scope (see Terms of Service §3).

## 12. Changes to this policy

Material changes are committed to this file in the repository,
making the full history auditable via git. The effective date
above updates on each material change, and the version number
increments.

## 13. Jurisdiction of interpretation

This policy is interpreted under the laws of the Republic of
Korea for the upstream deployment. Regional regulatory
authorities retain statutory jurisdiction over their residents
regardless.

---

*This document is a pre-legal-review draft. Please do not rely
on it as definitive compliance advice without independent
verification.*
