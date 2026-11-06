"""Dates without a year that have passed or whose year is unclear are flagged (#410).

Submission date for every case: Friday, Nov. 6, 2026.
"""

from datetime import date

from app.services.ai.editor import AIEditor
from app.utils.style_checks import detect_unconfirmed_dates

SUBMITTED = date(2026, 11, 6)
DATE_RULES = [
    {"rule_key": "date_conflicts", "severity": "error", "category": "dates", "rule_text": "x"},
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
        "rule_key": "date_conflicts",
        "message": (
            "Confirm this date with the submitter: 'Oct. 15' "
            "[DATE HAS PASSED: CONFIRM DATE; DAY OF WEEK NOT VERIFIED]"
        ),
    } in flags


def test_inactive_rule_silences_the_flag():
    assert AIEditor(None).post_analyze(
        "", "Open enrollment ends Oct. 15.", "faculty_staff", [], reference_date=SUBMITTED
    ) == []
