"""Unit tests for the convergence engine."""

import pytest

from ploidy.convergence import ConvergenceEngine
from ploidy.protocol import DebateMessage, DebatePhase, DebateProtocol, SemanticAction


def _make_protocol(
    *,
    phase: DebatePhase = DebatePhase.CONVERGENCE,
    messages: list[DebateMessage] | None = None,
) -> DebateProtocol:
    """Build a minimal DebateProtocol for testing."""
    proto = DebateProtocol(debate_id="test-debate", prompt="Should we use Rust?")
    proto.phase = phase
    if messages:
        proto.messages = messages
    return proto


def _msg(session_id: str, phase: DebatePhase, content: str, action=None) -> DebateMessage:
    return DebateMessage(
        session_id=session_id,
        phase=phase,
        content=content,
        timestamp="2026-01-01T00:00:00",
        action=action,
    )


class TestConvergenceEngine:
    """Tests for rule-based convergence."""

    async def test_wrong_phase_raises(self):
        proto = _make_protocol(phase=DebatePhase.POSITION)
        engine = ConvergenceEngine()
        with pytest.raises(Exception, match="expected convergence"):
            await engine.analyze(proto)

    async def test_no_challenges_produces_irreducible(self):
        proto = _make_protocol(
            messages=[
                _msg("deep", DebatePhase.POSITION, "Rust is fast"),
                _msg("fresh", DebatePhase.POSITION, "Go is simpler"),
            ],
        )
        engine = ConvergenceEngine()
        result = await engine.analyze(proto)
        assert len(result.points) == 1
        assert result.points[0].category == "irreducible"
        assert result.confidence == 0.0

    async def test_agree_action_classified_as_agreement(self):
        proto = _make_protocol(
            messages=[
                _msg("deep", DebatePhase.POSITION, "Rust is fast"),
                _msg("fresh", DebatePhase.POSITION, "Rust is safe"),
                _msg("fresh", DebatePhase.CHALLENGE, "I agree", SemanticAction.AGREE),
            ],
        )
        engine = ConvergenceEngine()
        result = await engine.analyze(proto)
        assert result.points[0].category == "agreement"
        assert result.confidence == 1.0

    async def test_challenge_action_classified_as_disagreement(self):
        proto = _make_protocol(
            messages=[
                _msg("deep", DebatePhase.POSITION, "PostgreSQL is fine"),
                _msg("fresh", DebatePhase.POSITION, "Consider TimescaleDB"),
                _msg("fresh", DebatePhase.CHALLENGE, "Sunk cost fallacy", SemanticAction.CHALLENGE),
            ],
        )
        engine = ConvergenceEngine()
        result = await engine.analyze(proto)
        assert result.points[0].category == "productive_disagreement"
        assert result.confidence == 0.0

    async def test_synthesize_counted_as_agreement(self):
        proto = _make_protocol(
            messages=[
                _msg("deep", DebatePhase.POSITION, "Use PostgreSQL"),
                _msg("fresh", DebatePhase.POSITION, "Use TimescaleDB"),
                _msg("deep", DebatePhase.CHALLENGE, "Both have merit", SemanticAction.SYNTHESIZE),
            ],
        )
        engine = ConvergenceEngine()
        result = await engine.analyze(proto)
        assert result.points[0].category == "agreement"
        assert result.points[0].resolution is not None

    async def test_mixed_actions_confidence(self):
        proto = _make_protocol(
            messages=[
                _msg("deep", DebatePhase.POSITION, "A"),
                _msg("fresh", DebatePhase.POSITION, "B"),
                _msg("fresh", DebatePhase.CHALLENGE, "Agree", SemanticAction.AGREE),
                _msg("deep", DebatePhase.CHALLENGE, "Disagree", SemanticAction.CHALLENGE),
            ],
        )
        engine = ConvergenceEngine()
        result = await engine.analyze(proto)
        assert result.confidence == pytest.approx(0.5)

    async def test_synthesis_text_contains_positions(self):
        proto = _make_protocol(
            messages=[
                _msg("deep", DebatePhase.POSITION, "Rust is fast"),
                _msg("fresh", DebatePhase.POSITION, "Go is simpler"),
                _msg(
                    "fresh", DebatePhase.CHALLENGE, "Speed vs simplicity", SemanticAction.CHALLENGE
                ),
            ],
        )
        engine = ConvergenceEngine()
        roles = {"deep": "Experienced", "fresh": "Fresh"}
        result = await engine.analyze(proto, session_roles=roles)
        assert "Experienced" in result.synthesis
        assert "Fresh" in result.synthesis
        assert "Rust" in result.synthesis


class TestExtractConfidence:
    """Tests for _extract_confidence regex parsing."""

    def setup_method(self):
        self.engine = ConvergenceEngine()

    def test_parses_confidence_colon_format(self):
        assert self.engine._extract_confidence("confidence: 0.85") == pytest.approx(0.85)

    def test_parses_score_format(self):
        assert self.engine._extract_confidence("Overall score: 0.7") == pytest.approx(0.7)

    def test_clamps_above_one(self):
        assert self.engine._extract_confidence("confidence: 1.5") == pytest.approx(1.0)

    def test_returns_none_for_no_match(self):
        assert self.engine._extract_confidence("no numbers here") is None

    def test_handles_integer_one(self):
        assert self.engine._extract_confidence("confidence: 1") == pytest.approx(1.0)

    def test_handles_zero(self):
        assert self.engine._extract_confidence("confidence: 0.0") == pytest.approx(0.0)
