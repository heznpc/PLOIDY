"""Convergence engine for Ploidy debates.

Analyzes the debate transcript to determine:
- Points of agreement (sessions converged independently)
- Points of productive disagreement (a session raised a valid concern)
- Points of irreducible disagreement (genuinely different values/priorities)

The convergence result is a structured synthesis, not a simple
majority vote. The goal is to surface *why* the sessions disagreed,
since context asymmetry makes disagreements interpretable.
"""

from dataclasses import dataclass

from ploidy.exceptions import ConvergenceError  # noqa: F401
from ploidy.protocol import DebatePhase, DebateProtocol  # noqa: F401


@dataclass
class ConvergencePoint:
    """A single point in the convergence analysis.

    Attributes:
        category: One of 'agreement', 'productive_disagreement', 'irreducible'.
        summary: Brief description of the point.
        session_a_view: How the experienced session sees this point.
        session_b_view: How the fresh session sees this point.
        resolution: The synthesized resolution, if any.
    """

    category: str
    summary: str
    session_a_view: str
    session_b_view: str
    resolution: str | None


@dataclass
class ConvergenceResult:
    """The outcome of a debate's convergence analysis.

    Attributes:
        debate_id: The debate this result belongs to.
        points: Individual convergence points identified.
        synthesis: Overall synthesized recommendation.
        confidence: Confidence score for the synthesis (0.0 to 1.0).
    """

    debate_id: str
    points: list[ConvergencePoint]
    synthesis: str
    confidence: float


class ConvergenceEngine:
    """Analyzes debate transcripts and produces convergence results.

    Takes the full debate protocol (with all messages from all sessions)
    and produces a structured analysis of where and why the sessions
    agreed or disagreed.
    """

    async def analyze(self, protocol: DebateProtocol) -> ConvergenceResult:
        """Run convergence analysis on a completed debate.

        Args:
            protocol: The debate protocol with all messages.

        Returns:
            Structured convergence result.

        Raises:
            ConvergenceError: If the debate is not yet in CONVERGENCE phase.
        """
        pass
