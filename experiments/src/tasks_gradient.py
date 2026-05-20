"""Context-length gradient task variants for H2 threshold measurement.

Honours the 2026-05-21 pre-registration amendment in
``planning/decisions.md``: the H2 replication carries a context-length
gradient (short ≈ 500 tokens / medium ≈ 1000 tokens / long = full) so
the entrenchment threshold predicted in §sec:threshold of the paper
can be located rather than just described qualitatively.

The 10 base tasks are reused at three length tiers each, yielding 30
variants. Tier ``long`` is the original task verbatim. Tiers ``medium``
and ``short`` are produced by ``_truncate_for_tier``, which preserves
the last ``## ``-prefixed section (typically "Decision under review")
verbatim — this is the prompt's anchoring trigger — and trims the
middle "Recent operational history" / team-narrative material from
the start until the target chars budget is reached. A visible marker
``[... context truncated for gradient experiment ...]`` is inserted at
the truncation point so the artefact remains self-describing.

Base task selection (10 total = 3 external + 3 original + 4 expansion):

  External (anti-circularity gate):
    ext_gitlab_2017_db_posture
    ext_github_2018_mysql_topology
    ext_knight_2012_smars_deploy

  Original long-context (paper §sec:exp2):
    long_db_migration
    long_auth_overhaul
    long_microservice_split

  Expansion long-context (the ~2k-token tier):
    long_custom_orm
    long_event_driven
    long_k8s_simple_app
    long_shared_config

External-source fraction in the gradient base set: 3/10 = 30 %,
matching the pre-registered ≥30 % external-source gate.
"""

from __future__ import annotations

from task_model import Task
from tasks_external import EXTERNAL_TASKS
from tasks_longcontext import LONG_CONTEXT_TASKS

SHORT_TARGET_CHARS = 2000  # ≈ 500 tokens at the chars-per-token ≈ 4 heuristic
MEDIUM_TARGET_CHARS = 4000  # ≈ 1000 tokens
TRUNCATION_MARKER = "\n\n[...earlier sections of project history elided for brevity...]\n"

BASE_TASK_IDS: tuple[str, ...] = (
    "ext_gitlab_2017_db_posture",
    "ext_github_2018_mysql_topology",
    "ext_knight_2012_smars_deploy",
    "long_db_migration",
    "long_auth_overhaul",
    "long_microservice_split",
    "long_custom_orm",
    "long_event_driven",
    "long_k8s_simple_app",
    "long_shared_config",
)


def _truncate_for_tier(context: str, target_chars: int) -> str:
    """Truncate ``context`` to roughly ``target_chars`` while preserving the
    trailing ``## ``-prefixed section (the prompt's anchoring trigger).
    """
    if len(context) <= target_chars:
        return context

    last_section_idx = context.rfind("\n## ")
    if last_section_idx == -1 or last_section_idx >= target_chars - 200:
        # No clean tail section, or the tail is too far in. Just hard-cut
        # the end and tag the truncation.
        return context[: max(0, target_chars - len(TRUNCATION_MARKER))] + TRUNCATION_MARKER

    tail = context[last_section_idx:]
    if len(tail) >= target_chars:
        # Tail alone exceeds the target — return tail truncated. This is
        # rare; flagged so the gradient runner can skip rather than emit
        # a degenerate variant.
        return tail[: target_chars - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER

    head_budget = target_chars - len(tail) - len(TRUNCATION_MARKER)
    return context[:head_budget] + TRUNCATION_MARKER + tail


def _by_id(tasks: list[Task]) -> dict[str, Task]:
    return {t.id: t for t in tasks}


def _gather_base_tasks() -> list[Task]:
    by_id = {**_by_id(LONG_CONTEXT_TASKS), **_by_id(EXTERNAL_TASKS)}
    missing = [tid for tid in BASE_TASK_IDS if tid not in by_id]
    if missing:
        raise RuntimeError(
            "tasks_gradient: missing base task ids in source modules: " + ", ".join(missing)
        )
    return [by_id[tid] for tid in BASE_TASK_IDS]


def _make_variant(base: Task, tier: str, context: str) -> Task:
    return Task(
        id=f"{base.id}__{tier}",
        name=f"{base.name} [{tier}]",
        context=context,
        prompt=base.prompt,
        ground_truth=list(base.ground_truth),
        domain=base.domain,
    )


def build_gradient_tasks() -> list[Task]:
    """Expand the 10 base tasks into 30 short/medium/long variants."""
    out: list[Task] = []
    for base in _gather_base_tasks():
        out.append(
            _make_variant(base, "short", _truncate_for_tier(base.context, SHORT_TARGET_CHARS))
        )
        out.append(
            _make_variant(base, "medium", _truncate_for_tier(base.context, MEDIUM_TARGET_CHARS))
        )
        out.append(_make_variant(base, "long", base.context))
    return out


GRADIENT_TASKS: list[Task] = build_gradient_tasks()


if __name__ == "__main__":  # pragma: no cover
    # Smoke-print the resulting tier sizes.
    print(f"{len(GRADIENT_TASKS)} gradient variants from {len(BASE_TASK_IDS)} base tasks")
    print(f"{'id':<55} {'tier':<7} {'chars':>6} ~tokens")
    for t in GRADIENT_TASKS:
        tier = t.id.rsplit("__", 1)[-1]
        approx_tokens = len(t.context) // 4
        print(f"{t.id:<55} {tier:<7} {len(t.context):>6} ~{approx_tokens}")
