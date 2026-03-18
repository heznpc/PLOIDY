"""Session management for Ploidy debates.

Defines the data structures for debate sessions:
- Session roles (experienced, semi-fresh, fresh)
- Session context (what each session knows)
- Context delivery modes (passive, active)

The key design principle: sessions are assigned different context depths
along the Context Asymmetry Spectrum. A deep session gets full context
(project history, prior decisions, accumulated knowledge). A semi-fresh
session gets compressed context (structured digest of prior analysis).
A fresh session gets deliberately limited context (just the decision
prompt and essential background). This N-ary asymmetry is what makes
the debate productive -- ploidy refers to the general concept of
chromosome set count, supporting any number of sessions.
"""

from dataclasses import dataclass, field
from enum import Enum


class SessionRole(Enum):
    """Role of a session within a debate group.

    EXPERIENCED: Full context -- project history, prior decisions, accumulated knowledge.
    SEMI_FRESH: Compressed context -- structured digest of prior analysis, not full narrative.
    FRESH: Zero context -- just the decision prompt and essential background.
    """

    EXPERIENCED = "experienced"
    SEMI_FRESH = "semi_fresh"
    FRESH = "fresh"


class DeliveryMode(Enum):
    """How context is delivered to a session.

    PASSIVE: Context embedded directly in the prompt, always present in context window.
    ACTIVE: Context available via explicit retrieval, not present until requested.
    NONE: No context delivery (Fresh sessions).
    """

    PASSIVE = "passive"
    ACTIVE = "active"
    NONE = "none"


class EffortLevel(Enum):
    """Effort level for LLM reasoning depth.

    Controls the amount of computation the model applies to each response.
    This is an experimental variable that may interact with context asymmetry.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


@dataclass
class SessionContext:
    """The context provided to a debate session.

    Attributes:
        session_id: Unique identifier for this session.
        role: EXPERIENCED (full), SEMI_FRESH (compressed), or FRESH (zero context).
        base_prompt: The decision prompt shared by all sessions.
        context_documents: Additional context documents provided to this session.
        delivery_mode: How context reaches this session (passive/active/none).
        effort: Effort level for LLM reasoning depth.
        compressed_summary: Compressed prior analysis (Semi-Fresh sessions only).
    """

    session_id: str
    role: SessionRole
    base_prompt: str
    context_documents: list[str]
    delivery_mode: DeliveryMode = DeliveryMode.NONE
    effort: EffortLevel = EffortLevel.HIGH
    compressed_summary: str | None = None
    metadata: dict = field(default_factory=dict)
