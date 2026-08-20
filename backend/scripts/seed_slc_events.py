"""Preview or import an SLC calendar workbook into the configured database."""

from __future__ import annotations

import argparse
import asyncio
import warnings
from datetime import date
from pathlib import Path

from app.db.engine import async_session_factory
from app.services.slc_event_import_service import import_records, load_import_plan


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected an ISO date such as 2026-08-20") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an Auxiliary Services workbook and populate the SLC calendar. "
            "The command is a dry run unless --apply is provided."
        )
    )
    parser.add_argument("spreadsheet", type=Path, help="Path to the .xlsx workbook")
    parser.add_argument(
        "--sheet",
        action="append",
        dest="sheets",
        help="Fiscal-year sheet to import (repeatable; defaults to all FY sheets)",
    )
    parser.add_argument(
        "--from-date",
        type=_iso_date,
        default=date.today(),
        help="Ignore events that end before this date (default: today)",
    )
    parser.add_argument(
        "--through-date",
        type=_iso_date,
        help="Ignore events that start after this date",
    )
    parser.add_argument(
        "--confirmed-only",
        action="store_true",
        help="Exclude source dates marked with a question mark",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit validated, non-duplicate events to the configured database",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    plan = load_import_plan(
        args.spreadsheet,
        sheet_names=args.sheets,
        from_date=args.from_date,
        through_date=args.through_date,
        include_tentative=not args.confirmed_only,
    )
    async with async_session_factory() as session:
        result = await import_records(session, plan, apply_changes=args.apply)

    confirmed = sum(not record.tentative for record in plan.records)
    tentative = len(plan.records) - confirmed
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] {plan.workbook_name}")
    print(f"Validated: {len(plan.records)} events ({confirmed} confirmed, {tentative} tentative)")
    print(f"Existing: {result.existing}")
    if args.apply:
        print(f"Inserted: {result.inserted}")
    else:
        print(f"Would insert: {result.would_insert}")

    if plan.issues:
        counts = ", ".join(
            f"{code}={count}" for code, count in sorted(plan.issue_counts().items())
        )
        print(f"Not imported: {len(plan.issues)} ({counts})")
        for issue in plan.issues:
            if issue.code in {"before_window", "after_window"}:
                continue
            print(
                f"  {issue.sheet_name}!{issue.row_number}: {issue.title} "
                f"[{issue.source_date or 'no date'}] — {issue.message}"
            )
    return 0


def main() -> int:
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    args = _build_parser().parse_args()
    if not args.spreadsheet.is_file():
        raise SystemExit(f"Spreadsheet not found: {args.spreadsheet}")
    if args.through_date and args.through_date < args.from_date:
        raise SystemExit("--through-date cannot be before --from-date")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
