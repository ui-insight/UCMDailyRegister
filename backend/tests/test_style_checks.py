"""Unit tests for the deterministic post-edit style detectors."""

from app.utils.style_checks import (
    strip_html,
    detect_unabbreviated_month_dates,
    detect_abbreviated_months_without_date,
    detect_nonstandard_meridiems,
    detect_twelve_oclock_meridiems,
    detect_platform_names,
    detect_undefined_acronyms,
    detect_repeated_cta_phrases,
)


class TestMonthAbbreviation:
    def test_flags_spelled_out_month_with_specific_date(self):
        assert detect_unabbreviated_month_dates("The deadline is October 2.") == ["October 2"]

    def test_accepts_correctly_abbreviated_date(self):
        assert detect_unabbreviated_month_dates("The deadline is Oct. 2.") == []

    def test_accepts_month_with_year_only(self):
        assert detect_unabbreviated_month_dates("Classes start in October 2026.") == []

    def test_accepts_never_abbreviated_months(self):
        assert detect_unabbreviated_month_dates("The fair is March 5.") == []

    def test_flags_abbreviated_month_without_date(self):
        assert detect_abbreviated_months_without_date("Sessions resume in Oct. after break.") == ["Oct."]

    def test_accepts_abbreviated_month_followed_by_date(self):
        assert detect_abbreviated_months_without_date("11 a.m. Wednesday, Sept. 2, online.") == []


class TestMeridiems:
    def test_flags_uppercase_meridiems(self):
        assert detect_nonstandard_meridiems("Join at 9 AM or 3:30 PM.") == ["9 AM", "3:30 PM"]

    def test_flags_lowercase_without_periods(self):
        assert detect_nonstandard_meridiems("Doors open at 7 pm.") == ["7 pm"]

    def test_accepts_ap_style_times(self):
        assert detect_nonstandard_meridiems("The talk runs 3-4 p.m. and ends by 5:15 p.m.") == []

    def test_flags_twelve_oclock_instead_of_noon_or_midnight(self):
        assert detect_twelve_oclock_meridiems("Lunch begins at 12 p.m. sharp.") == ["12 p.m."]

    def test_accepts_noon(self):
        assert detect_twelve_oclock_meridiems("Lunch begins at noon.") == []


class TestPlatformNames:
    def test_flags_zoom(self):
        assert detect_platform_names("Attend via Zoom from anywhere.") == ["Zoom"]

    def test_accepts_online_wording(self):
        assert detect_platform_names("Attend online from anywhere.") == []

    def test_does_not_flag_bare_teams(self):
        assert detect_platform_names("Teams of students compete Friday.") == []


class TestUndefinedAcronyms:
    def test_flags_acronym_never_defined(self):
        assert detect_undefined_acronyms("The NNSA hosts a briefing.") == ["NNSA"]

    def test_accepts_defined_acronym(self):
        body = "The National Nuclear Security Administration (NNSA) hosts a briefing. NNSA staff attend."
        assert detect_undefined_acronyms(body) == []

    def test_skips_roman_numerals_and_known_acronyms(self):
        assert detect_undefined_acronyms("Administrative specialist III, HR office, RSVP required.") == []


class TestRepeatedCta:
    def test_flags_repeated_register_cta(self):
        text = "Register for the workshop today. Space is limited, so register soon."
        assert detect_repeated_cta_phrases(text) == ["register"]

    def test_ignores_the_newsletter_name(self):
        text = "Read the Daily Register and register for the workshop."
        assert detect_repeated_cta_phrases(text) == []

    def test_accepts_single_cta(self):
        assert detect_repeated_cta_phrases("Sign up for the training.") == []


def test_strip_html_removes_tags_but_keeps_anchor_text():
    html = 'Attend <a href="https://example.com/PM">the briefing</a> online.'
    stripped = strip_html(html)
    assert "href" not in stripped
    assert "the briefing" in stripped
    assert detect_nonstandard_meridiems(stripped) == []
