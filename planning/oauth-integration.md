# OAuth 2.0 integration — design

Status: **design / not-yet-implemented**
Last updated: 2026-04-23

## Why

Today Ploidy's MCP server authenticates callers with a bearer token
pulled from `PLOIDY_TOKENS` (JSON `{token: tenant}`). That works for
the informal *Custom Connector* path — users paste a URL + bearer into
Claude.ai's "Add custom connector" UI. It does **not** work for the
**Connectors Directory** (the curated "verified" list).

Anthropic's submission guide
[claude.com/docs/connectors/building/submission](https://claude.com/docs/connectors/building/submission)
rejects bearer-token servers outright: directory entries must speak
OAuth 2.0 with PKCE and register redirect URIs for
`https://claude.ai/api/mcp/auth_callback` and the `claude.com`
equivalent. Landing in the directory is the single largest
distribution unlock the project has — it opens Ploidy to every
Claude.ai user one click instead of a config paste.

## Scope

**In scope for the first shippable slice:**

- Implement `OAuthAuthorizationServerProvider` (from
  `mcp.server.auth.provider`) against a SQLite-backed store.
- Wire FastMCP's `auth_server_provider=` kwarg alongside the existing
  `token_verifier=` so the server supports both auth modes during the
  transition.
- Expose the RFC 8414 discovery endpoint
  `/.well-known/oauth-authorization-server` and the RFC 7591
  Dynamic Client Registration endpoint.
- Implement Authorization Code + PKCE + Refresh Token grants.
- Allowlist the Claude.ai / Claude Desktop redirect URIs.
- Publish a privacy policy + terms of service (separate PR, needed
  for directory review).

**Out of scope for the first slice (deferred):**

- Multi-identity (we start with a single admin "register yourself"
  flow and layer real identity later).
- Third-party upstream identity (GitHub / Google OAuth) — the FastMCP
  docs describe the bridge pattern but we do not need it to ship v1.
- Consent UI beyond a minimal redirect page.
- Token revocation UI (the `revoke_token` hook ships but there is no
  user-facing "log out everywhere" page yet).

## Architecture

```
  ┌──────────────┐        ┌───────────────────────────────┐
  │  Claude.ai   │        │  Ploidy server                │
  │  (client)    │───1───▶│  /.well-known/oauth-...       │
  │              │◀──2────│    (metadata)                 │
  │              │───3───▶│  /authorize                   │
  │              │◀──4────│    (302 back with code)       │
  │              │───5───▶│  /token (code → access+refresh)│
  │              │◀──6────│                                │
  │              │───7───▶│  /mcp tool calls (Bearer)     │
  └──────────────┘        └───────────────────────────────┘
```

- **Discovery** (steps 1-2): FastMCP generates the metadata response
  from the provider; we only need to register the provider and routes.
- **/authorize** (3-4): consent page + code issuance. PKCE
  (`code_challenge`/`code_verifier`) stored against the code.
- **/token** (5-6): exchange code for access + refresh. Rotate refresh
  tokens per OAuth 2.1 guidance.
- **Tool calls** (7): FastMCP's `load_access_token` hook resolves the
  bearer we issued in step 6 back to an `AccessToken` with scopes.

## Persistence

New tables in the same SQLite DB (`PLOIDY_DB_PATH`) so operators get
one file to back up:

```sql
CREATE TABLE oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT,               -- hashed; nullable for public clients
    redirect_uris TEXT NOT NULL,      -- JSON array
    grant_types TEXT NOT NULL,        -- JSON array
    token_endpoint_auth_method TEXT,  -- 'none' for PKCE public clients
    client_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE oauth_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id),
    redirect_uri TEXT NOT NULL,
    scopes TEXT NOT NULL,              -- JSON array
    code_challenge TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL,  -- 'S256' required
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0    -- single-use guard
);

CREATE TABLE oauth_tokens (
    token TEXT PRIMARY KEY,             -- opaque random string
    kind TEXT NOT NULL,                 -- 'access' or 'refresh'
    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id),
    scopes TEXT NOT NULL,               -- JSON array
    expires_at TEXT,
    revoked INTEGER NOT NULL DEFAULT 0
);
```

A nightly task purges expired `oauth_codes` + revoked/expired
`oauth_tokens` alongside the existing retention job.

## Config surface

Two new env vars control the auth mode:

| var | default | meaning |
|---|---|---|
| `PLOIDY_AUTH_MODE` | `bearer` | `bearer` / `oauth` / `both` |
| `PLOIDY_OAUTH_ISSUER` | derived from `PLOIDY_PORT` | the `iss` URL |

`bearer` keeps today's behaviour. `oauth` mounts the OAuth routes and
rejects unsigned bearers. `both` accepts either (intended for the
transition window while existing users rotate off the bearer).

Redirect URI allowlist (hard-coded for directory compatibility):

```
https://claude.ai/api/mcp/auth_callback
https://claude.com/api/mcp/auth_callback
```

Operators can extend via `PLOIDY_OAUTH_EXTRA_REDIRECTS` (comma list)
for local dev.

## Shippable slices (PR plan)

1. **Schema + storage** — add the three tables + CRUD methods on
   `DebateStore`. No routes yet. Entirely additive.
2. **Provider implementation** — `src/ploidy/oauth.py` implements
   `OAuthAuthorizationServerProvider`. Code + refresh + access token
   lifecycle. Unit-tested with an in-memory store first.
3. **FastMCP wiring** — `PLOIDY_AUTH_MODE=oauth` activates the
   provider; `bearer` stays the default. Add the redirect allowlist.
4. **Discovery + DCR endpoints** — FastMCP generates these from the
   provider; we just ensure they are mounted under the right paths
   and verify with a conformance check.
5. **Retention + ops** — prune expired codes/tokens, add Prometheus
   counters, update `docs/custom-connector.md` to document both
   paths.
6. **Directory submission artefacts** — privacy policy, TOS, test
   account, screenshots, logo. Separate repo change.

Each slice is independently mergeable; only slice 6 touches
non-code artefacts.

## Testing strategy

- **Unit**: each provider method against an in-memory store (100%
  branch coverage on the OAuth module).
- **Contract**: a smoke test that issues an authorization code, posts
  it to `/token`, and uses the returned access token on a tool call —
  end-to-end without going through FastMCP's real HTTP stack.
- **Conformance**: the MCP SDK's auth tests if the upstream project
  ships any (`mcp.server.auth.tests`?); otherwise run the submission
  guide's self-check URLs manually during the directory review.
- **Mutation sanity**: flipping any PKCE check to a no-op must fail a
  test — PKCE is the single load-bearing defence against code
  interception.

## Open questions

1. **Consent screen**: do we serve our own HTML, or delegate to a
   third-party identity provider? First slice assumes a minimal
   self-hosted page that just shows the client_name + scopes and
   "Authorize". Acceptable for a research tool; revisit if we add
   real user accounts.
2. **DCR open vs. admin-gated**: the MCP spec implies open DCR. For
   abuse control we may gate it behind an admin token via the
   existing `PLOIDY_AUTH_TOKEN`. Decision: ship open, monitor, tighten
   if abuse materialises.
3. **Token storage**: opaque random strings vs. signed JWTs. Opaque
   is simpler and matches the existing bearer flow; JWT would let us
   skip the DB lookup on every tool call. Start opaque — optimise
   only if `load_access_token` shows up in profiling.
4. **Multi-tenancy**: current bearer flow maps token → tenant via the
   JSON config. OAuth needs the same mapping. Decision: each OAuth
   client is a tenant, `client_id` becomes the `AccessToken.client_id`
   exactly as today. No UI for provisioning new tenants in the first
   slice — `ploidy-admin register-client` CLI instead.

## Non-goals

- Full OIDC (no `id_token`, no UserInfo endpoint). The MCP spec only
  requires OAuth 2.0 Authorization Server; we ship that.
- Replacing the `PLOIDY_TOKENS` path for existing deployments — it
  stays supported via `PLOIDY_AUTH_MODE=bearer` indefinitely.
