"""Render convergence results as answer-first collapsible markdown.

The MCP tool layer used to return raw JSON that the caller stitched into
a human-readable response. That pushes a lot of narrative work onto every
integration. This renderer lets callers surface:

1. A one-line headline with confidence + tallies.
2. The debate synthesis (``synthesis`` as already computed).
3. The full transcript + per-category points + optional LLM meta-analysis,
   all inside ``<details>`` blocks so the caller sees the answer first
   and can expand when curious.

Claude.ai, Claude Desktop, and Claude Code all render markdown with
``<details>`` natively, which makes this the minimum-friction way to
deliver a "Grok Heavy"-style UX without a separate frontend.
"""

from __future__ import annotations

from collections.abc import Sequence

from ploidy.convergence import ConvergencePoint

_CATEGORY_LABELS = {
    "agreement": ("✅", "Agreements"),
    "productive_disagreement": ("🟡", "Productive disagreements"),
    "irreducible": ("🔴", "Irreducible disagreements"),
}


def _aggregate_block(items: Sequence[str], label: str) -> str:
    """Render a list of positions as one block.

    For the common single-position case the label is skipped — the block
    just contains the text — so the reader does not see "Deep 1/1"
    noise when there is nothing to compare it to.
    """
    if len(items) == 1:
        return items[0].strip() or "_(empty)_"
    parts = []
    for i, text in enumerate(items):
        parts.append(f"**{label} {i + 1}/{len(items)}**\n\n{text.strip()}")
    return "\n\n".join(parts)


def _tally(points: Sequence[ConvergencePoint]) -> tuple[int, int, int]:
    agree = sum(1 for p in points if p.category == "agreement")
    prod = sum(1 for p in points if p.category == "productive_disagreement")
    irr = sum(1 for p in points if p.category == "irreducible")
    return agree, prod, irr


def _render_points(points: Sequence[ConvergencePoint]) -> str:
    """One bullet per point, grouped by category with an emoji prefix."""
    if not points:
        return "_(no structured points — positions stand as stated)_"

    grouped: dict[str, list[ConvergencePoint]] = {
        "agreement": [],
        "productive_disagreement": [],
        "irreducible": [],
    }
    for p in points:
        grouped.setdefault(p.category, []).append(p)

    out: list[str] = []
    for category, points_in_cat in grouped.items():
        if not points_in_cat:
            continue
        emoji, label = _CATEGORY_LABELS.get(category, ("❔", category.title()))
        out.append(f"#### {emoji} {label}")
        for p in points_in_cat:
            summary = p.summary.strip().replace("\n", " ")
            line = f"- {summary}"
            if p.resolution:
                resolution = p.resolution.strip().replace("\n", " ")
                line += f"\n  - **Resolution:** {resolution}"
            if p.root_cause:
                root = p.root_cause.strip().replace("\n", " ")
                line += f"\n  - **Root cause:** {root}"
            out.append(line)
    return "\n".join(out)


def render_debate(
    *,
    prompt: str,
    deep_label: str,
    fresh_label: str,
    deep_positions: Sequence[str],
    fresh_positions: Sequence[str],
    deep_challenge: str | None,
    fresh_challenge: str | None,
    points: Sequence[ConvergencePoint],
    synthesis: str,
    confidence: float,
    meta_analysis: str | None = None,
    debate_id: str | None = None,
    mode: str | None = None,
) -> str:
    """Produce the answer-first collapsible markdown for a finished debate."""
    agree, prod, irr = _tally(points)
    confidence_pct = int(round(confidence * 100))

    parts: list[str] = [
        "## Ploidy debate result",
        "",
        (f"**Confidence: {confidence_pct}%** · ✅ {agree} · 🟡 {prod} · 🔴 {irr}"),
        "",
    ]

    # Synthesis already carries the per-category breakdown and positions;
    # show it collapsed by default so the reader sees the confidence line
    # first and only expands when they want the full narrative.
    parts.append("<details>")
    parts.append("<summary><strong>Synthesis</strong></summary>")
    parts.append("")
    parts.append(synthesis.strip())
    parts.append("")
    parts.append("</details>")
    parts.append("")

    parts.append("<details>")
    parts.append("<summary><strong>Full transcript</strong></summary>")
    parts.append("")
    parts.append(f"**Prompt**\n\n{prompt.strip()}")
    parts.append("")
    parts.append(f"### {deep_label} position")
    parts.append(_aggregate_block(list(deep_positions), deep_label))
    parts.append("")
    parts.append(f"### {fresh_label} position")
    parts.append(_aggregate_block(list(fresh_positions), fresh_label))
    if deep_challenge or fresh_challenge:
        parts.append("")
        parts.append("### Challenges")
        if deep_challenge:
            parts.append(f"**{deep_label} → {fresh_label}**\n\n{deep_challenge.strip()}")
        if fresh_challenge:
            parts.append(f"**{fresh_label} → {deep_label}**\n\n{fresh_challenge.strip()}")
    parts.append("")
    parts.append("### Convergence points")
    parts.append(_render_points(points))
    parts.append("")
    parts.append("</details>")

    if meta_analysis:
        parts.append("")
        parts.append("<details>")
        parts.append(
            "<summary><strong>Meta-analysis (root causes of disagreement)</strong></summary>"
        )
        parts.append("")
        parts.append(meta_analysis.strip())
        parts.append("")
        parts.append("</details>")

    if debate_id or mode:
        parts.append("")
        footer_bits = []
        if mode:
            footer_bits.append(f"mode: `{mode}`")
        if debate_id:
            footer_bits.append(f"debate_id: `{debate_id}`")
        parts.append(f"---\n*{' · '.join(footer_bits)}*")

    return "\n".join(parts)
