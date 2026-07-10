# Claude.ai Connectors Directory — HOLD

!!! danger "Not directory-ready in v0.4.0"

    OAuth discovery, DCR, PKCE, token issuance, and tenant scoping boot
    successfully, but authorization auto-approves every client. There is
    no resource-owner login, consent, or operator admission decision.
    New DCR clients can also evade per-client rate buckets. Do not submit
    v0.4.0 to a public connector directory. Add real owner authentication
    and consent, or place a reviewer-approved admission gateway in front,
    then repeat the security review.

Tracking doc for the directory submission path described in
[planning/oauth-integration.md](https://github.com/heznpc/PLOIDY/blob/main/planning/oauth-integration.md).
The four preceding OAuth slices shipped the code and tests; this
file captures the artefacts Anthropic's reviewers need alongside
the running server.

Source of truth for the submission process:
[claude.com/docs/connectors/building/submission](https://claude.com/docs/connectors/building/submission).

## Artefacts

| Item | Status | Location / note |
|---|---|---|
| Public HTTPS endpoint | ⏳ pending deploy | Fly.io recipe in [`deploy/fly/README.md`](https://github.com/heznpc/PLOIDY/blob/main/deploy/fly/README.md) — target URL TBD |
| OAuth 2.0 protocol flow | ⚠️ protocol-only | Boots and issues tokens, but auto-approval means it is not user authentication or admission control |
| PKCE S256 | ✅ shipped | Advertised in discovery; enforced by the SDK + provider |
| Dynamic Client Registration | ⚠️ unrestricted | `/register` auto-admits clients; sybil/rate-limit bypass remains open |
| Redirect URI allowlist (claude.ai / claude.com) | ✅ shipped | Each registered client may list either origin; the SDK validates on `/authorize` |
| Privacy policy (global baseline) | ✅ drafted | [`privacy-policy.md`](privacy-policy.md) — GDPR / CCPA / PIPA / LGPD structure; **legal review required before publishing** |
| Terms of service (global baseline) | ✅ drafted | [`terms-of-service.md`](terms-of-service.md) — governing law + consumer protections + indemnification; **legal review required before publishing** |
| Security reporting channel | ✅ [`SECURITY.md`](https://github.com/heznpc/PLOIDY/blob/main/SECURITY.md) | GitHub Security Advisories |
| Citation metadata | ✅ [`CITATION.cff`](https://github.com/heznpc/PLOIDY/blob/main/CITATION.cff) | Release metadata |
| Korean translation (PIPA) | ⏳ pending | Target: `docs/ko/privacy-policy.md` + `docs/ko/terms-of-service.md` before active Korean marketing |
| Logo (SVG + PNG) | ⏳ pending | Place in `docs/assets/logo.{svg,png}` |
| Favicon | ⏳ pending | `docs/assets/favicon.ico` |
| Screenshots (3-5) | ⏳ pending | Debate flow / dashboard / history — `docs/assets/screenshots/` |
| Test account for Anthropic reviewers | ⏳ pending | See "Review account" section below |
| Connector description (≤200 words) | ⏳ pending | Draft in this doc, copy into submission form |
| Tool list with annotations | 🟡 partial | The `debate` tool is annotated; verify descriptions read well out of context |
| Support channel | ⏳ pending | Choose: GitHub issues / dedicated email / Discord |
| GA date | ⏳ pending | Set once a publicly-reachable endpoint is stable |

## Submission draft

### Name

**Ploidy**

### One-line description

Cross-session multi-agent debate MCP server — same model,
different context depths, better decisions.

### Longer description (≤200 words; draft, needs polish)

Ploidy is a structured-debate protocol implemented as an MCP
server. When you face a design, migration, hiring, or prioritisation
decision, Ploidy runs two or more sessions of the same LLM in
parallel: one session holds the full project context, another
starts from zero. They state positions independently, exchange
targeted challenges, and the server synthesises the result with
explicit confidence scoring and a categorical breakdown (agreement
/ productive disagreement / irreducible disagreement).

The research hypothesis — that *context asymmetry*, not agent
count, is what breaks the martingale curse of homogeneous multi-
agent debate — is documented in the accompanying paper
(`paper/main.tex`, Zenodo DOI pending).

Tools exposed include a one-shot `debate` call, history review
(`ploidy-history`), a live-progress web UI, and a growing set of
decision-stage slash commands (`/spike`, `/review-pr`,
`/architecture`, `/hiring`, ...).

### Categories

- Developer tools
- Research / analysis

### Review account

Blocked. Unrestricted DCR is not a review-account provisioning flow.
Create an operator-approved identity and revocation path before issuing
reviewer credentials.

## Pre-submission self-check

Before opening the submission form, run:

- [ ] Resource-owner login and consent or equivalent operator admission
      control exists; DCR alone does not satisfy this gate.
- [ ] Rate limits cannot be reset by minting a new DCR client ID.
- [ ] `curl https://<deploy-url>/.well-known/oauth-authorization-server` returns a 200 with all four endpoint URLs.
- [ ] `curl https://<deploy-url>/.well-known/oauth-protected-resource` returns a 200 with the issuer listed.
- [ ] `pytest tests/test_oauth_endpoints.py -q` passes against the deployed build.
- [ ] Privacy policy + TOS reviewed by a human who is not me.
- [ ] Screenshots do not contain internal data or PII.
- [ ] The `debate` tool description reads sensibly when shown alone in the Claude.ai tool picker.
- [ ] Rate limits are set (`PLOIDY_RATE_CAPACITY`, `PLOIDY_RATE_PER_SEC`) so one misbehaving user cannot DoS reviewers.
- [ ] A status page / uptime monitor is linked from the support channel.

## Open questions

1. **Hosting cost model**: Directory acceptance implies the server
   stays reachable. Budget for Fly.io / Cloudflare Workers costs
   under reviewer + early-user load.
2. **Commercial use clause**: current TOS is permissive. Decide
   before submission whether commercial users need a separate tier.
3. **Abuse response playbook**: documented runbook for revoking
   a tenant that sends prohibited content is a reviewer checklist
   item.
4. **Admission architecture**: decide whether owner login/consent lives
   in Ploidy or an external gateway before resuming submission work.
