"""Session management for Ploidy debates.

Defines the data structures for debate sessions:
- Session roles (experienced, semi-fresh, fresh)
- Session context (what each session knows)
- Context delivery modes (passive, active)

Two independent phenomena motivate multi-session debate:

1. **Context asymmetry** (Event A): Sessions at different context depths
   (Deep vs Semi-Fresh vs Fresh) disagree because they have different
   information. Disagreements are interpretable -- one has context the
   other lacks.

2. **Stochastic variance** (Event B): Sessions at the SAME context depth
   produce different outputs due to sampling randomness. Even Deep₁ and
   Deep₂ with identical context may reach opposite conclusions. This is
   the "probability lottery" problem -- a single session locks into one
   stochastic trajectory.

These are independent events. A debate group may contain:
- Deep(n) × Fresh(m): n experienced + m fresh sessions, addressing BOTH
  context asymmetry (Deep vs Fresh) and stochastic variance (n>1 or m>1
  samples from the same context depth)
- Deep(1) × Fresh(1): minimal asymmetric debate (current default)
- Deep(3): three sessions with identical context, pure stochastic sampling

The ploidy metaphor reflects this: in a mixed-ploidy population, diversity
comes from BOTH different chromosome counts (context asymmetry) AND
variation within the same ploidy level (stochastic variance).
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
