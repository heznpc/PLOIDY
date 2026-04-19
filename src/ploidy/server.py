"""MCP server entry point for Ploidy.

Thin tool layer over ``DebateService``. Tools validate MCP-specific
concerns (annotations, docstrings surfaced to clients) and forward to
the service. All state lives on the service instance.

Tools exposed (12):
- debate_start: Begin a new debate session with a decision prompt
- debate_join: Join an existing debate as the fresh session
- debate_position: Submit a position from a session
- debate_challenge: Submit a challenge to another session's position
- debate_converge: Trigger convergence analysis
- debate_status: Get current state of a debate
- debate_cancel: Cancel a debate in progress
- debate_delete: Permanently delete a debate and all its data
- debate_history: Retrieve past debates and their outcomes
- debate_auto: Run a full two-sided debate automatically via API
- debate_review: Review and resume a paused auto-debate (HITL)
- debate_solo: Caller-supplied positions; converge in one call (no API key needed)
"""

import asyncio
import hmac
import logging
import os

from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ploidy.logctx import install as install_logctx
from ploidy.logctx import traced
from ploidy.ratelimit import TokenBucketLimiter
from ploidy.service import DebateService
from ploidy.store import DebateStore

logger = logging.getLogger("ploidy")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_PORT = int(os.environ.get("PLOIDY_PORT", "8765"))
_MAX_PROMPT_LEN = int(os.environ.get("PLOIDY_MAX_PROMPT_LEN", "10000"))
_MAX_CONTENT_LEN = int(os.environ.get("PLOIDY_MAX_CONTENT_LEN", "50000"))
_MAX_CONTEXT_DOCS = int(os.environ.get("PLOIDY_MAX_CONTEXT_DOCS", "10"))
_MAX_SESSIONS_PER_DEBATE = int(os.environ.get("PLOIDY_MAX_SESSIONS", "5"))
_AUTH_TOKEN = os.environ.get("PLOIDY_AUTH_TOKEN")
_USE_LLM_CONVERGENCE = os.environ.get("PLOIDY_LLM_CONVERGENCE", "").lower() in (
    "1",
    "true",
    "yes",
)
# 0 disables the limiter. Capacity is the burst allowance; rate is sustained.
_RATE_CAPACITY = float(os.environ.get("PLOIDY_RATE_CAPACITY", "0"))
_RATE_PER_SEC = float(os.environ.get("PLOIDY_RATE_PER_SEC", "0"))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class _PloidyTokenVerifier:
    """Bearer token verifier with constant-time compare."""

    async def verify_token(self, token: str) -> AccessToken | None:
        if not _AUTH_TOKEN:
            return None
        if hmac.compare_digest(token.encode("utf-8"), _AUTH_TOKEN.encode("utf-8")):
            return AccessToken(
                token=token,
                client_id="ploidy-client",
                scopes=["debate"],
            )
        return None


_auth_kwargs: dict = {}
if _AUTH_TOKEN:
    _auth_kwargs["token_verifier"] = _PloidyTokenVerifier()
    logger.info("Bearer token auth enabled via PLOIDY_AUTH_TOKEN")

mcp = FastMCP(
    "Ploidy",
    instructions="Cross-session multi-agent debate MCP server. "
    "Same model, different context depths, better decisions.",
    port=_PORT,
    **_auth_kwargs,
)


@mcp.custom_route("/healthz", methods=["GET"])
async def _healthz(_request):
    """Liveness probe. Succeeds once the DB connection is initialised."""
    from starlette.responses import JSONResponse

    try:
        await _init()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=503)
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Service instance
# ---------------------------------------------------------------------------

_service: DebateService | None = None
_init_lock = asyncio.Lock()


async def _init() -> DebateService:
    """Lazily construct and initialise the shared DebateService."""
    global _service
    if _service is not None and _service._initialized:
        return _service
    async with _init_lock:
        if _service is None:
            _service = DebateService(
                store=DebateStore(),
                use_llm_convergence=_USE_LLM_CONVERGENCE,
                max_prompt_len=_MAX_PROMPT_LEN,
                max_content_len=_MAX_CONTENT_LEN,
                max_context_docs=_MAX_CONTEXT_DOCS,
                max_sessions_per_debate=_MAX_SESSIONS_PER_DEBATE,
                rate_limiter=TokenBucketLimiter(
                    capacity=_RATE_CAPACITY, rate_per_sec=_RATE_PER_SEC
                ),
            )
        await _service.initialize()
        return _service


async def shutdown() -> None:
    """Close the database connection and drop runtime state."""
    global _service
    if _service is not None:
        await _service.shutdown()
        _service = None
    logger.info("Database connection closed and runtime state cleared")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=True, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_start(prompt: str, context_documents: list[str] | None = None) -> dict:
    """Begin a new debate session with a decision prompt.

    Creates a debate and a Deep (full-context) session.
    Share the returned debate_id with the fresh session so it can join.
    """
    svc = await _init()
    return await svc.start_debate(prompt, context_documents)


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=False, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_join(
    debate_id: str,
    role: str = "fresh",
    delivery_mode: str = "none",
) -> dict:
    """Join an existing debate as a fresh or semi-fresh session."""
    svc = await _init()
    return await svc.join_debate(debate_id, role, delivery_mode)


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=False, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_position(session_id: str, content: str) -> dict:
    """Submit a position from a session."""
    svc = await _init()
    return await svc.submit_position(session_id, content)


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=False, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_challenge(session_id: str, content: str, action: str = "challenge") -> dict:
    """Submit a challenge to another session's position."""
    svc = await _init()
    return await svc.submit_challenge(session_id, content, action)


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
@traced
async def debate_converge(debate_id: str) -> dict:
    """Trigger convergence analysis for a debate."""
    svc = await _init()
    return await svc.converge(debate_id)


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=True, readOnlyHint=False, idempotentHint=True),
)
@traced
async def debate_cancel(debate_id: str) -> dict:
    """Cancel a debate in progress."""
    svc = await _init()
    return await svc.cancel(debate_id)


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=True, readOnlyHint=False, idempotentHint=True),
)
@traced
async def debate_delete(debate_id: str) -> dict:
    """Permanently delete a debate and all its data."""
    svc = await _init()
    return await svc.delete(debate_id)


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
)
@traced
async def debate_status(debate_id: str) -> dict:
    """Get current state of a debate."""
    svc = await _init()
    return await svc.status(debate_id)


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
)
@traced
async def debate_history(limit: int = 50) -> dict:
    """Retrieve past debates and their outcomes."""
    svc = await _init()
    return await svc.history(limit)


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=True, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_solo(
    prompt: str,
    deep_position: str,
    fresh_position: str,
    deep_challenge: str | None = None,
    fresh_challenge: str | None = None,
    context_documents: list[str] | None = None,
    deep_label: str = "Deep",
    fresh_label: str = "Fresh",
) -> dict:
    """Run a complete debate from caller-supplied positions in one call.

    Single-terminal entry point: the caller generates both sides locally
    and submits the texts here. No external API key required.
    """
    svc = await _init()
    return await svc.run_solo(
        prompt=prompt,
        deep_position=deep_position,
        fresh_position=fresh_position,
        deep_challenge=deep_challenge,
        fresh_challenge=fresh_challenge,
        context_documents=context_documents,
        deep_label=deep_label,
        fresh_label=fresh_label,
    )


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=True, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_auto(
    prompt: str,
    context_documents: list[str] | None = None,
    fresh_role: str = "fresh",
    delivery_mode: str = "none",
    pause_at: str | None = None,
    deep_n: int = 1,
    fresh_n: int = 1,
    effort: str = "high",
    injection_mode: str = "raw",
    context_pct: int = 100,
    language: str = "en",
    deep_model: str | None = None,
    fresh_model: str | None = None,
) -> dict:
    """Run a complete debate automatically in a single command.

    Requires PLOIDY_API_BASE_URL to be configured. Generates positions
    and challenges via an OpenAI-compatible endpoint, runs the protocol,
    and returns the convergence result.
    """
    svc = await _init()
    return await svc.run_auto(
        prompt=prompt,
        context_documents=context_documents,
        fresh_role=fresh_role,
        delivery_mode=delivery_mode,
        pause_at=pause_at,
        deep_n=deep_n,
        fresh_n=fresh_n,
        effort=effort,
        injection_mode=injection_mode,
        context_pct=context_pct,
        language=language,
        deep_model=deep_model,
        fresh_model=fresh_model,
    )


@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=False, readOnlyHint=False, idempotentHint=False),
)
@traced
async def debate_review(
    debate_id: str,
    action: str = "approve",
    override_content: str | None = None,
) -> dict:
    """Review and resume a paused auto-debate (HITL).

    Call after ``debate_auto`` with ``pause_at`` paused the run. Action
    is one of 'approve', 'override', or 'reject'.
    """
    svc = await _init()
    return await svc.review(debate_id, action, override_content)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Ploidy MCP server."""
    log_level = os.environ.get("PLOIDY_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=(
            "%(asctime)s [%(name)s] %(levelname)s "
            "req=%(request_id)s debate=%(debate_id)s: %(message)s"
        ),
    )
    install_logctx(level=getattr(logging, log_level, logging.INFO))

    # Default to stdio so MCP clients (Claude Code, etc.) can spawn the server
    # on demand. Set PLOIDY_TRANSPORT=streamable-http (or sse) for the
    # multi-client cross-session deployment.
    transport = os.environ.get("PLOIDY_TRANSPORT", "stdio")

    # FastMCP owns the event loop once mcp.run() starts; a signal handler
    # that calls run_until_complete() from inside a running loop raises
    # RuntimeError, so we schedule shutdown on the active loop instead.
    import signal

    def _shutdown_handler(sig: int, frame: object) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(shutdown())
            return
        loop.create_task(shutdown())

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    mcp.run(transport=transport)
