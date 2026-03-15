# Ploidy

Cross-session multi-agent debate MCP server.

## Architecture Decision (2026-03-15)

- **v0.1** = Two-Terminal approach (Approach C). Two MCP client sessions connect to one Ploidy server via Streamable HTTP. Deep session has project context, Fresh session starts clean. Zero extra cost for Max/Pro subscribers.
- **v0.2** = API fallback (Approach B). OpenAI-compatible endpoint via `openai` SDK with configurable `base_url`. For automation and single-terminal use.
- **v0.3+** = MCP Sampling (Approach A). When clients support `sampling/createMessage` with strong isolation.

## Language & Runtime
- Python 3.11+
- Async-first (asyncio, aiosqlite)
- FastMCP-based server with Streamable HTTP transport

## Key Files
- `src/ploidy/server.py` -- FastMCP server entry point, registers debate tools, Streamable HTTP on port 8765
- `src/ploidy/protocol.py` -- Debate state machine (phases: CREATED, POSITIONS, CHALLENGE, CONVERGENCE, COMPLETE)
- `src/ploidy/session.py` -- Session lifecycle, Deep/Fresh role assignment, context metadata
- `src/ploidy/convergence.py` -- Convergence engine, synthesis of positions into structured results
- `src/ploidy/store.py` -- SQLite persistence layer (aiosqlite, WAL mode for concurrent access)
- `src/ploidy/exceptions.py` -- Domain exceptions (DebateNotFound, InvalidPhaseTransition, etc.)
- `src/ploidy/__main__.py` -- CLI entry point

## Key Design Docs
- `docs/ARCHITECTURE.md` -- System overview, module roles, data flow
- `docs/SESSION_B_ORCHESTRATION.md` -- Full analysis of three orchestration approaches

## Conventions
- Format with `ruff`
- Test with `pytest` (async tests via `pytest-asyncio`)
- All public functions need docstrings
- Type hints on all function signatures
