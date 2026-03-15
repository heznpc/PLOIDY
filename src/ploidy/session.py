"""Session management for Ploidy debates.

Handles the lifecycle of debate sessions, including:
- Creating session groups with varying context levels for a debate
- Managing context injection -- what each session knows
- Tracking session state across the debate lifecycle

The key design principle: sessions are assigned different context depths.
A deep session gets full context (project history, prior decisions,
accumulated knowledge). A fresh session gets deliberately limited context
(just the decision prompt and essential background). Intermediate sessions
can receive partial context. This N-ary asymmetry is what makes the
debate productive -- ploidy refers to the general concept of chromosome
set count, supporting any number of sessions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


class SessionRole(Enum):
    """Role of a session within a debate group.

    EXPERIENCED: Full context -- project history, prior decisions, accumulated knowledge.
    FRESH: Limited context -- just the decision prompt and essential background.
    """

    EXPERIENCED = "experienced"
    FRESH = "fresh"


@dataclass
class SessionContext:
    """The context provided to a debate session.

    Attributes:
        session_id: Unique identifier for this session.
        role: Either EXPERIENCED (full context) or FRESH (limited context).
        base_prompt: The decision prompt shared by all sessions.
        context_documents: Additional context documents provided to this session.
    """

    session_id: str
    role: SessionRole
    base_prompt: str
    context_documents: list[str]


class SessionManager:
    """Manages debate session groups and their context.

    Creates and tracks session groups for each debate, ensuring
    proper context asymmetry between the experienced and fresh sessions.
    """

    def __init__(self, store: "DebateStore") -> None:
        """Initialize the session manager.

        Args:
            store: Persistence layer for session data.
        """
        self.store = store
        self._sessions: dict[str, SessionContext] = {}

    async def create_session_pair(
        self,
        debate_id: str,
        prompt: str,
        full_context: list[str],
    ) -> tuple[SessionContext, SessionContext]:
        """Create an experienced/fresh session pair for a debate.

        Args:
            debate_id: The debate these sessions belong to.
            prompt: The decision prompt for all sessions.
            full_context: Complete context documents (given only to Session A).

        Returns:
            Tuple of (experienced_session, fresh_session).
        """
        experienced = SessionContext(
            session_id=f"{debate_id}-{uuid.uuid4().hex[:8]}",
            role=SessionRole.EXPERIENCED,
            base_prompt=prompt,
            context_documents=full_context,
        )
        fresh = SessionContext(
            session_id=f"{debate_id}-{uuid.uuid4().hex[:8]}",
            role=SessionRole.FRESH,
            base_prompt=prompt,
            context_documents=[],
        )
        self._sessions[experienced.session_id] = experienced
        self._sessions[fresh.session_id] = fresh
        return experienced, fresh

    async def get_session(self, session_id: str) -> SessionContext | None:
        """Retrieve a session by its ID.

        Args:
            session_id: The session to look up.

        Returns:
            The session context, or None if not found.
        """
        return self._sessions.get(session_id)
