# Ploidy

Cross-session multi-agent debate MCP server.

## Architecture Decision (2026-03-15, updated 2026-03-20)

- **v0.1** = Two-Terminal approach (Approach C). Two MCP client sessions connect to one Ploidy server via Streamable HTTP. Deep session has project context, Fresh session starts clean. Zero extra cost for Max/Pro subscribers.
- **v0.2** = API fallback (Approach B) + Semi-Fresh sessions + LLM convergence + Dashboard. OpenAI-compatible endpoint via `openai` SDK with configurable `base_url`. Single-terminal `debate_auto` tool. Semi-Fresh sessions with passive/active delivery modes. LLM-enhanced convergence meta-analysis. Visualization dashboard.
- **v0.3** (current) = Cross-model validation (4 families: Opus, Sonnet, Gemini, GPT-5.4). Stochastic-N baseline for Event A/B isolation. Ploidy sweep 1n–4n. Effort/language/injection sweeps. 25 extended tasks. COLM 2026 submission.
- **v0.4+** = MCP Sampling (Approach A). When clients support `sampling/createMessage` with strong isolation.

## Language & Runtime
- Python 3.11+
- Async-first (asyncio, aiosqlite)
- FastMCP-based server with Streamable HTTP transport

## Key Files
- `src/ploidy/server.py` -- FastMCP server entry point, 10 debate tools, Streamable HTTP on port 8765
- `src/ploidy/protocol.py` -- Debate state machine (phases: INDEPENDENT, POSITION, CHALLENGE, CONVERGENCE, COMPLETE)
- `src/ploidy/session.py` -- Session lifecycle, Deep/Semi-Fresh/Fresh roles, delivery modes, effort levels
- `src/ploidy/convergence.py` -- Convergence engine (rule-based + optional LLM meta-analysis)
- `src/ploidy/api_client.py` -- OpenAI-compatible API client for v0.2 automated sessions
- `src/ploidy/dashboard.py` -- Lightweight ASGI web dashboard for debate history visualization
- `src/ploidy/store.py` -- SQLite persistence layer (aiosqlite, WAL mode for concurrent access)
- `src/ploidy/exceptions.py` -- Domain exceptions (PloidyError, ProtocolError, etc.)
- `src/ploidy/__main__.py` -- CLI entry point
- `experiments/run_experiment.py` -- Experiment runner with effort-sweep support

## Key Design Docs
- `docs/ARCHITECTURE.md` -- System overview, module roles, data flow
- `docs/SESSION_B_ORCHESTRATION.md` -- Full analysis of three orchestration approaches

## Conventions
- Format with `ruff`
- Test with `pytest` (async tests via `pytest-asyncio`)
- All public functions need docstrings
- Type hints on all function signatures
