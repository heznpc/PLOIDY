# Ploidy

**Same model, different context depths, better decisions.**

[![Docs](https://img.shields.io/badge/docs-heznpc.github.io%2Fploidy-blue)](https://heznpc.github.io/ploidy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Status: Pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange)]()

Ploidy is an MCP server that orchestrates structured debates between multiple sessions of the same AI model -- each with intentionally different context depths. When two sessions of the same model disagree, the cause is clear: one has context the other doesn't. That's a signal you can act on.

## Quick Start

```bash
pip install ploidy
```

```bash
# Terminal 1 -- start the server and create a debate
ploidy start "Should we use monorepo or polyrepo?"

# Terminal 2 -- join the debate from a fresh session
ploidy join debate-xxxx
```

Both terminals connect to the same Ploidy MCP server via Streamable HTTP. Terminal 1 carries your full project context (the "Deep" session). Terminal 2 starts clean (the "Fresh" session). They debate through a structured protocol, and the disagreements are interpretable because context is the only variable.

### MCP Client Configuration

```json
{
  "ploidy": {
    "type": "streamable-http",
    "url": "http://localhost:8765/mcp"
  }
}
```

## Documentation

Full documentation is available at **[heznpc.github.io/ploidy](https://heznpc.github.io/ploidy/)**.

- [Getting Started](https://heznpc.github.io/ploidy/getting-started/) -- Installation and first debate
- [How It Works](https://heznpc.github.io/ploidy/how-it-works/) -- The core concept and debate protocol
- [Architecture](https://heznpc.github.io/ploidy/architecture/) -- Technical overview and module structure
- [API Reference](https://heznpc.github.io/ploidy/api-reference/) -- Complete MCP tool documentation
- [Research](https://heznpc.github.io/ploidy/research/) -- Academic positioning and references
- [Contributing](https://heznpc.github.io/ploidy/contributing/) -- Development setup and PR process

## Status

**Pre-alpha.** The server runs, the debate protocol is defined, and tools are registered. The full debate orchestration, convergence engine, and persistence layer are under active implementation.

## License

MIT
