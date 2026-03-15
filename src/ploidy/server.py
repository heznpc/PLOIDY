"""MCP server entry point for Ploidy.

Exposes debate tools via the Model Context Protocol, allowing MCP clients
to initiate debates, submit positions, and retrieve convergence results.

Tools exposed:
- debate/start: Begin a new debate session with a decision prompt
- debate/position: Submit a position from a session
- debate/challenge: Submit a challenge to another session's position
- debate/converge: Trigger convergence analysis
- debate/status: Get current state of a debate
- debate/history: Retrieve past debates and their outcomes
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP(
    "Ploidy",
    version="0.1.0",
    description="Cross-session multi-agent debate MCP server. "
    "Same model, different context depths, better decisions.",
)


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
def debate_start(prompt: str, context_documents: list[str] | None = None) -> dict:
    """Begin a new debate session with a decision prompt.

    Creates a debate and its session group (experienced + fresh).

    Args:
        prompt: The decision question to debate.
        context_documents: Optional documents to give the experienced session.

    Returns:
        Debate and session identifiers.
    """
    return {
        "debate_id": "placeholder-debate-id",
        "experienced_session_id": "placeholder-exp-id",
        "fresh_session_id": "placeholder-fresh-id",
        "phase": "independent",
        "prompt": prompt,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
def debate_position(session_id: str, content: str) -> dict:
    """Submit a position from a session.

    Records a session's stance on the debate prompt during the POSITION phase.

    Args:
        session_id: The session submitting the position.
        content: The position statement.

    Returns:
        Confirmation with current phase info.
    """
    return {
        "session_id": session_id,
        "phase": "position",
        "status": "recorded",
        "content_length": len(content),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        destructiveHint=False,
        readOnlyHint=False,
        idempotentHint=False,
    ),
)
def debate_challenge(session_id: str, content: str, action: str = "challenge") -> dict:
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
    return {
        "session_id": session_id,
        "phase": "challenge",
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
def debate_converge(debate_id: str) -> dict:
    """Trigger convergence analysis for a debate.

    Runs the convergence engine on the debate transcript and produces
    a structured synthesis of agreements and disagreements.

    Args:
        debate_id: The debate to analyze.

    Returns:
        Convergence result with synthesis and confidence score.
    """
    return {
        "debate_id": debate_id,
        "synthesis": "Placeholder synthesis -- not yet implemented.",
        "confidence": 0.0,
        "points": [],
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def debate_status(debate_id: str) -> dict:
    """Get current state of a debate.

    Returns phase, session info, and message counts for a debate.

    Args:
        debate_id: The debate to inspect.

    Returns:
        Current debate status.
    """
    return {
        "debate_id": debate_id,
        "phase": "independent",
        "message_count": 0,
        "sessions": [],
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def debate_history(limit: int = 50) -> dict:
    """Retrieve past debates and their outcomes.

    Lists recent debates with their status and convergence results.

    Args:
        limit: Maximum number of debates to return (default 50).

    Returns:
        List of past debate summaries.
    """
    return {
        "debates": [],
        "total": 0,
        "limit": limit,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Ploidy MCP server."""
    mcp.run()
