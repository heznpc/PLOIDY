"""Convergence engine for Ploidy debates.

Analyzes the debate transcript to determine:
- Points of agreement (sessions converged independently)
- Points of productive disagreement (a session raised a valid concern)
- Points of irreducible disagreement (genuinely different values/priorities)

The convergence result is a structured synthesis, not a simple
majority vote. The goal is to surface *why* the sessions disagreed,
since context asymmetry makes disagreements interpretable.

Supports two modes:
- Rule-based (default): fast, deterministic classification by semantic action
- LLM-enhanced (v0.2): optional meta-analysis explaining root causes of
  disagreements and attributing them to specific context factors
"""

import logging
from dataclasses import dataclass

from ploidy.exceptions import ConvergenceError
from ploidy.protocol import DebatePhase, DebateProtocol, SemanticAction

logger = logging.getLogger("ploidy.convergence")


@dataclass
class ConvergencePoint:
    """A single point in the convergence analysis.

    Attributes:
        category: One of 'agreement', 'productive_disagreement', 'irreducible'.
        summary: Brief description of the point.
        session_a_view: How the experienced session sees this point.
        session_b_view: How the fresh session sees this point.
        resolution: The synthesized resolution, if any.
        root_cause: LLM-attributed root cause of disagreement (v0.2, optional).
    """

    category: str
    summary: str
    session_a_view: str
    session_b_view: str
    resolution: str | None
    root_cause: str | None = None


@dataclass
class ConvergenceResult:
    """The outcome of a debate's convergence analysis.

    Attributes:
        debate_id: The debate this result belongs to.
        points: Individual convergence points identified.
        synthesis: Overall synthesized recommendation.
        confidence: Confidence score for the synthesis (0.0 to 1.0).
        meta_analysis: LLM-generated meta-analysis of why sessions disagreed (v0.2).
    """

    debate_id: str
    points: list[ConvergencePoint]
    synthesis: str
    confidence: float
    meta_analysis: str | None = None


class ConvergenceEngine:
    """Analyzes debate transcripts and produces convergence results.

    Takes the full debate protocol (with all messages from all sessions)
    and produces a structured analysis of where and why the sessions
    agreed or disagreed.

    Args:
        use_llm: If True, use LLM for meta-analysis (requires API client).
    """

    def __init__(self, use_llm: bool = False) -> None:
        """Initialize the convergence engine.

        Args:
            use_llm: Whether to use LLM-enhanced analysis via API client.
        """
        self.use_llm = use_llm

    async def analyze(
        self,
        protocol: DebateProtocol,
        session_roles: dict[str, str] | None = None,
    ) -> ConvergenceResult:
        """Run convergence analysis on a completed debate.

        Collects positions and challenges, classifies them by semantic action,
        and produces a structured synthesis. If use_llm is enabled, also
        generates a meta-analysis explaining why sessions disagreed.

        Args:
            protocol: The debate protocol with all messages.
            session_roles: Optional map of session_id to role display name.

        Returns:
            Structured convergence result.

        Raises:
            ConvergenceError: If the debate is not yet in CONVERGENCE phase.
        """
        if protocol.phase != DebatePhase.CONVERGENCE:
            raise ConvergenceError(
                f"Cannot analyze: debate is in {protocol.phase.value}, expected convergence"
            )

        positions: dict[str, str] = {}
        challenges = []

        for msg in protocol.messages:
            if msg.phase == DebatePhase.POSITION:
                positions[msg.session_id] = msg.content
            elif msg.phase == DebatePhase.CHALLENGE:
                challenges.append(msg)

        session_ids = sorted(positions.keys())

        points: list[ConvergencePoint] = []
        for ch in challenges:
            action = ch.action or SemanticAction.CHALLENGE

            if action in (SemanticAction.AGREE, SemanticAction.SYNTHESIZE):
                category = "agreement"
            else:
                category = "productive_disagreement"

            other_ids = [s for s in session_ids if s != ch.session_id]
            own_view = positions.get(ch.session_id, "")
            other_view = positions.get(other_ids[0], "") if other_ids else ""

            points.append(
                ConvergencePoint(
                    category=category,
                    summary=ch.content[:300],
                    session_a_view=own_view[:500],
                    session_b_view=other_view[:500],
                    resolution=(ch.content if action == SemanticAction.SYNTHESIZE else None),
                )
            )

        if not points and len(session_ids) >= 2:
            points.append(
                ConvergencePoint(
                    category="irreducible",
                    summary="No challenges exchanged — positions stand as stated.",
                    session_a_view=positions.get(session_ids[0], "")[:500],
                    session_b_view=positions.get(session_ids[1], "")[:500],
                    resolution=None,
                )
            )

        agree_count = sum(1 for p in points if p.category == "agreement")
        confidence = agree_count / len(points) if points else 0.0

        synthesis = self._build_synthesis(protocol.prompt, positions, points, session_roles)

        # LLM-enhanced meta-analysis (v0.2)
        meta_analysis = None
        if self.use_llm:
            meta_analysis = await self._llm_meta_analysis(
                protocol.prompt, positions, challenges, session_roles
            )
            # Optionally update confidence from LLM assessment
            if meta_analysis:
                llm_confidence = self._extract_confidence(meta_analysis)
                if llm_confidence is not None:
                    confidence = (confidence + llm_confidence) / 2.0

        return ConvergenceResult(
            debate_id=protocol.debate_id,
            points=points,
            synthesis=synthesis,
            confidence=confidence,
            meta_analysis=meta_analysis,
        )

    async def _llm_meta_analysis(
        self,
        prompt: str,
        positions: dict[str, str],
        challenges: list,
        session_roles: dict[str, str] | None = None,
    ) -> str | None:
        """Generate LLM-based meta-analysis explaining why sessions disagreed.

        Uses the API client to call an LLM for deep analysis of disagreement
        root causes, attributing them to specific context factors.

        Args:
            prompt: The original debate prompt.
            positions: Map of session_id to position text.
            challenges: List of challenge messages.
            session_roles: Optional map of session_id to role name.

        Returns:
            Meta-analysis text, or None if API is unavailable.
        """
        try:
            from ploidy.api_client import analyze_convergence, is_api_available

            if not is_api_available():
                logger.info("LLM meta-analysis skipped: API not configured")
                return None

            challenge_dicts = [
                {
                    "session_id": ch.session_id,
                    "content": ch.content,
                    "action": ch.action.value if ch.action else "challenge",
                }
                for ch in challenges
            ]

            return await analyze_convergence(
                debate_prompt=prompt,
                positions=positions,
                challenges=challenge_dicts,
                session_roles=session_roles or {},
            )
        except ImportError:
            logger.debug("openai package not available, skipping LLM meta-analysis")
            return None
        except Exception as e:
            logger.warning("LLM meta-analysis failed: %s", e)
            return None

    def _extract_confidence(self, meta_analysis: str) -> float | None:
        """Extract confidence score from LLM meta-analysis text.

        Args:
            meta_analysis: The meta-analysis text to parse.

        Returns:
            Confidence score (0.0-1.0), or None if not found.
        """
        import re

        match = re.search(r"(?:confidence|score)[:\s]*([01]\.?\d*)", meta_analysis.lower())
        if match:
            try:
                val = float(match.group(1))
                return max(0.0, min(1.0, val))
            except ValueError:
                pass
        return None

    def _build_synthesis(
        self,
        prompt: str,
        positions: dict[str, str],
        points: list[ConvergencePoint],
        session_roles: dict[str, str] | None = None,
    ) -> str:
        """Build a human-readable synthesis from debate data.

        Args:
            prompt: The original debate prompt.
            positions: Map of session_id to position content.
            points: Classified convergence points.
            session_roles: Optional map of session_id to role name.

        Returns:
            Formatted synthesis text.
        """
        roles = session_roles or {}
        parts = [f"## Debate: {prompt}\n"]

        for sid, pos in positions.items():
            role = roles.get(sid, f"Session {sid[:8]}")
            parts.append(f"### {role} Session Position\n{pos}\n")

        agree = [p for p in points if p.category == "agreement"]
        disagree = [p for p in points if p.category != "agreement"]

        parts.append("### Analysis")
        parts.append(f"- {len(points)} point(s) analyzed")
        parts.append(f"- {len(agree)} agreement(s), {len(disagree)} disagreement(s)")

        if agree:
            parts.append("\n### Agreements")
            for p in agree:
                parts.append(f"- {p.summary}")

        if disagree:
            parts.append("\n### Productive Disagreements")
            for p in disagree:
                parts.append(f"- {p.summary}")
                if p.root_cause:
                    parts.append(f"  Root cause: {p.root_cause}")

        return "\n".join(parts)
