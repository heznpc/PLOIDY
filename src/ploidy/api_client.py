"""OpenAI-compatible API client for Ploidy v0.2.

Provides automated session generation via any OpenAI-compatible endpoint,
enabling single-terminal debate workflows where the server auto-generates
Fresh or Semi-Fresh responses.

Supported backends (via configurable base_url):
- Anthropic (default)
- OpenAI
- Ollama (local)
- OpenRouter
- Google (Gemini via OpenAI-compatible proxy)

Environment variables:
    PLOIDY_API_BASE_URL: API endpoint URL (None = disabled)
    PLOIDY_API_KEY: API key for authentication
    PLOIDY_API_MODEL: Model identifier (default: claude-opus-4-6)
"""

import asyncio
import logging
import os

logger = logging.getLogger("ploidy.api")

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_API_BASE_URL = os.environ.get("PLOIDY_API_BASE_URL")
_API_KEY = os.environ.get("PLOIDY_API_KEY", "")
_API_MODEL = os.environ.get("PLOIDY_API_MODEL", "claude-opus-4-6")


def is_api_available() -> bool:
    """Check whether the API fallback is configured and available."""
    return _API_BASE_URL is not None and _API_BASE_URL != ""


async def _get_client():
    """Lazily create an AsyncOpenAI client."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError(
            "openai package required for v0.2 API fallback. Install with: pip install ploidy[api]"
        )

    kwargs = {"api_key": _API_KEY or "not-needed", "timeout": 120.0}
    if _API_BASE_URL:
        kwargs["base_url"] = _API_BASE_URL
    return AsyncOpenAI(**kwargs)


async def generate_response(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    effort: str = "high",
    max_tokens: int = 4096,
) -> str:
    """Generate a response from the configured API endpoint.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system-level instruction.
        model: Model override (defaults to PLOIDY_API_MODEL).
        effort: Effort level hint (low/medium/high/max).
        max_tokens: Maximum tokens in response.

    Returns:
        The model's response text.

    Raises:
        ImportError: If openai package is not installed.
        RuntimeError: If API call fails.
    """
    client = await _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Map effort level to max_tokens budget
    effort_tokens = {"low": 1024, "medium": 2048, "high": 4096, "max": 8192}
    effective_max_tokens = effort_tokens.get(effort, max_tokens)

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=model or _API_MODEL,
                messages=messages,
                max_tokens=effective_max_tokens,
            )
        except (IndexError, KeyError, AttributeError) as e:
            raise RuntimeError(
                f"Ploidy API returned malformed response: {e}"
            ) from e
        except Exception as e:
            last_error = e
            # Import error types available at runtime
            retryable = ("RateLimitError", "APITimeoutError", "APIConnectionError")
            if type(e).__name__ in retryable and attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "API call failed (attempt %d/%d, retrying in %.1fs): %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
                continue
            logger.error("API call failed: %s (%s)", e, type(e).__name__)
            raise RuntimeError(f"Ploidy API call failed: {e}") from e

        # Extract response content -- guard against empty/malformed choices
        try:
            content = response.choices[0].message.content or ""
        except (IndexError, KeyError, AttributeError) as e:
            raise RuntimeError(
                f"Ploidy API returned empty or malformed choices: {e}"
            ) from e
        return content
    raise RuntimeError(f"Ploidy API call failed after {_MAX_RETRIES} retries: {last_error}")


async def generate_fresh_position(
    debate_prompt: str,
    effort: str = "high",
    model: str | None = None,
) -> str:
    """Generate a Fresh session position via API.

    The Fresh session receives only the debate prompt with no project context,
    ensuring maximum independence from accumulated biases.

    Args:
        debate_prompt: The decision question to analyze.
        effort: Effort level for reasoning depth.
        model: Optional model override.

    Returns:
        The Fresh session's position text.
    """
    system = (
        "You are participating in a structured debate. You have NO background context "
        "about this system or project. Review based purely on the code/question itself. "
        "List every bug, risk, or issue you can find. Be specific and technical. "
        "For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
    )
    return await generate_response(
        prompt=debate_prompt,
        system_prompt=system,
        effort=effort,
        model=model,
    )


async def generate_experienced_position(
    debate_prompt: str,
    context_documents: list[str] | None = None,
    effort: str = "high",
    model: str | None = None,
) -> str:
    """Generate an Experienced session position via API."""
    context_block = ""
    if context_documents:
        joined = "\n\n".join(context_documents)
        context_block = f"Project context documents:\n{joined}\n\n"

    system = (
        "You are the experienced session in a structured debate. "
        "You have access to project-specific context that the other session may not see. "
        "Incorporate that context explicitly. List every bug, risk, or issue you can find. "
        "Be specific and technical. For each issue, classify your confidence as HIGH, "
        "MEDIUM, or LOW."
    )
    return await generate_response(
        prompt=f"{context_block}Debate prompt:\n{debate_prompt}",
        system_prompt=system,
        effort=effort,
        model=model,
    )


async def generate_semi_fresh_position(
    debate_prompt: str,
    compressed_summary: str,
    delivery_mode: str = "active",
    effort: str = "high",
    model: str | None = None,
) -> str:
    """Generate a Semi-Fresh session position via API.

    The Semi-Fresh session receives compressed context from the Deep session's
    analysis, delivered either passively (in prompt) or actively (after
    independent analysis).

    Args:
        debate_prompt: The decision question to analyze.
        compressed_summary: Compressed summary of Deep session's analysis.
        delivery_mode: 'passive' (summary in prompt) or 'active' (after independent).
        effort: Effort level for reasoning depth.
        model: Optional model override.

    Returns:
        The Semi-Fresh session's position text.
    """
    if delivery_mode == "passive":
        prompt = (
            f"A previous reviewer analyzed this code/system and produced this summary:\n\n"
            f"--- PRIOR ANALYSIS SUMMARY ---\n{compressed_summary}\n--- END SUMMARY ---\n\n"
            f"Now perform your own independent review:\n\n{debate_prompt}\n\n"
            f"Use the prior summary as background context, but form your own conclusions.\n"
            f"List every bug, risk, or issue you can find. Be specific and technical.\n"
            f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW."
        )
    else:  # active
        prompt = (
            f"{debate_prompt}\n\n"
            f"You have NO background context about this system.\n"
            f"However, a previous reviewer has already analyzed this code. "
            f"Their compressed summary is available below if you want to consult it "
            f"AFTER forming your initial assessment.\n\n"
            f"INSTRUCTION: First, write your own independent analysis. "
            f"Then, consult the prior summary and note any additional issues or "
            f"disagreements.\n\n"
            f"List every bug, risk, or issue you can find. Be specific and technical.\n"
            f"For each issue, classify your confidence as HIGH, MEDIUM, or LOW.\n\n"
            f"--- PRIOR ANALYSIS (consult after your independent review) ---\n"
            f"{compressed_summary}\n--- END ---"
        )

    return await generate_response(
        prompt=prompt,
        effort=effort,
        model=model,
    )


async def generate_challenge(
    own_position: str,
    other_position: str,
    own_role: str = "fresh",
    other_role: str = "experienced",
    effort: str = "high",
    model: str | None = None,
) -> str:
    """Generate a challenge response via API.

    Args:
        own_position: This session's position.
        other_position: The other session's position to challenge.
        own_role: This session's role description.
        other_role: The other session's role description.
        effort: Effort level for reasoning depth.
        model: Optional model override.

    Returns:
        The challenge response text.
    """
    if own_role in ("fresh", "semi_fresh"):
        bias_frame = "seems like rationalization or context-anchored bias"
    else:
        bias_frame = "wrong/misleading given project context"

    prompt = (
        f"You previously reviewed this code/system as a {own_role} session and found:\n\n"
        f"{own_position}\n\n"
        f"Now, a {other_role} session found these issues:\n\n{other_position}\n\n"
        f"For EACH of their points, respond with:\n"
        f"- AGREE: valid finding\n"
        f"- CHALLENGE: {bias_frame}, explain why\n"
        f"- SYNTHESIZE: partially right, here's the nuance\n\n"
        f"Also list anything YOU found that THEY missed."
    )
    return await generate_response(prompt=prompt, effort=effort, model=model)


async def compress_position(position: str, model: str | None = None) -> str:
    """Compress a Deep position into a structured summary for Semi-Fresh sessions.

    Args:
        position: The full position text to compress.
        model: Optional model override.

    Returns:
        A compressed summary (max ~300 words).
    """
    return await generate_response(
        prompt=(
            f"Compress the following code review / architecture analysis into a SHORT "
            f"structured summary.\nInclude ONLY:\n"
            f"- Key issues found (one line each)\n"
            f"- Approaches considered\n"
            f"- Constraints mentioned\n\n"
            f"Do NOT include the full reasoning or project narrative. Max 300 words.\n\n"
            f"Analysis to compress:\n{position}"
        ),
        model=model,
    )


async def analyze_convergence(
    debate_prompt: str,
    positions: dict[str, str],
    challenges: list[dict],
    session_roles: dict[str, str],
    model: str | None = None,
) -> str:
    """LLM-based convergence meta-analysis.

    Analyzes WHY sessions disagreed, attributing disagreements to specific
    context factors (e.g., sunk cost bias from project history, missing
    domain constraints in Fresh session).

    Args:
        debate_prompt: The original debate prompt.
        positions: Map of session_id to position text.
        challenges: List of challenge messages with session_id, content, action.
        session_roles: Map of session_id to role name.
        model: Optional model override.

    Returns:
        Structured meta-analysis text.
    """
    parts = [f"## Debate Prompt\n{debate_prompt}\n"]

    for sid, pos in positions.items():
        role = session_roles.get(sid, sid[:8])
        parts.append(f"## {role} Session Position\n{pos}\n")

    if challenges:
        parts.append("## Challenges Exchanged")
        for ch in challenges:
            role = session_roles.get(ch.get("session_id", ""), "Unknown")
            action = ch.get("action", "challenge")
            parts.append(f"\n### {role} ({action}):\n{ch.get('content', '')}")

    transcript = "\n".join(parts)

    return await generate_response(
        prompt=(
            f"You are a meta-analyst evaluating a structured debate between AI sessions "
            f"with different context depths.\n\n"
            f"DEBATE TRANSCRIPT:\n{transcript}\n\n"
            f"Produce a structured analysis:\n\n"
            f"1. **Root Cause of Disagreements**: For each disagreement, identify WHETHER "
            f"it was caused by:\n"
            f"   - Context anchoring (Deep session rationalized due to sunk cost/familiarity)\n"
            f"   - Missing constraints (Fresh session missed domain requirements)\n"
            f"   - Genuine trade-off (both perspectives have merit)\n"
            f"   - Stochastic variance (disagreement is random, not context-driven)\n\n"
            f"2. **Context Attribution**: Which specific pieces of context in the Deep "
            f"session's history caused their position to diverge from the Fresh session?\n\n"
            f"3. **Synthesis**: What is the best decision considering both perspectives?\n\n"
            f"4. **Confidence Assessment**: How confident should the user be in this "
            f"synthesis? (0.0 to 1.0)"
        ),
        model=model,
    )
