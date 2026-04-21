# Contribution conventions

Ground rules for keeping research and service work coherent in this
monorepo. External contributors are welcome; maintainers follow the
extra steps noted below.

## Paper snapshots get a tag

Every time a paper version is submitted or a preprint goes out, tag the
commit that produced the reported numbers:

```bash
git tag -a v<X.Y.Z>-paper <commit> -m "<venue> submission snapshot"
git push origin v<X.Y.Z>-paper
```

Annotation body template:

```
Paper-reproducing snapshot for the <venue> submission.

This is the last commit before <divergence-point>.

Reproduction: check out this tag, run experiments/src/run_experiment.py
per experiments/README.md.

Post-tag divergences (do NOT use when reproducing paper):
- <bullet per change that affects behaviour>
```

The tag is the public contract: "these numbers came from this code."
Everything on `main` beyond the tag is fair game to evolve for service
use, but the tagged commit stays immutable.

Current tags:
- `v0.3.3-paper` — preprint snapshot.

## Research ↔ service prompt firewall

[`experiments/src/run_experiment.py`](experiments/src/run_experiment.py)
has its **own inline prompts** and wraps the `claude --print` CLI. It
never imports from
[`src/ploidy/api_client.py`](src/ploidy/api_client.py). That gap is
intentional — it lets us restructure service-side prompts (for
caching, UX, latency) without silently changing what the experimental
pipeline sends.

Rules:

1. **Do not introduce an import from `experiments/` into `src/ploidy/`.**
2. If you change a shared-looking prompt in `src/ploidy/api_client.py`,
   record the change in the next paper-snapshot annotation's
   "Post-tag divergences" list.
3. If a research sweep wants to reuse a service prompt, copy the
   string with a clear `# vendored from src/ploidy/api_client.py at <sha>`
   comment — do not import.

## Branch + PR workflow

- Branch per logical change. Squash-merge on GitHub.
- CI must be green (`test (3.11/3.12/3.13)`, `ruff`, `licenses`,
  `security`, `build` when paper files change) before merging.
- **External contributors**: open a PR against the primary repo
  (`heznpc/ploidy-research`). Normal GitHub fork + PR flow.
- **Maintainers**: `origin` is configured with a multi-remote push
  (primary + historical mirror). One `git push` propagates to both;
  do not rebuild that config unless you know why it exists.

## Service vs research API surfaces

| Surface | Audience | Canonical entry point |
|---|---|---|
| Research protocol (strict phase state machine) | `experiments/` scripts | `run_experiment.py` inline prompts |
| Service tool (v0.4+) | MCP clients (Claude Code, Claude.ai, Desktop) | `debate(prompt, mode=...)` in [`src/ploidy/server.py`](src/ploidy/server.py) |
| Two-terminal legacy | Research users running the MCP server | 12-tool state machine — see [`docs/v0.4-migration.md`](docs/v0.4-migration.md) |
| Claude Code slash command | [`/ploidy`](.claude/commands/ploidy.md) users | `.claude/commands/ploidy.md` |

Do not collapse these. Each exists for a specific caller; merging them
would force research reproducibility to track service UX evolution,
which is precisely the trap we set tags to avoid.

## Documentation placement

- Service operator docs → `docs/` (e.g. `custom-connector.md`, `token-cost.md`, `v0.4-migration.md`).
- Research notes → `paper/`, `planning/`, `literature/`.
- Deployment recipes → `deploy/`.
- Convention / workflow → this file.

When adding a new capability, place the primary reference where its
audience will look first; link from the other locations if relevant.
