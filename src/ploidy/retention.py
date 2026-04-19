"""Manual retention CLI.

Usage::

    python -m ploidy.retention purge --days 30
    python -m ploidy.retention vacuum

The server already runs retention on an interval when ``PLOIDY_RETENTION_DAYS``
is set; this CLI exists for ops who want to run an ad-hoc cleanup without
restarting the server.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from ploidy.service import DebateService
from ploidy.store import DebateStore

logger = logging.getLogger("ploidy.retention")


async def _purge(days: int, vacuum: bool) -> int:
    store = DebateStore()
    svc = DebateService(
        store=store,
        retention_days=days,
        retention_vacuum=vacuum,
    )
    await svc.initialize()
    try:
        # initialize() normally also spawns the background loop; cancel it so
        # only the explicit one-shot runs for the CLI.
        if svc._retention_task is not None:
            svc._retention_task.cancel()
            try:
                await svc._retention_task
            except (asyncio.CancelledError, Exception):
                pass
            svc._retention_task = None
        return await svc.run_retention_once()
    finally:
        await svc.shutdown()


async def _vacuum_only() -> None:
    store = DebateStore()
    await store.initialize()
    try:
        await store.vacuum()
    finally:
        await store.close()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(prog="ploidy.retention")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_purge = sub.add_parser("purge", help="Delete completed/cancelled debates older than --days")
    p_purge.add_argument("--days", type=int, required=True)
    p_purge.add_argument("--no-vacuum", action="store_true")

    sub.add_parser("vacuum", help="Run VACUUM to reclaim space")

    args = parser.parse_args(argv)

    if args.cmd == "purge":
        removed = asyncio.run(_purge(args.days, vacuum=not args.no_vacuum))
        logger.info("Purged %d debate(s)", removed)
        return 0
    if args.cmd == "vacuum":
        asyncio.run(_vacuum_only())
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
