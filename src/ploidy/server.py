"""MCP server entry point for Ploidy.

Exposes debate tools via the Model Context Protocol, allowing MCP clients
to initiate debates, submit positions, and retrieve convergence results.

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
from ploidy.injection import (
    VALID_INJECTION_MODES,
    VALID_LANGUAGES,
    append_language,
    build_deep_prompt,
)
from ploidy.protocol import DebateMessage, DebatePhase, DebateProtocol, SemanticAction
from ploidy.session import DeliveryMode, EffortLevel, SessionContext, SessionRole
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


_RECOVERY_ROLE_MAP = {
    "deep": SessionRole.DEEP,
    "experienced": SessionRole.DEEP,  # backward compat with v0.1 schema
    "semi_fresh": SessionRole.SEMI_FRESH,
    "fresh": SessionRole.FRESH,
}


def _hydrate_session(s: dict) -> SessionContext:
    """Rebuild a SessionContext from a persisted row.

    Tolerates unknown enum values and missing optional columns so that
    older databases recover cleanly. Used by both the active-debate and
    paused-debate recovery paths.
    """
    role = _RECOVERY_ROLE_MAP.get(s["role"], SessionRole.FRESH)
    try:
        delivery_mode = DeliveryMode(s.get("delivery_mode", "none"))
    except ValueError:
        delivery_mode = DeliveryMode.NONE
    try:
        effort_level = EffortLevel(s.get("effort", "high"))
    except ValueError:
        effort_level = EffortLevel.HIGH
    return SessionContext(
        session_id=s["id"],
        role=role,
        base_prompt=s["base_prompt"],
        context_documents=s.get("context_documents", []),
        delivery_mode=delivery_mode,
        effort=effort_level,
        compressed_summary=s.get("compressed_summary"),
        model=s.get("model"),
        metadata=s.get("metadata", {}),
    )


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
            ctx = _hydrate_session(s)
            _sessions[ctx.session_id] = ctx
            _session_to_debate[ctx.session_id] = debate_id
            session_ids.append(ctx.session_id)

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

    # Recover paused debates (HITL state)
    paused_debates = await store.list_paused_debates()
    paused_recovered = 0
    for debate in paused_debates:
        debate_id = debate["id"]
        if debate_id in _paused_debates:
            continue

        paused_ctx_raw = debate.get("paused_context")
        if not paused_ctx_raw:
            logger.warning("Paused debate %s has no persisted context, skipping", debate_id)
            continue

        if isinstance(paused_ctx_raw, str):
            paused_ctx = json.loads(paused_ctx_raw)
        else:
            paused_ctx = paused_ctx_raw

        # Reconstruct protocol at the saved phase
        protocol = DebateProtocol(debate_id, debate["prompt"])
        saved_phase = paused_ctx.get("protocol_phase", "position")
        phase_order = [p.value for p in DebatePhase]
        target_idx = phase_order.index(saved_phase) if saved_phase in phase_order else 1
        for _ in range(target_idx):
            try:
                protocol.advance_phase()
            except ProtocolError:
                break

        # Replay persisted messages into protocol
        messages = await store.get_messages(debate_id)
        for m in messages:
            action = SemanticAction(m["action"]) if m["action"] else None
            msg = DebateMessage(
                session_id=m["session_id"],
                phase=DebatePhase(m["phase"]),
                content=m["content"],
                timestamp=m["timestamp"] or _now(),
                action=action,
            )
            protocol.messages.append(msg)

        # Recover sessions
        sessions = await store.get_sessions(debate_id)
        session_ids = []
        for s in sessions:
            ctx = _hydrate_session(s)
            _sessions[ctx.session_id] = ctx
            _session_to_debate[ctx.session_id] = debate_id
            session_ids.append(ctx.session_id)

        _protocols[debate_id] = protocol
        _debate_sessions[debate_id] = session_ids
        _debate_locks[debate_id] = asyncio.Lock()
        _paused_debates[debate_id] = paused_ctx
        paused_recovered += 1

    if paused_recovered:
        logger.info("Recovered %d paused debate(s) from database", paused_recovered)


def _find_debate(session_id: str) -> str:
    """Look up debate_id from a session_id via reverse index."""
    debate_id = _session_to_debate.get(session_id)
    if debate_id is None:
        raise SessionError(f"No debate found for session {session_id}")
    return debate_id


def _get_lock(debate_id: str) -> asyncio.Lock:
    """Get or create a per-debate lock.

    Uses dict.setdefault() which is atomic in CPython to avoid a
    TOCTOU race where concurrent async tasks could each create a
    different Lock for the same debate_id.
    """
    return _debate_locks.setdefault(debate_id, asyncio.Lock())


def _now() -> str:
    """UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def _validate_length(text: str, max_len: int, field: str) -> None:
    """Validate text length, raise ProtocolError if exceeded."""
    if len(text) > max_len:
        raise ProtocolError(f"{field} exceeds maximum length ({len(text)} > {max_len})")


def _aggregate_positions(positions: list[str] | tuple[str, ...], role_label: str) -> str:
    """Aggregate multiple session positions into a single text block.

    For single-session ploidy (n=1), returns the position as-is.
    For multi-session (n>1), wraps each in labeled sections.

    Args:
        positions: List of position texts.
        role_label: Display label for the role (e.g., 'Deep', 'Fresh').

    Returns:
        Aggregated position text.
    """
    if len(positions) == 1:
        return positions[0]
    parts = []
    for i, pos in enumerate(positions):
        parts.append(f"--- {role_label} Session {i + 1}/{len(positions)} ---\n{pos}")
    return "\n\n".join(parts)


def _parse_dominant_action(challenge_content: str) -> SemanticAction:
    """Parse the dominant semantic action from challenge response text.

    Uses word-boundary regex to count AGREE/CHALLENGE/SYNTHESIZE keywords,
    avoiding false matches (e.g., "DISAGREE" should not count as "AGREE").

    Args:
        challenge_content: The challenge response text.

    Returns:
        The most frequent semantic action found.
    """
    import re

    upper = challenge_content.upper()
    counts = {
        # \bAGREE\b matches "AGREE" but not "DISAGREE"
        SemanticAction.AGREE: len(re.findall(r"\bAGREE\b", upper)),
        SemanticAction.CHALLENGE: len(re.findall(r"\bCHALLENGE\b", upper)),
        SemanticAction.SYNTHESIZE: len(re.findall(r"\bSYNTHESIZE\b", upper)),
        SemanticAction.PROPOSE_ALTERNATIVE: len(
            re.findall(r"\bPROPOSE_ALTERNATIVE\b|\bALTERNATIVE\b", upper)
        ),
    }
    # Default to CHALLENGE if no keywords found
    return max(counts, key=counts.get) if any(counts.values()) else SemanticAction.CHALLENGE


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

    Creates a debate and a Deep (full-context) session.
    Share the returned debate_id with the fresh session so it can join.

    Args:
        prompt: The decision question to debate.
        context_documents: Optional documents to give the Deep session.

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

    deep_id = f"{debate_id}-deep-{uuid.uuid4().hex[:6]}"
    deep_ctx = SessionContext(
        session_id=deep_id,
        role=SessionRole.DEEP,
        base_prompt=prompt,
        context_documents=docs,
    )
    await store.save_session(
        deep_id,
        debate_id,
        "deep",
        prompt,
        context_documents=docs,
        delivery_mode=deep_ctx.delivery_mode.value,
        compressed_summary=deep_ctx.compressed_summary,
        metadata=deep_ctx.metadata,
    )

    _sessions[deep_id] = deep_ctx
    _debate_sessions[debate_id] = [deep_id]
    _session_to_debate[deep_id] = debate_id

    protocol = DebateProtocol(debate_id, prompt)
    _protocols[debate_id] = protocol
    _debate_locks[debate_id] = asyncio.Lock()

    logger.info("Debate started: %s by session %s", debate_id, deep_id)

    return {
        "debate_id": debate_id,
        "session_id": deep_id,
        "role": "deep",
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

    Single-terminal entry point. The caller (e.g. an MCP client like Claude
    Code) generates BOTH sides of the debate locally — typically by writing
    a deep analysis with full project context, then spawning a fresh
    sub-agent that has only the prompt — and submits both texts here.
    Ploidy persists the debate, classifies the challenge actions, runs
    convergence, and returns the structured result.

    No external API key (PLOIDY_API_BASE_URL) is required. This is the
    recommended single-terminal flow for users who want the
    "deep-thinking + agent debate" experience without setting up a
    separate API account or running two MCP client sessions.

    Args:
        prompt: The decision question being debated.
        deep_position: The deep (full-context) session's stance.
        fresh_position: The fresh (zero-context) session's stance.
        deep_challenge: Optional deep-side critique of the fresh position.
            If omitted, the convergence engine treats this as
            position-only (no challenges exchanged).
        fresh_challenge: Optional fresh-side critique of the deep position.
        context_documents: Optional context attached to the deep session
            for the persisted history.
        deep_label: Display name for the deep role (default "Deep").
        fresh_label: Display name for the fresh role (default "Fresh").

    Returns:
        Complete debate result with synthesis, confidence, and points.
    """
    store = await _init()

    _validate_length(prompt, _MAX_PROMPT_LEN, "prompt")
    _validate_length(deep_position, _MAX_CONTENT_LEN, "deep_position")
    _validate_length(fresh_position, _MAX_CONTENT_LEN, "fresh_position")
    if deep_challenge is not None:
        _validate_length(deep_challenge, _MAX_CONTENT_LEN, "deep_challenge")
    if fresh_challenge is not None:
        _validate_length(fresh_challenge, _MAX_CONTENT_LEN, "fresh_challenge")

    docs = context_documents or []
    if len(docs) > _MAX_CONTEXT_DOCS:
        raise ProtocolError(f"Too many context documents ({len(docs)} > {_MAX_CONTEXT_DOCS})")
    for i, doc in enumerate(docs):
        _validate_length(doc, _MAX_CONTENT_LEN, f"context_documents[{i}]")

    debate_id = uuid.uuid4().hex[:12]
    config = {
        "mode": "solo",
        "deep_label": deep_label,
        "fresh_label": fresh_label,
    }

    # try wraps every persistence step so a partial failure (e.g. the
    # second save_session raising) is rolled back via _delete_failed_debate
    try:
        await store.save_debate(debate_id, prompt, config=config)

        deep_id = f"{debate_id}-deep-{uuid.uuid4().hex[:6]}"
        fresh_id = f"{debate_id}-fresh-{uuid.uuid4().hex[:6]}"
        deep_ctx = SessionContext(
            session_id=deep_id,
            role=SessionRole.DEEP,
            base_prompt=prompt,
            context_documents=docs,
            delivery_mode=DeliveryMode.PASSIVE,
        )
        fresh_ctx = SessionContext(
            session_id=fresh_id,
            role=SessionRole.FRESH,
            base_prompt=prompt,
            context_documents=[],
            delivery_mode=DeliveryMode.NONE,
        )
        await store.save_session(
            deep_id,
            debate_id,
            SessionRole.DEEP.value,
            prompt,
            context_documents=docs,
            delivery_mode=deep_ctx.delivery_mode.value,
        )
        await store.save_session(
            fresh_id,
            debate_id,
            SessionRole.FRESH.value,
            prompt,
            context_documents=[],
            delivery_mode=fresh_ctx.delivery_mode.value,
        )
        _sessions[deep_id] = deep_ctx
        _sessions[fresh_id] = fresh_ctx
        _debate_sessions[debate_id] = [deep_id, fresh_id]
        _session_to_debate[deep_id] = debate_id
        _session_to_debate[fresh_id] = debate_id

        protocol = DebateProtocol(debate_id, prompt)
        _protocols[debate_id] = protocol
        _debate_locks[debate_id] = asyncio.Lock()

        protocol.advance_phase()
        for sid, content in ((deep_id, deep_position), (fresh_id, fresh_position)):
            msg = DebateMessage(
                session_id=sid,
                phase=DebatePhase.POSITION,
                content=content,
                timestamp=_now(),
            )
            protocol.submit_message(msg)
            await store.save_message(debate_id, sid, DebatePhase.POSITION.value, content)

        protocol.advance_phase()

        for sid, content in ((deep_id, deep_challenge), (fresh_id, fresh_challenge)):
            if not content:
                continue
            action = _parse_dominant_action(content)
            ch_msg = DebateMessage(
                session_id=sid,
                phase=DebatePhase.CHALLENGE,
                content=content,
                timestamp=_now(),
                action=action,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(
                debate_id, sid, DebatePhase.CHALLENGE.value, content, action.value
            )

        protocol.advance_phase()

        engine = ConvergenceEngine(use_llm=_USE_LLM_CONVERGENCE)
        session_roles = {deep_id: deep_label, fresh_id: fresh_label}
        result = await engine.analyze(protocol, session_roles)

        protocol.advance_phase()

        points_json = json.dumps(
            [
                {
                    "category": p.category,
                    "summary": p.summary,
                    "session_a_view": p.session_a_view,
                    "session_b_view": p.session_b_view,
                    "resolution": p.resolution,
                    "root_cause": p.root_cause,
                }
                for p in result.points
            ]
        )
        await store.save_convergence_and_complete(
            debate_id,
            result.synthesis,
            result.confidence,
            points_json,
            meta_analysis=result.meta_analysis,
        )
        _cleanup_debate(debate_id)
    except Exception:
        await _delete_failed_debate(store, debate_id)
        raise

    logger.info(
        "Solo debate %s complete (confidence=%.2f, challenges=%d)",
        debate_id,
        result.confidence,
        sum(1 for c in (deep_challenge, fresh_challenge) if c),
    )

    return {
        "debate_id": debate_id,
        "phase": "complete",
        "mode": "solo",
        "config": config,
        "synthesis": result.synthesis,
        "confidence": result.confidence,
        "meta_analysis": result.meta_analysis,
        "points": [
            {
                "category": p.category,
                "summary": p.summary,
                "resolution": p.resolution,
                "root_cause": p.root_cause,
            }
            for p in result.points
        ],
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
    # ── Paper experiment variables ──────────────────────────────────
    deep_n: int = 1,
    fresh_n: int = 1,
    effort: str = "high",
    injection_mode: str = "raw",
    context_pct: int = 100,
    language: str = "en",
    # ── Beyond-paper user customization ─────────────────────────────
    deep_model: str | None = None,
    fresh_model: str | None = None,
) -> dict:
    """Run a complete debate automatically in a single command.

    Creates a debate with Deep(deep_n) × Fresh(fresh_n) sessions,
    generates positions and challenges via API, runs the full protocol,
    and returns the convergence result.

    Requires PLOIDY_API_BASE_URL to be configured.

    Args:
        prompt: The decision question to debate.
        context_documents: Optional documents for the Deep session(s).
        fresh_role: Role for opposing side — 'fresh' or 'semi_fresh'.
        delivery_mode: Context delivery for semi-fresh — 'passive', 'active', or 'selective'.
        pause_at: Optional phase to pause at — 'challenge' or 'convergence'.
        deep_n: Number of Deep sessions (ploidy level, deep side).
        fresh_n: Number of Fresh/Semi-Fresh sessions (ploidy level, fresh side).
        effort: Reasoning depth — 'low', 'medium', 'high', or 'max'.
        injection_mode: How context is formatted — 'raw', 'system_prompt', 'memory',
            'skills', or 'claude_md'.
        context_pct: Percentage of context to retain (0-100).
        language: Output language — 'en', 'ko', 'ja', or 'zh'.
        deep_model: Model override for Deep sessions.
        fresh_model: Model override for Fresh/Semi-Fresh sessions.

    Returns:
        Complete debate result with convergence synthesis, or paused state.
    """
    try:
        from ploidy.api_client import (
            compress_failures_only,
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

    # ── Validate inputs ─────────────────────────────────────────────
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
        "selective": DeliveryMode.SELECTIVE,
    }
    dm = dm_map.get(delivery_mode)
    if dm is None:
        raise ProtocolError(
            f"Invalid delivery_mode '{delivery_mode}'. "
            "Must be 'none', 'passive', 'active', or 'selective'"
        )
    if auto_role == SessionRole.FRESH and dm != DeliveryMode.NONE:
        raise ProtocolError("Fresh auto sessions must use delivery_mode='none'")
    if auto_role == SessionRole.SEMI_FRESH and dm == DeliveryMode.NONE:
        raise ProtocolError("Semi-fresh auto sessions must use 'passive', 'active', or 'selective'")

    if pause_at not in {None, "challenge", "convergence"}:
        raise ProtocolError(f"Invalid pause_at '{pause_at}'. Must be 'challenge' or 'convergence'")
    if deep_n < 1 or fresh_n < 1:
        raise ProtocolError("deep_n and fresh_n must be >= 1")
    if deep_n + fresh_n > _MAX_SESSIONS_PER_DEBATE:
        raise ProtocolError(
            f"Total sessions ({deep_n}+{fresh_n}) exceeds max ({_MAX_SESSIONS_PER_DEBATE})"
        )
    try:
        effort_level = EffortLevel(effort)
    except ValueError:
        raise ProtocolError(f"Invalid effort '{effort}'. Must be low/medium/high/max")
    if injection_mode not in VALID_INJECTION_MODES:
        valid = sorted(VALID_INJECTION_MODES)
        raise ProtocolError(f"Invalid injection_mode '{injection_mode}'. Must be one of {valid}")
    if not (0 <= context_pct <= 100):
        raise ProtocolError("context_pct must be 0..100")
    if language not in VALID_LANGUAGES:
        raise ProtocolError(
            f"Invalid language '{language}'. Must be one of {sorted(VALID_LANGUAGES)}"
        )

    # ── Prepare context with injection mode ─────────────────────────
    # For injection_mode="system_prompt", context goes via system message.
    # For all others, context is formatted and prepended to the user prompt.
    raw_context = "\n\n".join(docs) if docs else ""
    deep_user_prompt, deep_sys_prompt = build_deep_prompt(
        raw_context, prompt, mode=injection_mode, context_pct=context_pct
    )
    deep_user_prompt = append_language(deep_user_prompt, language)
    fresh_prompt = append_language(prompt, language)

    # Build config for persistence
    config = {
        "deep_n": deep_n,
        "fresh_n": fresh_n,
        "effort": effort,
        "injection_mode": injection_mode,
        "context_pct": context_pct,
        "language": language,
        "deep_model": deep_model,
        "fresh_model": fresh_model,
        "fresh_role": fresh_role,
        "delivery_mode": delivery_mode,
    }

    # ── 1. Create debate ────────────────────────────────────────────
    debate_id = uuid.uuid4().hex[:12]
    await store.save_debate(debate_id, prompt, config=config)

    protocol = DebateProtocol(debate_id, prompt)
    _protocols[debate_id] = protocol
    _debate_locks[debate_id] = asyncio.Lock()
    _debate_sessions[debate_id] = []

    # ── 2. Create Deep sessions ─────────────────────────────────────
    deep_sessions: list[SessionContext] = []
    for i in range(deep_n):
        sid = f"{debate_id}-deep-{i}-{uuid.uuid4().hex[:6]}"
        ctx = SessionContext(
            session_id=sid,
            role=SessionRole.DEEP,
            base_prompt=prompt,
            context_documents=docs,
            delivery_mode=DeliveryMode.PASSIVE,
            effort=effort_level,
            model=deep_model,
        )
        await store.save_session(
            sid,
            debate_id,
            "deep",
            prompt,
            context_documents=docs,
            delivery_mode="passive",
            model=deep_model,
            effort=effort,
        )
        _sessions[sid] = ctx
        _debate_sessions[debate_id].append(sid)
        _session_to_debate[sid] = debate_id
        deep_sessions.append(ctx)

    # ── 3. Create Fresh/Semi-Fresh sessions ─────────────────────────
    fresh_sessions: list[SessionContext] = []
    prefix = "sf" if auto_role == SessionRole.SEMI_FRESH else "fresh"
    for i in range(fresh_n):
        sid = f"{debate_id}-{prefix}-{i}-{uuid.uuid4().hex[:6]}"
        ctx = SessionContext(
            session_id=sid,
            role=auto_role,
            base_prompt=prompt,
            context_documents=[],
            delivery_mode=dm,
            effort=effort_level,
            model=fresh_model,
        )
        await store.save_session(
            sid,
            debate_id,
            fresh_role,
            prompt,
            delivery_mode=dm.value,
            model=fresh_model,
            effort=effort,
        )
        _sessions[sid] = ctx
        _debate_sessions[debate_id].append(sid)
        _session_to_debate[sid] = debate_id
        fresh_sessions.append(ctx)

    logger.info(
        "Auto-debate %s: Deep(%d) x %s(%d), effort=%s, injection=%s",
        debate_id,
        deep_n,
        fresh_role,
        fresh_n,
        effort,
        injection_mode,
    )

    try:
        # ── 4. POSITION phase ───────────────────────────────────────
        protocol.advance_phase()  # → POSITION

        # Generate Deep positions (concurrent within group)
        deep_tasks = [
            generate_experienced_position(
                deep_user_prompt,
                context_documents=(None if injection_mode != "raw" or context_pct < 100 else docs),
                effort=effort,
                model=deep_model,
            )
            for _ in range(deep_n)
        ]
        deep_positions = await asyncio.gather(*deep_tasks)

        # For Semi-Fresh: compress Deep positions, then generate
        compressed = None
        if auto_role == SessionRole.SEMI_FRESH:
            deep_aggregate = _aggregate_positions(deep_positions, "Deep")
            if delivery_mode == "selective":
                compressed = await compress_failures_only(deep_aggregate, model=deep_model)
            else:
                compressed = await compress_position(deep_aggregate, model=deep_model)
            for ctx in fresh_sessions:
                ctx.compressed_summary = compressed
                await store.update_session_context(
                    ctx.session_id,
                    compressed_summary=compressed,
                )

        # Generate Fresh/Semi-Fresh positions (concurrent)
        fresh_tasks = []
        for _ in range(fresh_n):
            if auto_role == SessionRole.SEMI_FRESH and compressed:
                fresh_tasks.append(
                    generate_semi_fresh_position(
                        fresh_prompt,
                        compressed,
                        delivery_mode=delivery_mode,
                        effort=effort,
                        model=fresh_model,
                    )
                )
            else:
                fresh_tasks.append(
                    generate_fresh_position(fresh_prompt, effort=effort, model=fresh_model)
                )
        fresh_positions = await asyncio.gather(*fresh_tasks)

        # Persist all positions
        for ctx, pos in zip(deep_sessions, deep_positions):
            msg = DebateMessage(
                session_id=ctx.session_id,
                phase=DebatePhase.POSITION,
                content=pos,
                timestamp=_now(),
            )
            protocol.submit_message(msg)
            await store.save_message(debate_id, ctx.session_id, "position", pos)

        for ctx, pos in zip(fresh_sessions, fresh_positions):
            msg = DebateMessage(
                session_id=ctx.session_id,
                phase=DebatePhase.POSITION,
                content=pos,
                timestamp=_now(),
            )
            protocol.submit_message(msg)
            await store.save_message(debate_id, ctx.session_id, "position", pos)

        # ── HITL: pause before challenge ────────────────────────────
        if pause_at == "challenge":
            paused_ctx = {
                "deep_ids": [s.session_id for s in deep_sessions],
                "fresh_ids": [s.session_id for s in fresh_sessions],
                "deep_positions": list(deep_positions),
                "fresh_positions": list(fresh_positions),
                "fresh_role": fresh_role,
                "delivery_mode": delivery_mode,
                "effort": effort,
                "deep_model": deep_model,
                "fresh_model": fresh_model,
                "paused_phase": "challenge",
                "protocol_phase": protocol.phase.value,
            }
            _paused_debates[debate_id] = paused_ctx
            await store.update_debate_status(debate_id, "paused")
            await store.save_paused_context(debate_id, paused_ctx)
            return {
                "debate_id": debate_id,
                "phase": "paused",
                "paused_before": "challenge",
                "mode": "auto_hitl",
                "config": config,
                "positions": {
                    "deep": [p[:500] for p in deep_positions],
                    "fresh": [p[:500] for p in fresh_positions],
                },
                "message": "Debate paused for human review. Use debate_review to continue.",
            }

        # ── 5. CHALLENGE phase ──────────────────────────────────────
        protocol.advance_phase()  # → CHALLENGE

        deep_aggregate = _aggregate_positions(deep_positions, "Deep")
        fresh_aggregate = _aggregate_positions(
            fresh_positions, fresh_role.replace("_", "-").title()
        )

        # Deep challenges Fresh
        deep_challenge = await generate_challenge(
            own_position=deep_aggregate,
            other_position=fresh_aggregate,
            own_role="deep",
            other_role=fresh_role,
            effort=effort,
            model=deep_model,
        )
        # Fresh challenges Deep
        fresh_challenge = await generate_challenge(
            own_position=fresh_aggregate,
            other_position=deep_aggregate,
            own_role=fresh_role,
            other_role="deep",
            effort=effort,
            model=fresh_model,
        )

        # Record challenge for all sessions in each group.
        # The challenge text is generated from aggregated positions, so all
        # sessions in the same group share the same challenge content.
        deep_action = _parse_dominant_action(deep_challenge)
        fresh_action = _parse_dominant_action(fresh_challenge)

        for ctx in deep_sessions:
            ch_msg = DebateMessage(
                session_id=ctx.session_id,
                phase=DebatePhase.CHALLENGE,
                content=deep_challenge,
                timestamp=_now(),
                action=deep_action,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(
                debate_id,
                ctx.session_id,
                "challenge",
                deep_challenge,
                deep_action.value,
            )

        for ctx in fresh_sessions:
            ch_msg = DebateMessage(
                session_id=ctx.session_id,
                phase=DebatePhase.CHALLENGE,
                content=fresh_challenge,
                timestamp=_now(),
                action=fresh_action,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(
                debate_id,
                ctx.session_id,
                "challenge",
                fresh_challenge,
                fresh_action.value,
            )

        # ── HITL: pause before convergence ──────────────────────────
        if pause_at == "convergence":
            paused_ctx = {
                "deep_ids": [s.session_id for s in deep_sessions],
                "fresh_ids": [s.session_id for s in fresh_sessions],
                "deep_positions": list(deep_positions),
                "fresh_positions": list(fresh_positions),
                "deep_challenge": deep_challenge,
                "fresh_challenge": fresh_challenge,
                "fresh_role": fresh_role,
                "delivery_mode": delivery_mode,
                "effort": effort,
                "deep_model": deep_model,
                "fresh_model": fresh_model,
                "paused_phase": "convergence",
                "protocol_phase": protocol.phase.value,
            }
            _paused_debates[debate_id] = paused_ctx
            await store.update_debate_status(debate_id, "paused")
            await store.save_paused_context(debate_id, paused_ctx)
            return {
                "debate_id": debate_id,
                "phase": "paused",
                "paused_before": "convergence",
                "mode": "auto_hitl",
                "config": config,
                "challenges": {
                    "deep": deep_challenge[:500],
                    "fresh": fresh_challenge[:500],
                },
                "message": "Debate paused for human review. Use debate_review to continue.",
            }

        # ── 6. CONVERGENCE phase ────────────────────────────────────
        protocol.advance_phase()  # → CONVERGENCE

        engine = ConvergenceEngine(use_llm=_USE_LLM_CONVERGENCE)
        session_roles = {}
        for ctx in deep_sessions:
            session_roles[ctx.session_id] = "Deep"
        for ctx in fresh_sessions:
            session_roles[ctx.session_id] = fresh_role.replace("_", "-").title()
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
                    "root_cause": p.root_cause,
                }
                for p in result.points
            ]
        )
        await store.save_convergence_and_complete(
            debate_id,
            result.synthesis,
            result.confidence,
            points_json,
            meta_analysis=result.meta_analysis,
        )
        _cleanup_debate(debate_id)
    except Exception:
        await _delete_failed_debate(store, debate_id)
        raise

    logger.info(
        "Auto-debate %s complete (confidence=%.2f, ploidy=%dn)",
        debate_id,
        result.confidence,
        deep_n,
    )

    return {
        "debate_id": debate_id,
        "phase": "complete",
        "mode": "auto",
        "config": config,
        "synthesis": result.synthesis,
        "confidence": result.confidence,
        "meta_analysis": result.meta_analysis,
        "points": [
            {
                "category": p.category,
                "summary": p.summary,
                "resolution": p.resolution,
                "root_cause": p.root_cause,
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
    await store.clear_paused_context(debate_id)
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

    # Support both old (exp_id/auto_id) and new (deep_ids/fresh_ids) paused context
    deep_ids = ctx.get("deep_ids", [ctx["exp_id"]] if "exp_id" in ctx else [])
    fresh_ids = ctx.get("fresh_ids", [ctx["auto_id"]] if "auto_id" in ctx else [])
    deep_id = deep_ids[0] if deep_ids else None
    auto_id = fresh_ids[0] if fresh_ids else None
    fresh_role = ctx["fresh_role"]

    await store.update_debate_status(debate_id, "active")

    if ctx["paused_phase"] == "challenge":
        # Resume from after positions, before challenges
        deep_positions = ctx.get("deep_positions", [ctx.get("exp_pos", "")])
        fresh_positions = ctx.get("fresh_positions", [ctx.get("auto_pos", "")])
        deep_pos = _aggregate_positions(deep_positions, "Deep")
        auto_pos = _aggregate_positions(fresh_positions, fresh_role.replace("_", "-").title())

        if action == "override" and override_content and auto_id:
            auto_pos = override_content
            msg = DebateMessage(
                session_id=auto_id,
                phase=DebatePhase.POSITION,
                content=auto_pos,
                timestamp=_now(),
            )
            protocol.messages = [
                m
                for m in protocol.messages
                if not (m.session_id == auto_id and m.phase == DebatePhase.POSITION)
            ]
            protocol.submit_message(msg)
            await store.save_message(debate_id, auto_id, "position", auto_pos)

        protocol.advance_phase()  # → CHALLENGE

        effort = ctx.get("effort", "high")
        d_model = ctx.get("deep_model")
        f_model = ctx.get("fresh_model")

        deep_challenge = await generate_challenge(
            own_position=deep_pos,
            other_position=auto_pos,
            own_role="deep",
            other_role=fresh_role,
            effort=effort,
            model=d_model,
        )
        auto_challenge = await generate_challenge(
            own_position=auto_pos,
            other_position=deep_pos,
            own_role=fresh_role,
            other_role="deep",
            effort=effort,
            model=f_model,
        )

        for sid, content in [(deep_id, deep_challenge), (auto_id, auto_challenge)]:
            if sid is None:
                continue
            ch_action = _parse_dominant_action(content)
            ch_msg = DebateMessage(
                session_id=sid,
                phase=DebatePhase.CHALLENGE,
                content=content,
                timestamp=_now(),
                action=ch_action,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(debate_id, sid, "challenge", content, ch_action.value)

    elif ctx["paused_phase"] == "convergence":
        if action == "override" and override_content and auto_id:
            auto_challenge = override_content
            protocol.messages = [
                m
                for m in protocol.messages
                if not (m.session_id == auto_id and m.phase == DebatePhase.CHALLENGE)
            ]
            ch_action = _parse_dominant_action(auto_challenge)
            ch_msg = DebateMessage(
                session_id=auto_id,
                phase=DebatePhase.CHALLENGE,
                content=auto_challenge,
                timestamp=_now(),
                action=ch_action,
            )
            protocol.submit_message(ch_msg)
            await store.save_message(
                debate_id, auto_id, "challenge", auto_challenge, ch_action.value
            )

    # Continue to convergence + complete
    protocol.advance_phase()  # → CONVERGENCE

    engine = ConvergenceEngine(use_llm=_USE_LLM_CONVERGENCE)
    session_roles = {}
    for sid in deep_ids:
        session_roles[sid] = "Deep"
    for sid in fresh_ids:
        session_roles[sid] = fresh_role.replace("_", "-").title()
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
                "root_cause": p.root_cause,
            }
            for p in result.points
        ]
    )
    await store.save_convergence_and_complete(
        debate_id,
        result.synthesis,
        result.confidence,
        points_json,
        meta_analysis=result.meta_analysis,
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
                "root_cause": p.root_cause,
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

    # Default to stdio so MCP clients (Claude Code, etc.) can spawn the server
    # on demand, with no separate lifecycle to manage. Set
    # PLOIDY_TRANSPORT=streamable-http (or sse) for the multi-client
    # cross-session deployment described in the v0.1 architecture doc.
    transport = os.environ.get("PLOIDY_TRANSPORT", "stdio")
    mcp.run(transport=transport)
