# Deploy Ploidy on Fly.io

This recipe runs the immutable
`ghcr.io/heznpc/ploidy:0.4.0` image over HTTPS with controlled static
bearer admission.

## Prepare and deploy

Install `flyctl`, sign in, and replace `ploidy-demo` in `fly.toml` with
a globally unique app name. Then run from the repository root:

```bash
flyctl launch --no-deploy --copy-config --config deploy/fly/fly.toml

export PLOIDY_API_TOKEN=$(openssl rand -hex 32)
flyctl secrets set \
  PLOIDY_TOKENS="{\"$PLOIDY_API_TOKEN\":\"tenant-a\"}" \
  --config deploy/fly/fly.toml

flyctl deploy --config deploy/fly/fly.toml
export PLOIDY_URL=https://your-unique-app.fly.dev
```

Do not deploy the bearer configuration without `PLOIDY_TOKENS`; that is
an intentionally unauthenticated local-development mode.

The checked-in config sets:

- `PLOIDY_TRANSPORT=streamable-http`
- `PLOIDY_AUTH_MODE=bearer`
- a 20,000-token approximate context ceiling
- a 20-request burst and 1 request/second sustained rate
- 30-day completed/cancelled debate retention

The SQLite database is stored on the `ploidy_data` volume.

## Optional auto-mode backend

Auto mode requires an OpenAI-compatible backend. Store credentials as
Fly secrets, never in `fly.toml`:

```bash
flyctl secrets set \
  PLOIDY_API_BASE_URL="https://api.openai.com/v1" \
  PLOIDY_API_KEY="..." \
  PLOIDY_API_MODEL="your-model" \
  --config deploy/fly/fly.toml
```

Every auto request must also send non-empty `context_documents`.

## Verify and register

```bash
curl --fail "$PLOIDY_URL/healthz"
```

Register `${PLOIDY_URL}/mcp` as a Custom Connector with
`$PLOIDY_API_TOKEN` as bearer authentication. See the
[connector guide](../../docs/custom-connector.md).

## OAuth interoperability evaluation

Ploidy 0.4.0 can boot an OAuth Authorization Server and complete DCR,
PKCE, and token flows:

```bash
flyctl secrets set \
  PLOIDY_AUTH_MODE=oauth \
  PLOIDY_OAUTH_ISSUER="$PLOIDY_URL" \
  --config deploy/fly/fly.toml
```

This is not production admission control. The authorization endpoint
auto-approves clients without resource-owner login or consent, and an
attacker can mint new DCR client IDs to evade per-client rate buckets.
Keep OAuth mode behind a private ingress/gateway. It is not ready for a
public connector directory submission.

## Operations

- Logs: `flyctl logs --config deploy/fly/fly.toml`
- Health: `GET ${PLOIDY_URL}/healthz`
- MCP: `${PLOIDY_URL}/mcp`
- Live SSE: `POST ${PLOIDY_URL}/v1/debate/stream`
- Metrics: `GET ${PLOIDY_URL}/metrics`; restrict this route to trusted
  monitoring ingress.
- Backups: snapshot the `ploidy_data` volume on an operator-defined
  schedule.

Keep one running machine: the service uses a local SQLite database and
does not support multiple writers across replicas.
