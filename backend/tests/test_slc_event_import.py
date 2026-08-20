"""Tests for the guarded SLC calendar spreadsheet importer."""

from datetime import date, datetime

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from app.models.submission import Submission, SubmissionScheduleRequest
from app.services.slc_event_import_service import (
    DateParseError,
    import_records,
    load_import_plan,
    parse_event_date,
)


def test_parse_event_date_infers_fiscal_year_and_preserves_tentative_range():
    schedules, tentative, source = parse_event_date("2/25-3/7?", 2027)

    assert tentative is True
    assert source == "2/25-3/7?"
    assert schedules[0].start_date == date(2027, 2, 25)
    assert schedules[0].end_date == date(2027, 3, 7)


def test_parse_event_date_accepts_native_excel_date():
    schedules, tentative, _source = parse_event_date(datetime(2026, 8, 26), 2027)

    assert tentative is False
    assert schedules[0].start_date == date(2026, 8, 26)


@pytest.mark.parametrize("source", ["9/17 or 9/24", "3/25 or 4/1 or 4/8?"])
def test_parse_event_date_rejects_alternatives(source: str):
    with pytest.raises(DateParseError, match="require confirmation") as error:
        parse_event_date(source, 2027)

    assert error.value.code == "ambiguous_date"


def test_parse_event_date_rejects_year_outside_fiscal_sheet():
    with pytest.raises(DateParseError, match="outside FY27") as error:
        parse_event_date("11/5/2025?", 2027)

    assert error.value.code == "outside_fiscal_year"


def _write_workbook(path):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "FY27"
    worksheet.append(["Date", "Start Time", "Event", "Location", "Sponsor", "Catatory"])
    worksheet.append([datetime(2026, 8, 19), "8A", "Past event", "Wallace", "AUX", "SLC Leadership"])
    worksheet.append([datetime(2026, 8, 26), None, "Confirmed event", "Boise SUB", "ACMS", "SLC Leadership"])
    worksheet.append(["10/18-10/24", None, "Date range", None, None, "SLC Leadership"])
    worksheet.append(["11/5/26?", "5:30P", "Tentative event", "Ballroom", "Vandals First", "SLC Leadership"])
    worksheet.append(["11/19 or 11/20", "7P", "Ambiguous event", "Auditorium", "ACMS", "Concert"])
    workbook.create_sheet("Metadata")
    workbook.save(path)


def test_load_import_plan_filters_past_and_reports_ambiguous_dates(tmp_path):
    workbook_path = tmp_path / "calendar.xlsx"
    _write_workbook(workbook_path)

    plan = load_import_plan(workbook_path, from_date=date(2026, 8, 20))

    assert [record.title for record in plan.records] == [
        "Confirmed event",
        "Date range",
        "Tentative event",
    ]
    assert plan.records[1].schedules[0].end_date == date(2026, 10, 24)
    assert plan.records[2].tentative is True
    assert plan.records[0].detail_label == "Category"
    assert plan.issue_counts() == {"before_window": 1, "ambiguous_date": 1}


@pytest.mark.asyncio
async def test_import_records_is_idempotent_and_preserves_source_context(tmp_path, db):
    workbook_path = tmp_path / "calendar.xlsx"
    _write_workbook(workbook_path)
    plan = load_import_plan(workbook_path, from_date=date(2026, 8, 20))

    preview = await import_records(db, plan, apply_changes=False)
    first = await import_records(db, plan, apply_changes=True)
    second = await import_records(db, plan, apply_changes=True)

    assert preview.would_insert == 3
    assert first.inserted == 3
    assert second.inserted == 0
    assert second.existing == 3

    submissions = list((await db.execute(select(Submission))).scalars())
    assert len(submissions) == 3
    tentative = next(item for item in submissions if item.Original_Headline == "Tentative event")
    assert tentative.Target_Newsletter == "none"
    assert tentative.Show_In_SLC_Calendar is True
    assert tentative.Status == "pending_info"
    assert "Date status: Tentative" in tentative.Original_Body
    assert "SLC spreadsheet import key:" in tentative.Submitter_Notes

    range_schedule = (
        await db.execute(
            select(SubmissionScheduleRequest)
            .join(Submission)
            .where(Submission.Original_Headline == "Date range")
        )
    ).scalar_one()
    assert range_schedule.Recurrence_Type == "date_range"
    assert range_schedule.Requested_Date == date(2026, 10, 18)
    assert range_schedule.Recurrence_End_Date == date(2026, 10, 24)
    assert (await db.execute(select(func.count()).select_from(Submission))).scalar_one() == 3
