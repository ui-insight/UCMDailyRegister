"""The editorial evaluation harness scores outputs correctly (#411).

These tests never call a model: a scripted provider stands in for it, so
they check the cases file, the scoring and the pipeline wiring only.
"""

import re
from datetime import date

import pytest

from app.evals.editorial import (
    CaseRun,
    Check,
    expected_checks,
    SeedRulesEditor,
    load_cases,
    run_case,
    score,
    summarize,
    render_markdown,
)
from app.services.ai.provider import LLMProvider

KNOWN_EXPECTATIONS = {
    "contains",
    "not_contains",
    "body_matches",
    "body_not_matches",
    "headline_matches",
    "headline_not_matches",
    "flag_matches",
    "body_unchanged",
    "no_straight_quotes",
    "headline_not_echo_lead",
}
CASES = load_cases()


def case(case_id: str) -> dict:
    return next(c for c in CASES if c["id"] == case_id)


class ScriptedLLM(LLMProvider):
    model = "scripted"

    def __init__(self, reply: dict):
        self.reply = reply

    async def complete(self, *args, **kwargs):
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return dict(self.reply)


def test_cases_are_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    for c in CASES:
        assert c["newsletter"] in {"tdr", "myui"}, c["id"]
        assert c["issues"] and c["decision"], c["id"]
        date.fromisoformat(c["submitted"])
        assert c["expect"] and set(c["expect"]) <= KNOWN_EXPECTATIONS, c["id"]
        for key in ("body_matches", "body_not_matches", "headline_matches",
                    "headline_not_matches", "flag_matches"):
            for pattern in c["expect"].get(key, []):
                re.compile(pattern)


def test_unchanged_body_passes_and_rewrite_fails():
    notice = case("clear-notice-untouched")
    assert all(check.passed for check in score(notice, notice["headline"], notice["body"], []))
    rewritten = "The Example Library closes early on Nov. 20 for maintenance."
    assert not all(check.passed for check in score(notice, notice["headline"], rewritten, []))


def test_curly_quotes_check_ignores_html_attributes():
    quotes = case("curly-quotes")
    body = (
        '<a href="https://example.edu">The college’s fall lecture</a>, '
        "“Soil and Society,” is at 4 p.m."
    )
    assert all(check.passed for check in score(quotes, quotes["headline"], body, []))
    assert not all(
        check.passed for check in score(quotes, quotes["headline"], 'A "straight" quote', [])
    )


def test_flag_expectation_reads_rule_key_and_message():
    conflict = case("weekday-date-conflict-kept-and-flagged")
    flags = [{"rule_key": "date_conflicts", "message": "Keep the submitted weekday"}]
    checks = score(conflict, conflict["headline"], conflict["body"], flags)
    assert all(check.passed for check in checks)
    assert not all(check.passed for check in score(conflict, "", conflict["body"], []))


@pytest.mark.asyncio
async def test_run_case_scores_the_final_pipeline_output():
    job = case("job-listing-format")
    llm = ScriptedLLM({
        "edited_headline": "",
        "edited_body": "Program coordinator, Example Department",
        "changes_made": ["Removed default location"],
        "flags": [],
        "embedded_links": [],
        "confidence": 0.9,
    })
    result = await run_case(SeedRulesEditor(llm), None, job, run=1)
    assert result.error is None
    assert result.checks and all(check.passed for check in result.checks), result.checks


@pytest.mark.asyncio
async def test_model_error_is_reported_not_raised():
    class FailingLLM(ScriptedLLM):
        async def complete_json(self, *args, **kwargs):
            raise TimeoutError("synthetic timeout")

    result = await run_case(SeedRulesEditor(FailingLLM({})), None, case("can-not-may"), run=1)
    assert result.error and "AIEditError" in result.error


@pytest.mark.asyncio
async def test_summary_keeps_pending_cases_out_of_the_pass_rate():
    passed_case = case("composition-title-protected")
    pending_case = {**case("year-unclear"), "pending": "Synthetic pending marker."}
    llm = ScriptedLLM({
        "edited_headline": "Listen to the new podcast episode",
        "edited_body": passed_case["body"],
        "flags": [],
    })
    runs = [
        await run_case(SeedRulesEditor(llm), None, passed_case, run=1),
        await run_case(SeedRulesEditor(llm), None, pending_case, run=1),
    ]
    summary = summarize([passed_case, pending_case], runs)
    assert summary["checks_passed"] == summary["checks_total"] == 1
    meta = {
        "run_at": "2026-11-06T00:00:00+00:00",
        "provider": "scripted",
        "model": "scripted",
        "rules": "seed",
        "policy_fingerprint": "test",
        "repeat": 1,
    }
    report = render_markdown(meta, summary, runs)
    assert "| composition-title-protected | #396 | pass |" in report
    assert "| year-unclear | #410 | pending |" in report


def test_html_paragraphs_and_breaks_count_as_lines():
    job = case("job-listing-format")
    for body in (
        "<p>Program coordinator, Example Department</p><p>Second line</p>",
        "Program coordinator, Example Department<br>Second line",
    ):
        failed = [c.name for c in score(job, "", body, []) if not c.passed]
        assert "body_not_matches: \\n" in failed, body


def test_invented_multi_digit_room_fails_the_venue_case():
    venue = case("unclear-venue-flagged")
    body = "The staff book club meets at noon Tuesday, Nov. 17, in Room 214."
    flags = [{"rule_key": "protected_names", "message": "[CONFIRM VENUE NAME]"}]
    assert not all(c.passed for c in score(venue, "", body, flags))


def test_summary_counts_each_check_once_per_run_and_errors_as_failures():
    product = case("product-names-protected")
    names = expected_checks(product)
    assert len(names) == 2
    good = CaseRun(product["id"], 1, checks=[Check(n, True) for n in names])
    failed = CaseRun(product["id"], 2, error="TimeoutError: synthetic")
    mixed = summarize([product], [good, failed])
    assert (mixed["checks_passed"], mixed["checks_total"]) == (2, 4)
    assert mixed["cases"][0]["errors"] == 1 and not mixed["cases"][0]["all_passed"]

    all_errors = summarize([product], [failed, CaseRun(product["id"], 3, error="x")])
    assert (all_errors["checks_passed"], all_errors["checks_total"]) == (0, 4)
    assert [c["name"] for c in all_errors["cases"][0]["checks"]] == names
