"""Context injection modes and language instructions for Ploidy debates.

Controls how context is formatted and delivered to Deep sessions. The *form*
of context delivery affects model behavior independently of content:
- Memory-style (accumulated observations) may produce stronger anchoring
- System-prompt delivery may create positional authority bias
- Declarative rules may be treated as external constraints rather than beliefs

Extracted from ``experiments/run_experiment.py`` to share between the
experiment runner and the MCP server.
"""

INJECTION_MODES = {
    "raw": {
        "description": "Raw context in user prompt (baseline)",
        "format": lambda ctx: f"Context about this code/system:\n{ctx}",
    },
    "system_prompt": {
        "description": "Context as system-level instruction",
        "format": lambda ctx: (
            f"You are a senior engineer with deep knowledge of this system. "
            f"You have the following project context that informs your analysis:\n\n{ctx}"
        ),
    },
    "memory": {
        "description": "Context as accumulated memories (CLAUDE.md / memory.md style)",
        "format": lambda ctx: (
            "The following memories were accumulated from your prior work sessions "
            "on this project. They represent observations, decisions, and lessons "
            "learned over time:\n\n"
            "---\n"
            "## Project Memory\n\n"
            + "\n".join(
                f"- **Observation #{i + 1}**: {line}"
                for i, line in enumerate(
                    s.strip() for s in ctx.strip().split("\n") if s.strip()
                )
            )
            + "\n---"
        ),
    },
    "skills": {
        "description": "Context as declarative rules/capabilities (skills.md style)",
        "format": lambda ctx: (
            "# Project Skills & Rules\n\n"
            "When analyzing this codebase, apply the following rules and constraints:\n\n"
            + "\n".join(
                f"- RULE: {line.strip()}" for line in ctx.strip().split("\n") if line.strip()
            )
        ),
    },
    "claude_md": {
        "description": "Context as CLAUDE.md project instructions",
        "format": lambda ctx: (
            f"<project-instructions>\n"
            f"# CLAUDE.md\n\n"
            f"## Project Context\n\n{ctx}\n\n"
            f"## Conventions\n"
            f"- Be thorough in code review\n"
            f"- Flag all security issues\n"
            f"- Consider operational context\n"
            f"</project-instructions>"
        ),
    },
}

VALID_INJECTION_MODES = frozenset(INJECTION_MODES.keys())

LANGUAGE_INSTRUCTIONS = {
    "en": "",
    "ko": "\n\n한국어로 답변하세요. 기술적 용어는 가능한 한 한국어로 번역하세요.",
    "ja": "\n\n日本語で回答してください。技術用語はできる限り日本語に翻訳してください。",
    "zh": "\n\n请用中文回答。尽可能将技术术语翻译成中文。",
}

VALID_LANGUAGES = frozenset(LANGUAGE_INSTRUCTIONS.keys())


def format_context(context: str, mode: str = "raw") -> str:
    """Format context string using the specified injection mode.

    Args:
        context: Raw context string.
        mode: Injection mode key (raw/system_prompt/memory/skills/claude_md).

    Returns:
        Formatted context string.
    """
    if mode not in INJECTION_MODES:
        mode = "raw"
    return INJECTION_MODES[mode]["format"](context)


def get_system_prompt_for_mode(context: str, mode: str = "raw") -> str | None:
    """Return system prompt if injection mode uses it, else None.

    For system_prompt mode, context is delivered via the system message
    rather than the user prompt. For all other modes, returns None.

    Args:
        context: Raw context string.
        mode: Injection mode key.

    Returns:
        System prompt string if mode is 'system_prompt', else None.
    """
    if mode == "system_prompt":
        return format_context(context, mode)
    return None


def build_deep_prompt(
    context: str,
    prompt: str,
    mode: str = "raw",
    context_pct: int = 100,
) -> tuple[str, str | None]:
    """Build the Deep session user prompt and optional system prompt.

    For system_prompt mode, context goes into the system message and the
    user prompt contains only the task. For all other modes, formatted
    context is prepended to the user prompt.

    Args:
        context: Raw context string (will be truncated per context_pct).
        prompt: The task/decision prompt.
        mode: Injection mode key.
        context_pct: Percentage of context to retain (0-100).

    Returns:
        Tuple of (user_prompt, system_prompt_or_none).
    """
    truncated = truncate_context(context, context_pct)
    if not truncated:
        return prompt, None

    if mode == "system_prompt":
        return prompt, format_context(truncated, mode)

    formatted = format_context(truncated, mode)
    return f"{formatted}\n\n{prompt}", None


def truncate_context(context: str, pct: int) -> str:
    """Truncate context to a given percentage, snapping to sentence boundaries.

    Args:
        context: Full context string.
        pct: Percentage of context to retain (0-100).

    Returns:
        Truncated context string.
    """
    if pct >= 100:
        return context
    if pct <= 0:
        return ""
    target_len = int(len(context) * pct / 100)
    truncated = context[:target_len]
    last_period = truncated.rfind(".")
    if last_period > target_len * 0.7:
        return truncated[: last_period + 1]
    return truncated


def append_language(prompt: str, language: str = "en") -> str:
    """Append language instruction to a prompt if not English.

    Args:
        prompt: The prompt text.
        language: Language code (en/ko/ja/zh).

    Returns:
        Prompt with language instruction appended (unchanged for 'en').
    """
    suffix = LANGUAGE_INSTRUCTIONS.get(language, "")
    if suffix:
        return f"{prompt}{suffix}"
    return prompt
