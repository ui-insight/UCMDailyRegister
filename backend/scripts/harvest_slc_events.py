"""Harvest the U of I Trumba events feed into the configured database.

The scheduled counterpart of the triage page's "Refresh events" button and the
POST /api/v1/slc/harvest endpoint — all three call the same harvest service.
Run it from cron at the deployment layer (see docs/deployment.md, "Scheduled
harvest") so /slc-triage stays fresh and upstream changes to flagged events
are detected without anyone pressing Refresh.

The command is a dry run unless --apply is provided: it fetches the live feed
and reports what a harvest would change, without writing. Output is a single
timestamped line of counts, so cron logs stay grep-able; failures (network
error, feed shape change) print a clear error to stderr and exit nonzero,
leaving existing rows untouched.

An apply run finishes with the ops classify-pending step: events that are new
or whose content changed get an AI needs assessment for /ops-triage (a second
counts line). Classifier trouble — MindRouter down, malformed output — never
fails the harvest; unassessed events are picked up on the next run.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

import httpx

from app.db.engine import async_session_factory
from app.services.harvested_event_service import (
    harvest_trumba_events,
    plan_trumba_harvest,
)
from app.services.ops_event_service import classify_pending_ops_events


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Harvest the U of I Trumba events feed into harvested_events. "
            "The command is a dry run unless --apply is provided."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the harvest to the configured database",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    async with async_session_factory() as session:
        if args.apply:
            summary = await harvest_trumba_events(session)
        else:
            summary = await plan_trumba_harvest(session)

    mode = "APPLY" if args.apply else "DRY RUN"
    stamp = datetime.now().isoformat(timespec="seconds")
    print(
        f"[{mode}] {stamp} fetched={summary.fetched} created={summary.created} "
        f"updated={summary.updated} unchanged={summary.unchanged} "
        f"canceled={summary.canceled} skipped={summary.skipped}"
    )

    if args.apply:
        try:
            async with async_session_factory() as session:
                classification = await classify_pending_ops_events(session)
        except Exception as exc:  # the harvest already succeeded; never fail it
            stamp = datetime.now().isoformat(timespec="seconds")
            print(f"[WARN] {stamp} ops classification failed: {exc}", file=sys.stderr)
        else:
            stamp = datetime.now().isoformat(timespec="seconds")
            print(
                f"[CLASSIFY] {stamp} assessed={classification.assessed} "
                f"failed={classification.failed} pending={classification.pending}"
            )
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    try:
        return asyncio.run(_run(args))
    except (httpx.HTTPError, ValueError) as exc:
        stamp = datetime.now().isoformat(timespec="seconds")
        print(f"[ERROR] {stamp} harvest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
