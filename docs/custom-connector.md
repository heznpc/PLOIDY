# Ploidy as a Custom Connector

A Custom Connector needs a publicly reachable Streamable HTTP server.
Local `stdio` configuration is not visible to a hosted chat client.

!!! danger "OAuth in 0.4.0 is not admission control"

    Ploidy 0.4.0 implements discovery, DCR, PKCE, token issuance, and
    tenant scoping, but its authorization endpoint auto-approves every
    registered client. There is no resource-owner login, consent screen,
    or operator allowlist. New client IDs can also bypass per-client rate
    buckets. OAuth mode is suitable for protocol interoperability tests,
    not unrestricted public access or a directory submission.

    Put the service behind a private network or admission gateway, or use
    static bearer tokens when access must be controlled.

## Admission-controlled deployment

Set a canonical URL for clients and configure a random tenant token:

```bash
export PLOIDY_URL=https://ploidy.example.com
export PLOIDY_TRANSPORT=streamable-http
export PLOIDY_AUTH_MODE=bearer
export PLOIDY_TOKENS='{"replace-with-random-token":"tenant-a"}'
```

Supported deployment recipes:

- [Fly.io](https://github.com/heznpc/PLOIDY/blob/main/deploy/fly/README.md)
- [Helm](https://github.com/heznpc/PLOIDY/tree/main/deploy/helm/ploidy)
- [Plain Kubernetes](https://github.com/heznpc/PLOIDY/blob/main/deploy/kubernetes/ploidy.yaml)

They use the immutable `0.4.0` image tag and bounded context, rate, and
retention defaults. A gateway remains responsible for TLS, network
admission, and abuse controls beyond the service's token map.

## Register with static bearer auth

In the connector settings, add:

| Field | Value |
|---|---|
| Name | `Ploidy` |
| URL | `${PLOIDY_URL}/mcp` after substituting the public origin |
| Authentication | Bearer token from `PLOIDY_TOKENS` |

Ploidy exposes 13 tools. For a simple surface, enable only `debate` in
clients that provide per-tool toggles. The remaining 12 tools are the
0.4.0 compatibility surface; there is no supported server flag that
hides them.

## OAuth interoperability evaluation

To exercise discovery, DCR, PKCE, token issuance, and OAuth tenant
ownership in a controlled environment:

```bash
export PLOIDY_AUTH_MODE=oauth
export PLOIDY_OAUTH_ISSUER=$PLOIDY_URL
```

The issuer must be the exact external HTTPS origin without `/mcp`.
`PLOIDY_AUTH_MODE=both` adds the static-token fallback during a bounded
migration. Neither mode adds resource-owner authentication: an external
gateway or a future consent/login implementation is still required for
public admission control.

## First call

Auto mode must include Deep-only context:

> Use Ploidy `debate` in auto mode to decide whether to split the
> ingestion service. Pass the architecture summary and recent incident
> constraints as `context_documents`, with matching
> `context_sources`.

An auto request without non-empty `context_documents` is rejected. The
completed response includes `rendered_markdown`, structured points, the
convergence synthesis, and a context provenance manifest.

## Live HTTP/SSE clients

Custom Connector tool calls complete as one MCP response. A separate
web or bot client can show phase progress from:

```text
POST ${PLOIDY_URL}/v1/debate/stream
```

```bash
curl -N "$PLOIDY_URL/v1/debate/stream" \
  -H "Authorization: Bearer $PLOIDY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data '{
    "prompt": "Should we split the ingestion service?",
    "context_documents": ["Architecture and incident constraints…"],
    "context_sources": ["architecture-review"]
  }'
```

Missing or invalid bearer credentials return `401`. If the client
disconnects, the running task is cancelled and active debate state is
cleaned up.

## Pre-launch checklist

- [ ] A private ingress/gateway or static bearer token controls admission.
- [ ] OAuth is labelled protocol-only until owner login/consent exists.
- [ ] `PLOIDY_MAX_CONTEXT_TOKENS` is bounded.
- [ ] Rate limiting also exists at the gateway; DCR client IDs are not a
      durable anti-abuse identity.
- [ ] `PLOIDY_RETENTION_DAYS` is non-zero.
- [ ] `/metrics` is limited to trusted monitoring ingress.
- [ ] The dashboard binds to loopback or has `PLOIDY_DASH_TOKEN`.
- [ ] SQLite data is backed up and the service remains single-replica.
