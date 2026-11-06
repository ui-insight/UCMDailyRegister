"""Dates without a year that have passed or whose year is unclear are flagged (#410).

Submission date for every case: Friday, Nov. 6, 2026.
"""

from datetime import date

import pytest

from app.services.ai.editor import AIEditor
from app.utils.style_checks import detect_unconfirmed_dates

SUBMITTED = date(2026, 11, 6)
DATE_RULES = [
    {"rule_key": "date_conflicts", "severity": "error", "category": "dates", "rule_text": "x"},
    {"rule_key": "unconfirmed_dates", "severity": "warning", "category": "dates", "rule_text": "x"},
]


def unconfirmed(text: str, source: str | None = None, **limits) -> dict[str, str]:
    return detect_unconfirmed_dates(
        text if source is None else source, text, reference_date=SUBMITTED, **limits
    )


def test_recently_passed_date_is_flagged_not_moved():
    assert unconfirmed("Open enrollment ends Oct. 15.") == {
        "Oct. 15": "DATE HAS PASSED: CONFIRM DATE"
    }


def test_the_day_before_submission_has_passed():
    assert unconfirmed("Nominations closed Nov. 5.") == {
        "Nov. 5": "DATE HAS PASSED: CONFIRM DATE"
    }


def test_submission_day_and_near_future_are_fine():
    assert unconfirmed("Join us Nov. 6 or Jan. 14 or May 5.") == {}


def test_far_future_date_needs_its_year_confirmed():
    assert unconfirmed("The conference returns Aug. 20.") == {"Aug. 20": "CONFIRM YEAR"}


def test_older_date_rolls_to_next_year_and_needs_its_year_confirmed():
    # Aug. 1 is 97 days back, beyond the passed window, so it means Aug. 1, 2027.
    assert unconfirmed("Applications open Aug. 1.") == {"Aug. 1": "CONFIRM YEAR"}


def test_explicit_year_is_never_flagged():
    assert unconfirmed("The deadline was Oct. 15, 2026, and the next is Aug. 20, 2027.") == {}


def test_limits_are_configurable():
    assert unconfirmed("Ends Oct. 15.", passed_window_days=14) == {"Oct. 15": "CONFIRM YEAR"}
    assert unconfirmed("Returns Aug. 20.", year_unclear_after_days=300) == {}


def test_added_weekday_on_an_unconfirmed_date_is_not_verified():
    found = unconfirmed(
        "The conference returns Friday, Aug. 20.",
        source="The conference returns Aug. 20.",
    )
    assert found == {"Aug. 20": "CONFIRM YEAR; DAY OF WEEK NOT VERIFIED"}


def test_submitted_weekday_is_not_called_unverified():
    found = unconfirmed("The conference returns Friday, Aug. 20.")
    assert found == {"Aug. 20": "CONFIRM YEAR"}


def test_impossible_and_html_dates():
    assert unconfirmed('<a href="x">Feb. 30</a> and <b>Oct. 15</b>') == {
        "Oct. 15": "DATE HAS PASSED: CONFIRM DATE"
    }


def test_a_date_just_before_new_year_has_passed():
    found = detect_unconfirmed_dates(
        "Ended Dec. 31.", "Ended Dec. 31.", reference_date=date(2027, 1, 5)
    )
    assert found == {"Dec. 31": "DATE HAS PASSED: CONFIRM DATE"}


def test_leap_day_uses_its_real_occurrences():
    assert unconfirmed("Leap day party Feb. 29.") == {"Feb. 29": "CONFIRM YEAR"}
    found = detect_unconfirmed_dates(
        "Feb. 29", "Feb. 29", reference_date=date(2028, 3, 1)
    )
    assert found == {"Feb. 29": "DATE HAS PASSED: CONFIRM DATE"}


def test_a_range_ending_in_a_year_is_not_yearless():
    assert unconfirmed("The clinic is closed May 26-30, 2027.") == {}
    assert unconfirmed("Closed Dec. 30\u2013Jan. 2, 2028.") == {}
    assert unconfirmed("The clinic is closed May 26\u201330.") == {"May 26": "CONFIRM YEAR"}


def test_post_analyze_flags_as_a_warning_so_it_never_triggers_repair():
    flags = AIEditor(None).post_analyze(
        "Review benefits before enrollment ends",
        "Open enrollment ends Thursday, Oct. 15.",
        "faculty_staff",
        DATE_RULES,
        source_text="Open enrollment ends Oct. 15.",
        reference_date=SUBMITTED,
    )
    assert {
        "type": "warning",
        "rule_key": "unconfirmed_dates",
        "message": (
            "Confirm this date with the submitter: 'Oct. 15' "
            "[DATE HAS PASSED: CONFIRM DATE; DAY OF WEEK NOT VERIFIED]"
        ),
    } in flags


def test_inactive_rule_silences_the_flag():
    assert AIEditor(None).post_analyze(
        "", "Open enrollment ends Oct. 15.", "faculty_staff", [], reference_date=SUBMITTED
    ) == []


@pytest.mark.asyncio
async def test_unconfirmed_date_warning_does_not_send_the_model_into_repair():
    from app.models.submission import Submission
    from datetime import datetime, timezone

    calls = []

    class OneDraft:
        model = "scripted"

        async def complete_json(self, **kwargs):
            calls.append(kwargs)
            return {
                "edited_headline": "Review benefits before enrollment ends",
                "edited_body": "Open enrollment ends Oct. 15.",
                "flags": [],
            }

    class Editor(AIEditor):
        async def load_style_rules(self, session, newsletter_type):
            return DATE_RULES

    submission = Submission(
        Id="synthetic",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="Benefits",
        Original_Body="Open enrollment ends Oct. 15.",
        Submitter_Name="Synthetic",
        Submitter_Email="synthetic@example.edu",
        Created_At=datetime(2026, 11, 6, 9, tzinfo=timezone.utc),
        Links=[],
    )
    result = await Editor(OneDraft()).edit_submission(None, submission, "tdr")
    assert len(calls) == 1
    assert any(flag["rule_key"] == "unconfirmed_dates" for flag in result.flags)
