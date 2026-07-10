# Ploidy

**Context-asymmetric structured debate for difficult decisions.**

[![CI](https://github.com/heznpc/PLOIDY/actions/workflows/ci.yml/badge.svg)](https://github.com/heznpc/PLOIDY/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-heznpc.github.io%2FPLOIDY-blue)](https://heznpc.github.io/PLOIDY/)
[![PyPI](https://img.shields.io/pypi/v/ploidy)](https://pypi.org/project/ploidy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Ploidy gives one side of a debate project context and keeps the other
side fresh, then records positions before either side can anchor on the
other. It ships as a Python 3.11+ MCP server with SQLite persistence.

## Install

```bash
pip install ploidy
```

Add the API extra only when the server itself will generate an automatic
debate:

```bash
pip install "ploidy[api]"
```

## Recommended local setup: stdio

`stdio` is the default transport. One MCP client starts one server on
demand, so there is no port or background process to manage.

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

The primary tool is `debate`:

- `mode="solo"`: the caller supplies independently generated Deep and
  Fresh positions. No external model API is required.
- `mode="auto"`: the server generates both sides through an
  OpenAI-compatible API. Non-empty `context_documents` are required so
  the Deep and Fresh sides are actually asymmetric.

Example auto call:

```python
await debate(
    prompt="Should we split the ingestion service?",
    mode="auto",
    context_documents=["Current topology, incident history, and constraints…"],
    context_sources=["architecture-notes"],
)
```

Configure the API backend before using auto mode:

```bash
export PLOIDY_API_BASE_URL=https://api.openai.com/v1
export PLOIDY_API_KEY=...
export PLOIDY_API_MODEL=your-model
```

## Shared server: Streamable HTTP

Use HTTP when multiple MCP clients must share one debate or when Ploidy
is deployed as a service:

```bash
PLOIDY_TRANSPORT=streamable-http python3 -m ploidy
export PLOIDY_URL=http://127.0.0.1:8765
```

Configure each client with `${PLOIDY_URL}/mcp` (substitute the value;
JSON does not expand shell variables):

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

`PLOIDY_URL` is the base URL used by `ploidy-ask` and other HTTP
clients. The MCP endpoint is `/mcp`, and the live HTTP/SSE endpoint is
`/v1/debate/stream`.

## MCP tools

Ploidy 0.4.0 exposes exactly 13 tools. New integrations should use the
unified `debate` tool. The other 12 remain available for explicit
two-client, phase-by-phase, history, cancellation, and HITL workflows.

| Tool | Purpose |
|---|---|
| `debate` | Unified `auto` or `solo` debate |
| `debate_start` | Create a Deep session |
| `debate_join` | Join as Fresh or Semi-Fresh |
| `debate_position` | Submit an independent position |
| `debate_challenge` | Submit a semantic challenge |
| `debate_converge` | Produce the convergence result |
| `debate_cancel` | Cancel an active debate |
| `debate_delete` | Permanently delete a debate |
| `debate_status` | Read current state |
| `debate_history` | List visible debate history |
| `debate_solo` | Legacy alias for caller-supplied debate |
| `debate_auto` | Legacy alias for API-generated debate |
| `debate_review` | Approve, override, or reject a paused auto debate |

## Service configuration

Common environment variables:

```bash
PLOIDY_TRANSPORT=stdio             # stdio (default) or streamable-http
PLOIDY_PORT=8765
PLOIDY_DB_PATH=~/.ploidy/ploidy.db
PLOIDY_MAX_CONTEXT_TOKENS=20000    # recommended for hosted auto mode
PLOIDY_RATE_CAPACITY=20
PLOIDY_RATE_PER_SEC=1
PLOIDY_RETENTION_DAYS=30
```

Authentication modes and their limits:

- Admission-controlled self-hosting: `PLOIDY_AUTH_MODE=bearer` with
  `PLOIDY_TOKENS='{"token":"tenant"}'`.
- OAuth interoperability: `PLOIDY_AUTH_MODE=oauth` and an exact public
  `PLOIDY_OAUTH_ISSUER`; v0.4.0 auto-approves clients and therefore is
  not user login or public admission control.
- Migration only: `PLOIDY_AUTH_MODE=both` adds the static-token fallback.

Bearer mode without a configured token is intentionally unauthenticated
and is suitable only for loopback development. Public services need a
private ingress/gateway or controlled static tokens until OAuth gains
resource-owner login and consent.

## Container

The published image is immutable by release version:

```bash
docker run --rm \
  -p 127.0.0.1:8765:8765 \
  -v ploidy-data:/data \
  ghcr.io/heznpc/ploidy:0.4.0
```

Or run the checked-in Compose configuration:

```bash
docker compose up --build
```

The image defaults to `streamable-http` and contains the API,
dashboard, metrics, Redis, and CLI runtime extras.

## Documentation

- [Getting started](https://heznpc.github.io/PLOIDY/getting-started/)
- [API reference](https://heznpc.github.io/PLOIDY/api-reference/)
- [v0.4 migration](https://heznpc.github.io/PLOIDY/v0.4-migration/)
- [Custom Connector](https://heznpc.github.io/PLOIDY/custom-connector/)
- [Deployment](deploy/README.md)

## License

MIT
