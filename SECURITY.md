# Security Policy

## Supported versions

| Branch | Supported |
|---|---|
| `main` | ✅ latest commits |
| Tagged releases | Most recent two minor versions |
| Anything older | ❌ please upgrade |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security
vulnerabilities.**

Preferred channel — **GitHub Security Advisories**:

1. Go to <https://github.com/heznpc/ploidy-research/security/advisories/new>
2. Provide a reproducer and your assessment of impact.
3. We will acknowledge within 72 hours.

Fallback — **private email** to the maintainer listed in
`pyproject.toml` (address available via the repository's
`.zenodo.json` metadata or the maintainer's GitHub profile).

## What to include

- A clear description of the issue and how to reproduce it.
- The version / commit SHA affected.
- Impact assessment (authentication bypass? data leak? DoS?).
- Your proposed fix or mitigation, if you have one.

## Our response

- **Acknowledgement**: within 72 hours of receipt.
- **Triage and severity assessment**: within 7 days.
- **Fix timeline**: communicated at triage. Critical (auth
  bypass, remote code execution, credential leak) — target 7
  days. High — 14 days. Medium — 30 days. Low — next scheduled
  release.
- **Coordinated disclosure**: we will agree a disclosure date
  with you before publishing details. Default embargo is 90
  days or until a fix is shipped, whichever is first.

## Credit

Reporters are credited in release notes unless they request
otherwise. We do not currently run a paid bug-bounty programme.

## Out of scope

- Issues in dependencies (report upstream to `mcp`, `aiosqlite`,
  `starlette`, etc.).
- Denial-of-service from unconfigured deployments — operators
  are responsible for rate-limit settings
  (`PLOIDY_RATE_CAPACITY`, `PLOIDY_RATE_PER_SEC`).
- Social-engineering attacks against the maintainer.
- Self-inflicted issues from running older untagged commits.

## Cryptographic primitives

Security-critical comparisons use `hmac.compare_digest`. OAuth
tokens are `secrets.token_urlsafe(32)` (256-bit opaque). PKCE
verification is handled by the MCP SDK. If you find a site that
should use constant-time comparison or a CSPRNG but doesn't,
please report it.
