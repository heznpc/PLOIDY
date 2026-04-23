# Claude.ai Connectors Directory — submission checklist

Tracking doc for the directory submission path described in
[planning/oauth-integration.md](../planning/oauth-integration.md).
The four preceding OAuth slices shipped the code and tests; this
file captures the artefacts Anthropic's reviewers need alongside
the running server.

Source of truth for the submission process:
[claude.com/docs/connectors/building/submission](https://claude.com/docs/connectors/building/submission).

## Artefacts

| Item | Status | Location / note |
|---|---|---|
| Public HTTPS endpoint | ⏳ pending deploy | Fly.io recipe in [`deploy/fly/README.md`](../deploy/fly/README.md) — target URL TBD |
| OAuth 2.0 Authorization Server | ✅ shipped | `PLOIDY_AUTH_MODE=oauth`; discovery at `/.well-known/oauth-authorization-server` |
| PKCE S256 | ✅ shipped | Advertised in discovery; enforced by the SDK + provider |
| Dynamic Client Registration | ✅ shipped | `/register` route |
| Redirect URI allowlist (claude.ai / claude.com) | ✅ shipped | Each registered client may list either origin; the SDK validates on `/authorize` |
| Privacy policy (global baseline) | ✅ drafted | [`privacy-policy.md`](privacy-policy.md) — GDPR / CCPA / PIPA / LGPD structure; **legal review required before publishing** |
| Terms of service (global baseline) | ✅ drafted | [`terms-of-service.md`](terms-of-service.md) — governing law + consumer protections + indemnification; **legal review required before publishing** |
| Security reporting channel | ✅ [`SECURITY.md`](../SECURITY.md) | GitHub Security Advisories + email fallback |
| Citation metadata | ✅ [`CITATION.cff`](../CITATION.cff) + `.zenodo.json` | Zenodo DOI placeholder pending release |
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

Create a dedicated OAuth client with label `anthropic-review` and
share the credentials via Anthropic's reviewer-support channel.
Procedure once the server is deployed:

```sh
curl -X POST https://<deploy-url>/register \
  -H 'content-type: application/json' \
  -d '{
        "client_name": "Anthropic Review",
        "redirect_uris": [
          "https://claude.ai/api/mcp/auth_callback",
          "https://claude.com/api/mcp/auth_callback"
        ]
      }'
```

Response contains the `client_id`; include it in the submission
form. Rotate on approval.

## Pre-submission self-check

Before opening the submission form, run:

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
