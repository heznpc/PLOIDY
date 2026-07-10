# Getting started

Ploidy requires Python 3.11 or newer and an MCP-compatible client.

## Install

```bash
pip install ploidy==0.4.0
```

For server-generated auto debates, install the API extra:

```bash
pip install "ploidy[api]==0.4.0"
```

## Local MCP client: stdio

`stdio` is the default transport. Add this server entry to your MCP
client; the client will start and stop Ploidy itself.

```json
{
  "mcpServers": {
    "ploidy": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "ploidy"]
    }
  }
}
```

No HTTP server is started in this mode.

## First debate without an API key

Ask the MCP client to create two analyses independently:

1. A Deep analysis that can inspect the project.
2. A Fresh analysis from a new subagent that sees only the decision
   prompt.

Then call the unified tool:

```python
await debate(
    prompt="Should this repository split the ingestion service?",
    mode="solo",
    deep_position="…analysis grounded in this repository…",
    fresh_position="…independent analysis that saw only the prompt…",
    deep_challenge="…optional critique of the Fresh position…",
    fresh_challenge="…optional critique of the Deep position…",
)
```

Ploidy persists the transcript and returns `rendered_markdown` plus the
structured convergence result. The server does not make the two caller-
supplied positions independent; the caller must create the Fresh side in
a genuinely separate context.

## Auto debate

Auto mode uses an OpenAI-compatible backend:

```bash
export PLOIDY_API_BASE_URL=https://api.openai.com/v1
export PLOIDY_API_KEY=...
export PLOIDY_API_MODEL=your-model
```

Every auto debate requires non-empty `context_documents`. This is the
Deep-only evidence that creates the intervention; an auto call without it
is rejected rather than silently running two symmetric prompts.

```python
await debate(
    prompt="Should this repository split the ingestion service?",
    mode="auto",
    context_documents=[
        "Service topology…",
        "Recent incident and dependency constraints…",
    ],
    context_sources=["topology", "incident-review"],
    fresh_role="fresh",
    delivery_mode="none",
    deep_n=2,
    fresh_n=2,
)
```

For a Fresh side, `delivery_mode` must be `none`. A Semi-Fresh side uses
`passive`, `active`, or `selective` delivery.

## Shared HTTP server

Two independent MCP clients need one shared Streamable HTTP server:

```bash
PLOIDY_TRANSPORT=streamable-http python3 -m ploidy
export PLOIDY_URL=http://127.0.0.1:8765
```

`PLOIDY_URL` is the base URL understood by Ploidy's HTTP client commands.
Use `${PLOIDY_URL}/mcp` as the MCP URL after substituting its value:

```json
{
  "mcpServers": {
    "ploidy": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

The legacy phase tools support the original two-client flow:

1. Deep calls `debate_start` with the prompt and Deep-only
   `context_documents`.
2. Fresh calls `debate_join` with the returned `debate_id`.
3. Every seat submits `debate_position`; no position is disclosed until
   the position barrier is complete.
4. Every seat submits its own `debate_challenge`.
5. One client calls `debate_converge`.

## Authentication

Loopback development may run without authentication. Do not expose that
configuration publicly.

Static bearer tokens for self-hosting:

```bash
export PLOIDY_AUTH_MODE=bearer
export PLOIDY_TOKENS='{"replace-with-random-token":"tenant-a"}'
```

OAuth protocol interoperability in a controlled environment:

```bash
export PLOIDY_AUTH_MODE=oauth
export PLOIDY_OAUTH_ISSUER=https://ploidy.example.com
```

The issuer must be the exact public HTTPS origin, without `/mcp`.
In 0.4.0, DCR clients are auto-approved without resource-owner login or
consent, so OAuth is not public admission control. Use an external
gateway/private ingress or static bearer tokens where admission matters.
`PLOIDY_AUTH_MODE=both` is reserved for a transition that must accept
both protocol OAuth and an existing `PLOIDY_TOKENS` map.

## Hosted-service safety limits

The repository's container and deployment examples enable bounded
defaults. When running from the Python package directly, set them
explicitly:

| Variable | Hosted example | Purpose |
|---|---:|---|
| `PLOIDY_MAX_CONTEXT_TOKENS` | `20000` | Approximate combined Deep-context ceiling |
| `PLOIDY_MAX_CONTEXT_DOCS` | `10` | Maximum document count |
| `PLOIDY_RATE_CAPACITY` | `20` | Per-tenant burst allowance |
| `PLOIDY_RATE_PER_SEC` | `1` | Per-tenant sustained request rate |
| `PLOIDY_RETENTION_DAYS` | `30` | Purge old completed/cancelled debates |

## Container

```bash
docker compose up --build
```

The Compose service binds only to `127.0.0.1` by default. For a public
deployment, terminate TLS and configure a private gateway or controlled
bearer authentication before changing that binding.

## Next steps

- [API reference](api-reference.md)
- [v0.4 migration](v0.4-migration.md)
- [Custom Connector](custom-connector.md)
- [Deployment recipes](https://github.com/heznpc/PLOIDY/blob/main/deploy/README.md)
