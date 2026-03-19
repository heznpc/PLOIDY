"""MCP server entry point for Ploidy.

Exposes debate tools via the Model Context Protocol, allowing MCP clients
to initiate debates, submit positions, and retrieve convergence results.

Tools exposed (11):
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
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime

from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ploidy.convergence import ConvergenceEngine
from ploidy.exceptions import PloidyError, ProtocolError, SessionError
from ploidy.protocol import DebateMessage, DebatePhase, DebateProtocol, SemanticAction
from ploidy.session import DeliveryMode, SessionContext, SessionRole
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
_USE_LLM_CONVERGENCE = os.environ.get("PLOIDY_LLM_CONVERGENCE", "").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class _PloidyTokenVerifier:
    """Simple bearer token verifier using PLOIDY_AUTH_TOKEN env var."""

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a bearer token against the configured secret."""
        if _AUTH_TOKEN and token == _AUTH_TOKEN:
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

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_store: DebateStore | None = None
_protocols: dict[str, DebateProtocol] = {}
_sessions: dict[str, SessionContext] = {}
_debate_sessions: dict[str, list[str]] = {}
_session_to_debate: dict[str, str] = {}  # reverse index
_debate_locks: dict[str, asyncio.Lock] = {}
_paused_debates: dict[str, dict] = {}  # debate_id -> auto-debate context for HITL resume


async def _init() -> DebateStore:
    """Lazily initialise the store and recover state from SQLite."""
    global _store
    if _store is None:
        _store = DebateStore()
        await _store.initialize()
        await _recover_state(_store)
    return _store


async def _recover_state(store: DebateStore) -> None:
    """Reconstruct in-memory state from persisted data on startup."""
    active_debates = await store.list_active_debates()
    recovered = 0
    for debate in active_debates:
        debate_id = debate["id"]
        if debate_id in _protocols:
            continue

        protocol = DebateProtocol(debate_id, debate["prompt"])
        sessions = await store.get_sessions(debate_id)
        messages = await store.get_messages(debate_id)

        session_ids = []
        for s in sessions:
            role_map = {
                "experienced": SessionRole.EXPERIENCED,
                "semi_fresh": SessionRole.SEMI_FRESH,
                "fresh": SessionRole.FRESH,
            }
            role = role_map.get(s["role"], SessionRole.FRESH)
            try:
                delivery_mode = DeliveryMode(s.get("delivery_mode", "none"))
            except ValueError:
                delivery_mode = DeliveryMode.NONE
            ctx = SessionContext(
                session_id=s["id"],
                role=role,
                base_prompt=s["base_prompt"],
                context_documents=s.get("context_documents", []),
                delivery_mode=delivery_mode,
                compressed_summary=s.get("compressed_summary"),
                metadata=s.get("metadata", {}),
            )
            _sessions[s["id"]] = ctx
            _session_to_debate[s["id"]] = debate_id
            session_ids.append(s["id"])

        # Replay messages to reconstruct protocol state
        phase_order = list(DebatePhase)
        for m in messages:
            phase = DebatePhase(m["phase"])
            # Advance protocol to match message phase, with safety limit
            advances = 0
            while protocol.phase != phase and advances < len(phase_order):
                try:
                    protocol.advance_phase()
                    advances += 1
                except ProtocolError:
                    logger.warning(
                        "Cannot advance to %s during recovery of debate %s",
                        phase.value,
                        debate_id,
                    )
                    break
            action = SemanticAction(m["action"]) if m["action"] else None
            msg = DebateMessage(
                session_id=m["session_id"],
                phase=phase,
                content=m["content"],
                timestamp=m["timestamp"] or _now(),
                action=action,
            )
            protocol.messages.append(msg)

        # If all positions are in, advance to challenge
        if protocol.phase == DebatePhase.POSITION:
            position_sessions = {
                m.session_id for m in protocol.messages if m.phase == DebatePhase.POSITION
            }
            if len(session_ids) >= 2 and set(session_ids) <= position_sessions:
                try:
                    protocol.advance_phase()
                except ProtocolError:
                    pass

        _protocols[debate_id] = protocol
        _debate_sessions[debate_id] = session_ids
        _debate_locks[debate_id] = asyncio.Lock()
        recovered += 1

    if recovered:
        logger.info("Recovered %d active debate(s) from database", recovered)


def _find_debate(session_id: str) -> str:
    """Look up debate_id from a session_id via reverse index."""
    debate_id = _session_to_debate.get(session_id)
    if debate_id is None:
        raise SessionError(f"No debate found for session {session_id}")
    return debate_id


def _get_lock(debate_id: str) -> asyncio.Lock:
    """Get or create a per-debate lock."""
    if debate_id not in _debate_locks:
        _debate_locks[debate_id] = asyncio.Lock()
    return _debate_locks[debate_id]


def _now() -> str:
    """UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def _validate_length(text: str, max_len: int, field: str) -> None:
    """Validate text length, raise ProtocolError if exceeded."""
    if len(text) > max_len:
        raise ProtocolError(f"{field} exceeds maximum length ({len(text)} > {max_len})")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=True,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
async def debate_start(prompt: str, context_documents: list[str] | None = None) -> dict:
    """Begin a new debate session with a decision prompt.

    Creates a debate and an experienced (deep-context) session.
    Share the returned debate_id with the fresh session so it can join.

    Args:
        prompt: The decision question to debate.
        context_documents: Optional documents to give the experienced session.

    Returns:
        Debate and session identifiers.
    """
    store = await _init()

    _validate_length(prompt, _MAX_PROMPT_LEN, "prompt")
    docs = context_documents or []
    if len(docs) > _MAX_CONTEXT_DOCS:
        raise ProtocolError(f"Too many context documents ({len(docs)} > {_MAX_CONTEXT_DOCS})")
    for i, doc in enumerate(docs):
        _validate_length(doc, _MAX_CONTENT_LEN, f"context_documents[{i}]")

    debate_id = uuid.uuid4().hex[:12]
    await store.save_debate(debate_id, prompt)

    exp_id = f"{debate_id}-exp-{uuid.uuid4().hex[:6]}"
    exp = SessionContext(
        session_id=exp_id,
        role=SessionRole.EXPERIENCED,
        base_prompt=prompt,
        context_documents=docs,
    )
    await store.save_session(
        exp_id,
        debate_id,
        "experienced",
        prompt,
        context_documents=docs,
        delivery_mode=exp.delivery_mode.value,
        compressed_summary=exp.compressed_summary,
        metadata=exp.metadata,
    )

    _sessions[exp_id] = exp
    _debate_sessions[debate_id] = [exp_id]
    _session_to_debate[exp_id] = debate_id

    protocol = DebateProtocol(debate_id, prompt)
    _protocols[debate_id] = protocol
    _debate_locks[debate_id] = asyncio.Lock()

    logger.info("Debate started: %s by session %s", debate_id, exp_id)

    return {
        "debate_id": debate_id,
        "session_id": exp_id,
        "role": "experienced",
        "phase": protocol.phase.value,
        "prompt": prompt,
        "message": f"Debate created. Share this debate_id with the Fresh session: {debate_id}",
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
async def debate_join(
    debate_id: str,
    role: str = "fresh",
    delivery_mode: str = "none",
) -> dict:
    """Join an existing debate as a fresh or semi-fresh session.

    The session receives context based on its role:
    - fresh: Only the debate prompt (zero context)
    - semi_fresh: Compressed summary of prior analysis

    Args:
        debate_id: The debate to join (provided by the experienced session).
        role: Session role — 'fresh' (default) or 'semi_fresh'.
        delivery_mode: Context delivery — 'none', 'passive', or 'active'.

    Returns:
        Session identifier and the debate prompt.
    """
    store = await _init()

    protocol = _protocols.get(debate_id)
    if protocol is None:
        raise PloidyError(f"Debate {debate_id} not found")

    current_count = len(_debate_sessions.get(debate_id, []))
    if current_count >= _MAX_SESSIONS_PER_DEBATE:
        raise ProtocolError(
            f"Debate already has {current_count} sessions (max {_MAX_SESSIONS_PER_DEBATE})"
        )

    # Validate role
    role_map = {"fresh": SessionRole.FRESH, "semi_fresh": SessionRole.SEMI_FRESH}
    session_role = role_map.get(role)
    if session_role is None:
        raise ProtocolError(f"Invalid role '{role}'. Must be 'fresh' or 'semi_fresh'")

    # Validate delivery mode
    dm_map = {
        "none": DeliveryMode.NONE,
        "passive": DeliveryMode.PASSIVE,
        "active": DeliveryMode.ACTIVE,
    }
    dm = dm_map.get(delivery_mode, DeliveryMode.NONE)

    prefix = "sf" if session_role == SessionRole.SEMI_FRESH else "fresh"
    sid = f"{debate_id}-{prefix}-{uuid.uuid4().hex[:6]}"
    ctx = SessionContext(
        session_id=sid,
        role=session_role,
        base_prompt=protocol.prompt,
        context_documents=[],
        delivery_mode=dm,
    )
    await store.save_session(
        sid,
        debate_id,
        role,
        protocol.prompt,
        context_documents=ctx.context_documents,
        delivery_mode=ctx.delivery_mode.value,
        compressed_summary=ctx.compressed_summary,
        metadata=ctx.metadata,
    )

    _sessions[sid] = ctx
    _debate_sessions[debate_id].append(sid)
    _session_to_debate[sid] = debate_id

    logger.info("Session %s joined debate %s as %s", sid, debate_id, role)

    return {
        "debate_id": debate_id,
        "session_id": sid,
        "role": role,
        "delivery_mode": delivery_mode,
        "phase": protocol.phase.value,
        "prompt": protocol.prompt,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
async def debate_position(session_id: str, content: str) -> dict:
    """Submit a position from a session.

    Records a session's stance on the debate prompt during the POSITION phase.
    Auto-advances from INDEPENDENT to POSITION on first submission.
    Auto-advances from POSITION to CHALLENGE when all sessions have submitted.

    Args:
        session_id: The session submitting the position.
        content: The position statement.

    Returns:
        Confirmation with current phase info.
    """
    store = await _init()
    _validate_length(content, _MAX_CONTENT_LEN, "content")

    if session_id not in _sessions:
        raise SessionError(f"Session {session_id} not found")

    debate_id = _find_debate(session_id)
    lock = _get_lock(debate_id)

    async with lock:
        protocol = _protocols[debate_id]

        if protocol.phase == DebatePhase.INDEPENDENT:
            protocol.advance_phase()

        if protocol.phase != DebatePhase.POSITION:
            raise ProtocolError(f"Cannot submit position in phase {protocol.phase.value}")

        msg = DebateMessage(
            session_id=session_id,
            phase=DebatePhase.POSITION,
            content=content,
            timestamp=_now(),
        )
        protocol.submit_message(msg)
        await store.save_message(debate_id, session_id, "position", content)

        session_ids = set(_debate_sessions[debate_id])
        submitted = {m.session_id for m in protocol.messages if m.phase == DebatePhase.POSITION}
        all_in = len(session_ids) >= 2 and session_ids <= submitted

        if all_in:
            protocol.advance_phase()

    logger.info("Position from %s in debate %s (all_in=%s)", session_id, debate_id, all_in)

    return {
        "session_id": session_id,
        "debate_id": debate_id,
        "phase": protocol.phase.value,
        "status": "recorded",
        "content_length": len(content),
        "all_positions_in": all_in,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
async def debate_challenge(session_id: str, content: str, action: str = "challenge") -> dict:
    """Submit a challenge to another session's position.

    Records a session's critique during the CHALLENGE phase.

    Args:
        session_id: The session submitting the challenge.
        content: The challenge or critique text.
        action: Semantic action -- one of 'challenge', 'agree',
                'propose_alternative', or 'synthesize'.

    Returns:
        Confirmation with current phase info.
    """
    store = await _init()
    _validate_length(content, _MAX_CONTENT_LEN, "content")

    if session_id not in _sessions:
        raise SessionError(f"Session {session_id} not found")

    debate_id = _find_debate(session_id)
    lock = _get_lock(debate_id)

    async with lock:
        protocol = _protocols[debate_id]

        if protocol.phase != DebatePhase.CHALLENGE:
            raise ProtocolError(f"Cannot submit challenge in phase {protocol.phase.value}")

        try:
            semantic_action = SemanticAction(action)
        except ValueError:
            raise ProtocolError(
                "Invalid action. Must be one of: agree, challenge, propose_alternative, synthesize"
            )

        msg = DebateMessage(
            session_id=session_id,
            phase=DebatePhase.CHALLENGE,
            content=content,
            timestamp=_now(),
            action=semantic_action,
        )
        protocol.submit_message(msg)
        await store.save_message(debate_id, session_id, "challenge", content, action)

    logger.info("Challenge from %s in debate %s (action=%s)", session_id, debate_id, action)

    return {
        "session_id": session_id,
        "debate_id": debate_id,
        "phase": protocol.phase.value,
        "action": action,
        "status": "recorded",
        "content_length": len(content),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def debate_converge(debate_id: str) -> dict:
    """Trigger convergence analysis for a debate.

    Runs the convergence engine on the debate transcript and produces
    a structured synthesis of agreements and disagreements.

    Args:
        debate_id: The debate to analyze.

    Returns:
        Convergence result with synthesis and confidence score.
    """
    store = await _init()

    protocol = _protocols.get(debate_id)
    if protocol is None:
        raise PloidyError(f"Debate {debate_id} not found")

    lock = _get_lock(debate_id)

    async with lock:
        if protocol.phase != DebatePhase.CHALLENGE:
            raise ProtocolError(
                f"Cannot converge from phase {protocol.phase.value}, must be in CHALLENGE"
            )

        protocol.advance_phase()  # → CONVERGENCE

        engine = ConvergenceEngine(use_llm=_USE_LLM_CONVERGENCE)
        session_roles = {
            sid: _sessions[sid].role.value.capitalize()
            for sid in _debate_sessions.get(debate_id, [])
            if sid in _sessions
        }
        result = await engine.analyze(protocol, session_roles)

        protocol.advance_phase()  # → COMPLETE

    points_json = json.dumps(
        [
            {
                "category": p.category,
                "summary": p.summary,
                "session_a_view": p.session_a_view,
                "session_b_view": p.session_b_view,
                "resolution": p.resolution,
            }
            for p in result.points
        ]
    )
    await store.save_convergence_and_complete(
        debate_id, result.synthesis, result.confidence, points_json
    )

    # Clean up completed debate from memory
    _cleanup_debate(debate_id)

    logger.info(
        "Debate %s converged (confidence=%.2f, points=%d)",
        debate_id,
        result.confidence,
        len(result.points),
    )

    return {
        "debate_id": debate_id,
        "phase": "complete",
        "synthesis": result.synthesis,
        "confidence": result.confidence,
        "points": [
            {
                "category": p.category,
                "summary": p.summary,
                "resolution": p.resolution,
            }
            for p in result.points
        ],
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=True,
        readOnlyHint=False,
        idempotentHint=True,
    ),
)
async def debate_cancel(debate_id: str) -> dict:
    """Cancel a debate in progress.

    Marks the debate as cancelled and cleans up in-memory state.
    Cannot cancel a completed debate.

    Args:
        debate_id: The debate to cancel.

    Returns:
        Confirmation of cancellation.
    """
    store = await _init()

    protocol = _protocols.get(debate_id)
    if protocol is None:
        raise PloidyError(f"Debate {debate_id} not found")

    if protocol.phase == DebatePhase.COMPLETE:
        raise ProtocolError("Cannot cancel a completed debate")

    await store.update_debate_status(debate_id, "cancelled")
    _cleanup_debate(debate_id)

    logger.info("Debate %s cancelled", debate_id)

    return {
        "debate_id": debate_id,
        "status": "cancelled",
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=True,
        readOnlyHint=False,
        idempotentHint=True,
    ),
)
async def debate_delete(debate_id: str) -> dict:
    """Permanently delete a debate and all its data.

    Removes the debate, its sessions, messages, and convergence results
    from both memory and the database. This action is irreversible.

    Args:
        debate_id: The debate to delete.

    Returns:
        Confirmation of deletion.
    """
    store = await _init()

    debate = await store.get_debate(debate_id)
    if debate is None:
        raise PloidyError(f"Debate {debate_id} not found")

    _cleanup_debate(debate_id)
    await store.delete_debate(debate_id)

    logger.info("Debate %s permanently deleted", debate_id)

    return {
        "debate_id": debate_id,
        "status": "deleted",
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
async def debate_status(debate_id: str) -> dict:
    """Get current state of a debate.

    Returns phase, session info, and all messages for a debate.

    Args:
        debate_id: The debate to inspect.

    Returns:
        Current debate status.
    """
    await _init()

    protocol = _protocols.get(debate_id)
    if protocol is None:
        raise PloidyError(f"Debate {debate_id} not found")

    session_ids = _debate_sessions.get(debate_id, [])
    sessions_info = []
    for sid in session_ids:
        ctx = _sessions.get(sid)
        if ctx:
            sessions_info.append({"session_id": sid, "role": ctx.role.value})

    messages_by_phase: dict[str, list[dict]] = {}
    for msg in protocol.messages:
        phase = msg.phase.value
        if phase not in messages_by_phase:
            messages_by_phase[phase] = []
        messages_by_phase[phase].append(
            {
                "session_id": msg.session_id,
                "content": msg.content,
                "action": msg.action.value if msg.action else None,
                "timestamp": msg.timestamp,
            }
        )

    return {
        "debate_id": debate_id,
        "phase": protocol.phase.value,
        "prompt": protocol.prompt,
        "message_count": len(protocol.messages),
        "sessions": sessions_info,
        "messages": messages_by_phase,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
async def debate_history(limit: int = 50) -> dict:
    """Retrieve past debates and their outcomes.

    Lists recent debates with their status and convergence results.

    Args:
        limit: Maximum number of debates to return (default 50, max 200).

    Returns:
        List of past debate summaries.
    """
    store = await _init()
    clamped = min(max(limit, 1), 200)
    debates = await store.list_debates(clamped)
    return {
        "debates": debates,
        "total": len(debates),
        "limit": clamped,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=True,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
async def debate_auto(
    prompt: str,
    context_documents: list[str] | None = None,
    fresh_role: str = "fresh",
    delivery_mode: str = "none",
    pause_at: str | None = None,
) -> dict:
    """Run a complete debate automatically in a single command (v0.2).

    Creates a debate, generates Fresh/Semi-Fresh responses via API,
    runs the full protocol, and returns the convergence result.
    Requires PLOIDY_API_BASE_URL to be configured.

    Args:
        prompt: The decision question to debate.
        context_documents: Optional documents for the experienced session.
        fresh_role: Role for auto-session — 'fresh' or 'semi_fresh'.
        delivery_mode: Context delivery for semi-fresh — 'passive' or 'active'.
        pause_at: Optional phase to pause at for human review — 'challenge'
            (after positions, before challenges) or 'convergence' (after
            challenges, before convergence). Use debate_review to resume.

    Returns:
        Complete debate result with convergence synthesis, or paused state
        if pause_at is specified.
    """
    try:
        from ploidy.api_client import (
            compress_position,
            generate_challenge,
            generate_experienced_position,
            generate_fresh_position,
            generate_semi_fresh_position,
            is_api_available,
        )
    except ImportError:
        raise PloidyError("API client not available. Install with: pip install ploidy[api]")

    if not is_api_available():
        raise PloidyError("API not configured. Set PLOIDY_API_BASE_URL environment variable.")

    store = await _init()

    _validate_length(prompt, _MAX_PROMPT_LEN, "prompt")
    docs = context_documents or []
    if len(docs) > _MAX_CONTEXT_DOCS:
        raise ProtocolError(f"Too many context documents ({len(docs)} > {_MAX_CONTEXT_DOCS})")
    for i, doc in enumerate(docs):
        _validate_length(doc, _MAX_CONTENT_LEN, f"context_documents[{i}]")

    role_map = {"fresh": SessionRole.FRESH, "semi_fresh": SessionRole.SEMI_FRESH}
    auto_role = role_map.get(fresh_role)
    if auto_role is None:
        raise ProtocolError(f"Invalid fresh_role '{fresh_role}'. Must be 'fresh' or 'semi_fresh'")

    dm_map = {
        "none": DeliveryMode.NONE,
        "passive": DeliveryMode.PASSIVE,
        "active": DeliveryMode.ACTIVE,
    }
    dm = dm_map.get(delivery_mode)
    if dm is None:
        raise ProtocolError(
            f"Invalid delivery_mode '{delivery_mode}'. Must be 'none', 'passive', or 'active'"
        )
    if auto_role == SessionRole.FRESH and dm != DeliveryMode.NONE:
        raise ProtocolError("Fresh auto sessions must use delivery_mode='none'")
    if auto_role == SessionRole.SEMI_FRESH and dm == DeliveryMode.NONE:
        raise ProtocolError("Semi-fresh auto sessions must use 'passive' or 'active'")

    valid_pause = {None, "challenge", "convergence"}
    if pause_at not in valid_pause:
        raise ProtocolError(f"Invalid pause_at '{pause_at}'. Must be 'challenge' or 'convergence'")

    # 1. Create debate + experienced session
    debate_id = uuid.uuid4().hex[:12]
    await store.save_debate(debate_id, prompt)

    exp_id = f"{debate_id}-exp-{uuid.uuid4().hex[:6]}"
    exp = SessionContext(
        session_id=exp_id,
        role=SessionRole.EXPERIENCED,
        base_prompt=prompt,
        context_documents=docs,
        delivery_mode=DeliveryMode.PASSIVE,
    )
    await store.save_session(
        exp_id,
        debate_id,
        "experienced",
        prompt,
        context_documents=docs,
        delivery_mode=exp.delivery_mode.value,
        compressed_summary=exp.compressed_summary,
        metadata=exp.metadata,
    )

    _sessions[exp_id] = exp
    _debate_sessions[debate_id] = [exp_id]
    _session_to_debate[exp_id] = debate_id

    protocol = DebateProtocol(debate_id, prompt)
    _protocols[debate_id] = protocol
    _debate_locks[debate_id] = asyncio.Lock()

    # 2. Create auto-session
    prefix = "sf" if auto_role == SessionRole.SEMI_FRESH else "fresh"
    auto_id = f"{debate_id}-{prefix}-{uuid.uuid4().hex[:6]}"
    auto_ctx = SessionContext(
        session_id=auto_id,
        role=auto_role,
        base_prompt=prompt,
        context_documents=[],
        delivery_mode=dm,
    )
    await store.save_session(
        auto_id,
        debate_id,
        fresh_role,
        prompt,
        context_documents=auto_ctx.context_documents,
        delivery_mode=auto_ctx.delivery_mode.value,
        compressed_summary=auto_ctx.compressed_summary,
        metadata=auto_ctx.metadata,
    )

    _sessions[auto_id] = auto_ctx
    _debate_sessions[debate_id].append(auto_id)
    _session_to_debate[auto_id] = debate_id

    logger.info(
        "Auto-debate %s: experienced=%s, %s=%s",
        debate_id,
        exp_id,
        fresh_role,
        auto_id,
    )
    try:
        # 3. Generate positions
        protocol.advance_phase()  # → POSITION

        exp_pos = await generate_experienced_position(prompt, docs)

        if auto_role == SessionRole.SEMI_FRESH:
            compressed = await compress_position(exp_pos)
            auto_ctx.compressed_summary = compressed
            await store.update_session_context(
                auto_id,
                context_documents=auto_ctx.context_documents,
                delivery_mode=auto_ctx.delivery_mode.value,
                compressed_summary=auto_ctx.compressed_summary,
                metadata=auto_ctx.metadata,
            )
            auto_pos = await generate_semi_fresh_position(
                prompt, compressed, delivery_mode=delivery_mode
            )
        else:
            auto_pos = await generate_fresh_position(prompt)

        for sid, content in [(exp_id, exp_pos), (auto_id, auto_pos)]:
            msg = DebateMessage(
                session_id=sid,
                phase=DebatePhase.POSITION,
                content=content,
                timestamp=_now(),
            )
            protocol.submit_message(msg)
            await store.save_message(debate_id, sid, "position", content)

        # HITL checkpoint: pause before challenge phase
        if pause_at == "challenge":
            _paused_debates[debate_id] = {
                "exp_id": exp_id,
                "auto_id": auto_id,
                "exp_pos": exp_pos,
                "auto_pos": auto_pos,
                "fresh_role": fresh_role,
                "delivery_mode": delivery_mode,
                "paused_phase": "challenge",
            }
            await store.update_debate_status(debate_id, "paused")
            logger.info("Auto-debate %s paused before challenge phase (HITL)", debate_id)
            return {
                "debate_id": debate_id,
                "phase": "paused",
                "paused_before": "challenge",
                "mode": "auto_hitl",
                "positions": {
                    "experienced": exp_pos[:500],
                    "auto": auto_pos[:500],
                },
                "message": "Debate paused for human review. Use debate_review to continue.",
            }

        protocol.advance_phase()  # → CHALLENGE

        exp_challenge = await generate_challenge(
            own_position=exp_pos,
            other_position=auto_pos,
            own_role="experienced",
            other_role=fresh_role,
        )
        auto_challenge = await generate_challenge(
            own_position=auto_pos,
            other_position=exp_pos,
            own_role=fresh_role,
            other_role="experienced",
        )

        for sid, content in [(exp_id, exp_challenge), (auto_id, auto_challenge)]:
            ch_msg = DebateMessage(
                session_id=sid,
                phase=DebatePhase.CHALLENGE,
                content=content,
                timestamp=_now(),
                action=SemanticAction.CHALLENGE,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(debate_id, sid, "challenge", content, "challenge")

        # HITL checkpoint: pause before convergence phase
        if pause_at == "convergence":
            _paused_debates[debate_id] = {
                "exp_id": exp_id,
                "auto_id": auto_id,
                "exp_pos": exp_pos,
                "auto_pos": auto_pos,
                "exp_challenge": exp_challenge,
                "auto_challenge": auto_challenge,
                "fresh_role": fresh_role,
                "delivery_mode": delivery_mode,
                "paused_phase": "convergence",
            }
            await store.update_debate_status(debate_id, "paused")
            logger.info("Auto-debate %s paused before convergence (HITL)", debate_id)
            return {
                "debate_id": debate_id,
                "phase": "paused",
                "paused_before": "convergence",
                "mode": "auto_hitl",
                "challenges": {
                    "experienced": exp_challenge[:500],
                    "auto": auto_challenge[:500],
                },
                "message": "Debate paused for human review. Use debate_review to continue.",
            }

        protocol.advance_phase()  # → CONVERGENCE

        engine = ConvergenceEngine(use_llm=_USE_LLM_CONVERGENCE)
        session_roles = {
            exp_id: "Experienced",
            auto_id: fresh_role.replace("_", "-").title(),
        }
        result = await engine.analyze(protocol, session_roles)

        protocol.advance_phase()  # → COMPLETE

        points_json = json.dumps(
            [
                {
                    "category": p.category,
                    "summary": p.summary,
                    "session_a_view": p.session_a_view,
                    "session_b_view": p.session_b_view,
                    "resolution": p.resolution,
                }
                for p in result.points
            ]
        )
        await store.save_convergence_and_complete(
            debate_id, result.synthesis, result.confidence, points_json
        )
        _cleanup_debate(debate_id)
    except Exception:
        await _delete_failed_debate(store, debate_id)
        raise

    logger.info(
        "Auto-debate %s complete (confidence=%.2f)",
        debate_id,
        result.confidence,
    )

    return {
        "debate_id": debate_id,
        "phase": "complete",
        "mode": "auto",
        "fresh_role": fresh_role,
        "delivery_mode": delivery_mode,
        "synthesis": result.synthesis,
        "confidence": result.confidence,
        "meta_analysis": result.meta_analysis,
        "points": [
            {
                "category": p.category,
                "summary": p.summary,
                "resolution": p.resolution,
            }
            for p in result.points
        ],
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
async def debate_review(
    debate_id: str,
    action: str = "approve",
    override_content: str | None = None,
) -> dict:
    """Review and resume a paused auto-debate (HITL).

    When debate_auto is called with pause_at, the debate pauses at the
    specified phase for human review. Use this tool to approve, override,
    or reject the paused output and continue the debate.

    Args:
        debate_id: The paused debate to review.
        action: One of 'approve' (continue as-is), 'override' (replace
            last phase output with override_content), or 'reject' (cancel).
        override_content: Required when action='override'. Replaces the
            auto-generated content for the current phase.

    Returns:
        The resumed debate result or cancellation confirmation.
    """
    store = await _init()

    if debate_id not in _paused_debates:
        raise PloidyError(f"Debate {debate_id} is not paused or does not exist")

    if action not in ("approve", "override", "reject"):
        raise ProtocolError(
            f"Invalid action '{action}'. Must be 'approve', 'override', or 'reject'"
        )

    if action == "override" and not override_content:
        raise ProtocolError("override_content is required when action='override'")

    ctx = _paused_debates.pop(debate_id)
    protocol = _protocols.get(debate_id)

    if protocol is None:
        raise PloidyError(f"Protocol state lost for debate {debate_id}")

    if action == "reject":
        await store.update_debate_status(debate_id, "cancelled")
        _cleanup_debate(debate_id)
        logger.info("Auto-debate %s rejected by human reviewer", debate_id)
        return {
            "debate_id": debate_id,
            "phase": "cancelled",
            "mode": "auto_hitl",
            "message": "Debate rejected and cancelled by reviewer.",
        }

    try:
        from ploidy.api_client import generate_challenge
    except ImportError:
        raise PloidyError("API client not available. Install with: pip install ploidy[api]")

    exp_id = ctx["exp_id"]
    auto_id = ctx["auto_id"]
    fresh_role = ctx["fresh_role"]

    await store.update_debate_status(debate_id, "active")

    if ctx["paused_phase"] == "challenge":
        # Resume from after positions, before challenges
        exp_pos = ctx["exp_pos"]
        auto_pos = ctx["auto_pos"]

        if action == "override" and override_content:
            # Human overrides the auto position
            auto_pos = override_content
            # Update the stored message
            msg = DebateMessage(
                session_id=auto_id,
                phase=DebatePhase.POSITION,
                content=auto_pos,
                timestamp=_now(),
            )
            # Replace last auto position in protocol
            protocol.messages = [
                m
                for m in protocol.messages
                if not (m.session_id == auto_id and m.phase == DebatePhase.POSITION)
            ]
            protocol.submit_message(msg)
            await store.save_message(debate_id, auto_id, "position", auto_pos)

        protocol.advance_phase()  # → CHALLENGE

        exp_challenge = await generate_challenge(
            own_position=exp_pos,
            other_position=auto_pos,
            own_role="experienced",
            other_role=fresh_role,
        )
        auto_challenge = await generate_challenge(
            own_position=auto_pos,
            other_position=exp_pos,
            own_role=fresh_role,
            other_role="experienced",
        )

        for sid, content in [(exp_id, exp_challenge), (auto_id, auto_challenge)]:
            ch_msg = DebateMessage(
                session_id=sid,
                phase=DebatePhase.CHALLENGE,
                content=content,
                timestamp=_now(),
                action=SemanticAction.CHALLENGE,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(debate_id, sid, "challenge", content, "challenge")

    elif ctx["paused_phase"] == "convergence":
        # Resume from after challenges, before convergence
        if action == "override" and override_content:
            # Human overrides the auto challenge
            auto_challenge = override_content
            protocol.messages = [
                m
                for m in protocol.messages
                if not (m.session_id == auto_id and m.phase == DebatePhase.CHALLENGE)
            ]
            ch_msg = DebateMessage(
                session_id=auto_id,
                phase=DebatePhase.CHALLENGE,
                content=auto_challenge,
                timestamp=_now(),
                action=SemanticAction.CHALLENGE,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(debate_id, auto_id, "challenge", auto_challenge, "challenge")

    # Continue to convergence + complete
    protocol.advance_phase()  # → CONVERGENCE

    engine = ConvergenceEngine(use_llm=_USE_LLM_CONVERGENCE)
    session_roles = {
        exp_id: "Experienced",
        auto_id: fresh_role.replace("_", "-").title(),
    }
    result = await engine.analyze(protocol, session_roles)

    protocol.advance_phase()  # → COMPLETE

    points_json = json.dumps(
        [
            {
                "category": p.category,
                "summary": p.summary,
                "session_a_view": p.session_a_view,
                "session_b_view": p.session_b_view,
                "resolution": p.resolution,
            }
            for p in result.points
        ]
    )
    await store.save_convergence_and_complete(
        debate_id, result.synthesis, result.confidence, points_json
    )
    _cleanup_debate(debate_id)

    logger.info(
        "Auto-debate %s resumed and completed via HITL (confidence=%.2f)",
        debate_id,
        result.confidence,
    )

    return {
        "debate_id": debate_id,
        "phase": "complete",
        "mode": "auto_hitl",
        "reviewer_action": action,
        "fresh_role": fresh_role,
        "synthesis": result.synthesis,
        "confidence": result.confidence,
        "meta_analysis": result.meta_analysis,
        "points": [
            {
                "category": p.category,
                "summary": p.summary,
                "resolution": p.resolution,
            }
            for p in result.points
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _cleanup_debate(debate_id: str) -> None:
    """Remove a completed/cancelled debate from in-memory state."""
    _protocols.pop(debate_id, None)
    _debate_locks.pop(debate_id, None)
    session_ids = _debate_sessions.pop(debate_id, [])
    for sid in session_ids:
        _sessions.pop(sid, None)
        _session_to_debate.pop(sid, None)


async def _delete_failed_debate(store: DebateStore, debate_id: str) -> None:
    """Best-effort cleanup for debates that fail mid-creation."""
    _cleanup_debate(debate_id)
    try:
        await store.delete_debate(debate_id)
    except Exception:
        logger.exception("Failed to clean up partially created debate %s", debate_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def shutdown() -> None:
    """Close the database connection on server shutdown."""
    global _store
    if _store is not None:
        await _store.close()
        _store = None
    _protocols.clear()
    _sessions.clear()
    _debate_sessions.clear()
    _session_to_debate.clear()
    _debate_locks.clear()
    logger.info("Database connection closed and runtime state cleared")


def main() -> None:
    """Run the Ploidy MCP server."""
    log_level = os.environ.get("PLOIDY_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    import signal

    def _shutdown_handler(sig: int, frame: object) -> None:
        asyncio.get_event_loop().run_until_complete(shutdown())

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    mcp.run(transport="streamable-http")
