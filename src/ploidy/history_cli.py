"""Terminal browser for past debates — ``ploidy-history`` command.

Queries the local SQLite DB directly (same path the dashboard uses) so
the server does not need to be running. Two subcommands:

- ``ploidy-history`` or ``ploidy-history list`` — most-recent-first
  table of debates (id / status / confidence / prompt preview).
- ``ploidy-history show <debate-id-or-prefix>`` — synthesis, confidence,
  and per-category convergence points for one debate.

Intentionally zero-dependency: stdlib only. The goal is "quick check
from zsh"; the full-interactivity UI is what ``ploidy-dashboard``
covers on port 8766.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from ploidy.store import DebateStore


def _truncate(text: str, width: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= width:
        return cleaned
    return cleaned[: width - 1] + "…"


def _format_table(rows: list[list[str]], headers: list[str]) -> str:
    """Pure-stdlib table formatter — avoids pulling in ``rich`` just for
    one report."""
    all_rows = [headers, *rows]
    widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
    sep = "  "

    def line(cells: list[str]) -> str:
        return sep.join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    out = [line(headers), line(["-" * w for w in widths])]
    out.extend(line(r) for r in rows)
    return "\n".join(out)


async def _list_debates(args: argparse.Namespace) -> int:
    store = DebateStore()
    await store.initialize()
    try:
        debates = await store.list_debates(limit=args.limit)
        if not debates:
            print("No debates yet.")
            return 0

        rows: list[list[str]] = []
        for d in debates:
            conv = await store.get_convergence(d["id"])
            conf = ""
            if conv and conv.get("confidence") is not None:
                conf = f"{int(conv['confidence'] * 100)}%"
            rows.append(
                [
                    d["id"],
                    d.get("status", "?"),
                    conf,
                    _truncate(d.get("prompt", ""), 60),
                    d.get("updated_at", "")[:19],
                ]
            )
        print(_format_table(rows, ["debate_id", "status", "conf", "prompt", "updated"]))
        return 0
    finally:
        await store.close()


def _resolve_debate_id(debates: list[dict], prefix: str) -> str | None:
    matches = [d["id"] for d in debates if d["id"].startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    return None


async def _show_debate(args: argparse.Namespace) -> int:
    store = DebateStore()
    await store.initialize()
    try:
        debate = await store.get_debate(args.debate_id)
        if debate is None:
            # Accept a prefix when the exact id does not hit.
            debates = await store.list_debates(limit=200)
            resolved = _resolve_debate_id(debates, args.debate_id)
            if resolved is None:
                print(f"No debate matches {args.debate_id!r}.", file=sys.stderr)
                return 1
            debate = await store.get_debate(resolved)
        if debate is None:
            print(f"Debate {args.debate_id} not found.", file=sys.stderr)
            return 1

        conv = await store.get_convergence(debate["id"])
        print(f"# Debate {debate['id']}")
        print(f"Prompt: {debate['prompt']}")
        print(f"Status: {debate['status']}")
        print(f"Updated: {debate.get('updated_at', '?')}")
        print()

        if conv is None:
            print("(No convergence result yet.)")
            return 0

        conf = int((conv.get("confidence") or 0) * 100)
        print(f"Confidence: {conf}%")
        print()
        print("## Synthesis")
        print(conv.get("synthesis", "(empty)"))
        print()

        points_json = conv.get("points_json") or "[]"
        try:
            points = json.loads(points_json)
        except json.JSONDecodeError:
            points = []

        if points:
            print("## Convergence points")
            for p in points:
                cat = p.get("category", "?")
                summary = p.get("summary", "")
                print(f"- [{cat}] {summary}")
                if p.get("resolution"):
                    print(f"    resolution: {p['resolution']}")
                if p.get("root_cause"):
                    print(f"    root cause: {p['root_cause']}")
        return 0
    finally:
        await store.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ploidy-history",
        description="Browse past debates from the local Ploidy SQLite DB.",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="Show recent debates (default).")
    p_list.add_argument("--limit", type=int, default=20)

    p_show = sub.add_parser("show", help="Show synthesis + points for one debate.")
    p_show.add_argument("debate_id", help="Full debate id or a unique prefix.")
    return parser


async def run(argv: list[str] | None = None) -> int:
    """Async entry point. ``main()`` wraps this with ``asyncio.run``.

    Split this way so pytest-asyncio tests can ``await run(...)``
    directly instead of fighting with the outer event loop.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd in (None, "list"):
        if args.cmd is None:
            args.limit = 20
        return await _list_debates(args)
    if args.cmd == "show":
        return await _show_debate(args)
    parser.print_help()
    return 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    sys.exit(main())
