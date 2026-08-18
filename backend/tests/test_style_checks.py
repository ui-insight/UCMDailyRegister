"""Unit tests for the deterministic post-edit style detectors."""

from datetime import date

from app.utils.style_checks import (
    strip_html,
    detect_unabbreviated_month_dates,
    detect_abbreviated_months_without_date,
    detect_nonstandard_meridiems,
    detect_twelve_oclock_meridiems,
    detect_platform_names,
    detect_undefined_acronyms,
    detect_repeated_cta_phrases,
    detect_missing_anchored_requirements,
    detect_missing_contact_titles,
    detect_missing_information_options,
    detect_missing_protected_organizations,
    detect_missing_source_contacts,
    detect_new_contact_channels,
    detect_new_contact_names,
    detect_changed_official_names,
    detect_missing_near_term_weekdays,
    detect_weekday_date_mismatches,
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


class TestSourceFidelity:
    def test_flags_removed_source_contact_and_new_contact_name(self):
        source = "Email dance@uidaho.edu for alternate audition options."
        edited = (
            "Contact Melanie Meenan at melanie@example.com or 208-555-0199 "
            "for alternate audition options."
        )

        assert detect_missing_source_contacts(source, edited) == ["dance@uidaho.edu"]
        assert detect_new_contact_channels(source, edited) == [
            "melanie@example.com",
            "208-555-0199",
        ]
        assert detect_new_contact_names(source, edited) == ["Melanie Meenan"]

    def test_accepts_source_email_preserved_in_mailto_link(self):
        source = "Email dance@uidaho.edu for alternate audition options."
        edited = (
            'Contact the <a href="mailto:dance@uidaho.edu">dance program</a> '
            "for alternate audition options."
        )

        assert detect_missing_source_contacts(source, edited) == []
        assert detect_new_contact_channels(source, edited) == []
        assert detect_new_contact_names(source, edited) == []

    def test_flags_changed_official_and_branded_names(self):
        source = "Audition for UIdaho Dance Ensemble and manage details in VandalStar."
        edited = "Audition for U of I Dance Ensemble and manage details in Vandal Star."

        assert detect_changed_official_names(source, edited) == [
            "UIdaho Dance Ensemble",
            "VandalStar",
        ]

    def test_accepts_exact_official_and_branded_names(self):
        text = "Audition for UIdaho Dance Ensemble and manage details in VandalStar."

        assert detect_changed_official_names(text, text) == []

    def test_official_names_do_not_merge_across_headline_body_boundary(self):
        source = (
            "Learn More About Sustainability on Campus\n"
            "Visit the Office of Sustainability's Inside U of I homepage."
        )
        edited = (
            "Explore campus sustainability resources\n"
            "Visit the Office of Sustainability's Inside U of I homepage."
        )

        assert detect_changed_official_names(source, edited) == []

    def test_flags_missing_sponsor_and_accrediting_organization(self):
        source = (
            "Idaho Eats offers nonprofit groups a fundraising opportunity. "
            "U of I is an Association for Advancement in Sustainability in Higher "
            "Education STARS Gold-rated university."
        )

        assert detect_missing_protected_organizations(
            source,
            "Nonprofit groups can raise funds. U of I is STARS Gold-rated.",
        ) == [
            "Idaho Eats",
            "Association for Advancement in Sustainability in Higher Education",
        ]

    def test_accepts_sponsor_and_accreditor_preserved_in_body(self):
        source = (
            "Idaho Eats offers nonprofit groups a fundraising opportunity. "
            "The designation is administered by National Science Foundation."
        )
        edited = (
            "Nonprofit groups can raise funds through Idaho Eats. The designation "
            "is administered by the National Science Foundation."
        )

        assert detect_missing_protected_organizations(source, edited) == []

    def test_flags_parenthetical_contact_titles_removed_from_linked_names(self):
        source = (
            "Contact Danny Conklin (Concessions Manager) at dconklin@uidaho.edu or "
            "Perry Wenzel (Director of Retail Dining) at pwenzel@uidaho.edu."
        )
        edited = (
            'Contact <a href="mailto:dconklin@uidaho.edu">Danny Conklin</a> or '
            '<a href="mailto:pwenzel@uidaho.edu">Perry Wenzel</a>.'
        )

        assert detect_missing_contact_titles(source, edited) == [
            "Danny Conklin, concessions manager",
            "Perry Wenzel, director of retail dining",
        ]

    def test_accepts_contact_titles_rendered_after_names_in_ap_style(self):
        source = "Contact Danny Conklin (Concessions Manager) at dconklin@uidaho.edu."
        edited = (
            'Contact <a href="mailto:dconklin@uidaho.edu">Danny Conklin</a>, '
            "concessions manager."
        )

        assert detect_missing_contact_titles(source, edited) == []

    def test_does_not_treat_parenthetical_name_or_acronym_as_contact_title(self):
        source = "The University of Idaho (U of I) hosts the event."

        assert detect_missing_contact_titles(source, "U of I hosts the event.") == []

    def test_flags_removed_learn_more_option(self):
        assert detect_missing_information_options(
            "Sign up or learn more by emailing the office.",
            "Sign up by emailing the office.",
        ) == ["learn more"]

    def test_accepts_reworded_information_option(self):
        assert detect_missing_information_options(
            "Sign up or learn more by emailing the office.",
            "Sign up or view details by emailing the office.",
        ) == []

    def test_flags_removed_requirement_with_stable_anchors(self):
        assert detect_missing_anchored_requirements(
            "Applicants must have a 3.0 GPA.",
            "Applications are now open.",
        ) == ["Applicants must have a 3.0 GPA."]

    def test_accepts_reworded_age_and_certification_requirement(self):
        assert detect_missing_anchored_requirements(
            "Cashiers serving alcohol must be 21+ and TIPS certified.",
            "Cashiers serving alcohol are required to be 21 or older and TIPS certified.",
        ) == []


class TestWeekdayDateConsistency:
    def test_flags_near_term_dates_without_weekdays_in_any_context(self):
        assert detect_missing_near_term_weekdays(
            (
                "Enroll by Aug. 22. Registration closes Sept. 10. "
                "Applications are due Aug. 28. The drawing is Aug. 30."
            ),
            reference_date=date(2026, 8, 17),
        ) == ["Aug. 22", "Sept. 10", "Aug. 28", "Aug. 30"]

    def test_accepts_near_term_dates_with_correct_weekdays(self):
        assert detect_missing_near_term_weekdays(
            "Enroll by Saturday, Aug. 22. Applications are due Friday, Aug. 28.",
            reference_date=date(2026, 8, 17),
        ) == []

    def test_ignores_dates_beyond_the_next_thirty_days(self):
        assert detect_missing_near_term_weekdays(
            "Registration closes Sept. 16. Applications are due Sept. 17.",
            reference_date=date(2026, 8, 17),
        ) == ["Sept. 16"]

    def test_resolves_near_term_dates_across_year_boundary(self):
        assert detect_missing_near_term_weekdays(
            "Apply by Jan. 5.",
            reference_date=date(2026, 12, 20),
        ) == ["Jan. 5"]

    def test_flags_weekday_that_disagrees_with_explicit_date(self):
        assert detect_weekday_date_mismatches(
            "Auditions are Thursday, Aug. 25, 2026.",
            reference_date=date(2026, 8, 13),
        ) == ["Thursday, Aug. 25, 2026"]

    def test_accepts_correct_weekday_for_explicit_date(self):
        assert detect_weekday_date_mismatches(
            "Auditions are Tuesday, Aug. 25, 2026.",
            reference_date=date(2026, 8, 13),
        ) == []

    def test_resolves_year_boundary_for_dates_without_year(self):
        assert detect_weekday_date_mismatches(
            "Orientation is Thursday, Jan. 1.",
            reference_date=date(2026, 12, 20),
        ) == ["Thursday, Jan. 1"]

        assert detect_weekday_date_mismatches(
            "Orientation is Friday, Jan. 1.",
            reference_date=date(2027, 1, 1),
        ) == []
