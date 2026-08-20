"""Unit tests for the deterministic post-edit style detectors."""

from datetime import date

from app.utils.style_checks import (
    strip_html,
    detect_unabbreviated_month_dates,
    detect_abbreviated_months_without_date,
    detect_nonstandard_meridiems,
    detect_twelve_oclock_meridiems,
    detect_cross_period_hyphen_ranges,
    detect_event_detail_order_violations,
    detect_disallowed_ampersands,
    detect_platform_names,
    detect_undefined_acronyms,
    detect_repeated_cta_phrases,
    detect_redundant_promotional_leads,
    detect_generic_destination_references,
    detect_indirect_contact_language,
    detect_missing_anchored_requirements,
    detect_missing_contact_titles,
    detect_missing_information_options,
    detect_missing_protected_organizations,
    detect_missing_broad_audience,
    detect_introduced_audience_groups,
    detect_unformatted_composition_titles,
    detect_noncanonical_campus_locations,
    detect_missing_approved_venue_addresses,
    detect_missing_specific_audience_lead,
    detect_missing_source_contacts,
    detect_new_contact_channels,
    detect_new_contact_names,
    detect_changed_official_names,
    detect_missing_relative_date_components,
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

    def test_flags_hyphenated_range_that_crosses_periods(self):
        assert detect_cross_period_hyphen_ranges("Open 11 a.m.-2 p.m.") == [
            "11 a.m.-2 p.m."
        ]

    def test_accepts_hyphenated_range_within_one_period(self):
        assert detect_cross_period_hyphen_ranges("Open 1-2 p.m.") == []


class TestEventDetailsAndAmpersands:
    def test_flags_date_before_time(self):
        sentence = "The workshop is Wednesday, Aug. 26, at 2 p.m. in IRIC 352."
        assert detect_event_detail_order_violations(sentence) == [sentence]

    def test_accepts_time_before_date(self):
        assert detect_event_detail_order_violations(
            "The workshop is at 2 p.m. Wednesday, Aug. 26, in IRIC 352."
        ) == []

    def test_flags_ampersand_in_official_name_but_allows_qa(self):
        assert detect_disallowed_ampersands(
            "The Research & Faculty Development Q&A starts soon."
        ) == ["&"]

    def test_ignores_html_entities(self):
        assert detect_disallowed_ampersands("Research &amp; scholarship") == []


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

    def test_flags_repeated_enrollment_cta(self):
        text = "Employees who enroll qualify. Enroll now."

        assert detect_repeated_cta_phrases(text) == ["enroll"]


class TestActionAndContactLanguage:
    def test_flags_redundant_passive_promotional_lead(self):
        lead = "The last week to have a parking permit reimbursed is this week."

        assert detect_redundant_promotional_leads(lead) == [lead]

    def test_accepts_action_and_benefit_promotional_lead(self):
        assert detect_redundant_promotional_leads(
            "Enroll this week for a chance to have your parking permit reimbursed."
        ) == []

    def test_flags_generic_unlinked_destination_reference(self):
        assert detect_generic_destination_references(
            "Enroll now. See the landing page for details."
        ) == ["landing page"]

    def test_accepts_descriptive_linked_destination(self):
        assert detect_generic_destination_references(
            'Review the <a href="https://example.com">promotion page</a> and enroll.'
        ) == []

    def test_flags_indirect_audience_prefixed_contact_language(self):
        assert detect_indirect_contact_language(
            "Interested participants should contact Betsy Church."
        ) == ["Interested participants should contact"]

    def test_accepts_direct_information_first_contact_language(self):
        assert detect_indirect_contact_language(
            "For more information, contact Betsy Church."
        ) == []


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

    def test_accepts_ampersand_replaced_with_and_in_official_name(self):
        source = "The Research & Faculty Development Office hosts a workshop."
        edited = "The Research and Faculty Development Office hosts a workshop."

        assert detect_changed_official_names(source, edited) == []

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

    def test_flags_removed_comma_style_contact_title(self):
        source = (
            "To schedule, email Laurel Meyer, Education Abroad Advisor & "
            "Outreach/Marketing Coordinator. Email: laurelm@uidaho.edu"
        )
        edited = "To schedule, email Laurel Meyer at laurelm@uidaho.edu."

        assert detect_missing_contact_titles(source, edited) == [
            "Laurel Meyer, education abroad advisor & outreach/marketing coordinator"
        ]

    def test_accepts_comma_style_contact_title_preserved_after_name(self):
        source = (
            "Email Laurel Meyer, Education Abroad Advisor & Outreach/Marketing "
            "Coordinator, at laurelm@uidaho.edu."
        )
        edited = (
            "Email Laurel Meyer, education abroad advisor & outreach/marketing "
            "coordinator, at laurelm@uidaho.edu."
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

    def test_flags_specific_recruitment_group_and_age_range_missing_from_lead(self):
        source = (
            "Researchers are seeking lactating women for a study. Participants must be "
            "between the ages of 18 and 50."
        )
        edited = (
            "Researchers are recruiting participants for a study. Participants must be "
            "18 to 50 years old."
        )

        assert detect_missing_specific_audience_lead(source, edited) == [
            "breastfeeding/lactating women",
            "ages 18-50",
        ]

    def test_accepts_specific_recruitment_group_and_age_range_in_lead(self):
        source = (
            "Researchers are seeking lactating women for a study. Participants must be "
            "between the ages of 18 and 50."
        )
        edited = "Researchers are seeking breastfeeding women ages 18-50 for a study."

        assert detect_missing_specific_audience_lead(source, edited) == []

    def test_ignores_incidental_participant_group_without_recruitment_context(self):
        source = "Volunteers assist participants during the event."
        edited = "Event staff assist participants."

        assert detect_missing_specific_audience_lead(source, edited) == []

    def test_flags_broad_invitation_narrowed_to_employees(self):
        source = "All are welcome to attend the gallery reception."
        edited = "Employees are invited to attend the gallery reception."

        assert detect_missing_broad_audience(source, edited) == ["all are welcome"]

    def test_accepts_direct_invitation_for_broad_audience(self):
        source = "All are welcome to attend the gallery reception."
        edited = "Attend the gallery reception from 4-6 p.m. Wednesday."

        assert detect_missing_broad_audience(source, edited) == []

    def test_flags_audience_group_introduced_by_edit(self):
        assert detect_introduced_audience_groups(
            "Attend the workshop online.",
            "Employees can attend the workshop online.",
        ) == ["employees"]

    def test_accepts_audience_group_present_in_source(self):
        assert detect_introduced_audience_groups(
            "Employees can attend the workshop online.",
            "The workshop is open to employees online.",
        ) == []

    def test_flags_relative_date_or_calendar_date_removed(self):
        source = "Apply today, Aug. 20, for the fellowship."

        assert detect_missing_relative_date_components(
            source,
            "Apply today for the fellowship.",
        ) == ["today, Aug. 20"]
        assert detect_missing_relative_date_components(
            source,
            "Apply Aug. 20 for the fellowship.",
        ) == ["today, Aug. 20"]

    def test_accepts_relative_and_calendar_date_preserved(self):
        assert detect_missing_relative_date_components(
            "Apply today, Aug. 20, for the fellowship.",
            "Apply today, Aug. 20, for the fellowship.",
        ) == []


class TestCompositionAndLocations:
    def test_flags_unquoted_composition_title_in_headline_and_body(self):
        source = 'Attend a screening of the film "Tumbbad."'

        assert detect_unformatted_composition_titles(
            source,
            "Watch a screening of Tumbbad",
            "Watch the film Tumbbad at 7 p.m.",
        ) == ["Tumbbad"]

    def test_accepts_ap_quotes_for_composition_title(self):
        source = 'Attend a screening of the film "Tumbbad."'

        assert detect_unformatted_composition_titles(
            source,
            "Watch a screening of 'Tumbbad'",
            'Watch the film "Tumbbad" at 7 p.m.',
        ) == []

    def test_flags_room_before_known_campus_building(self):
        assert detect_noncanonical_campus_locations(
            "The reception is in Reflections Gallery, ISUB."
        ) == ["ISUB Reflections Gallery"]

    def test_accepts_canonical_building_before_room(self):
        assert detect_noncanonical_campus_locations(
            "The reception is in the ISUB Reflections Gallery."
        ) == []

    def test_flags_missing_approved_off_campus_address(self):
        source = "The film is at the Kenworthy Performing Arts Centre."
        edited = "Watch the film at the Kenworthy Performing Arts Centre."

        assert detect_missing_approved_venue_addresses(source, edited) == [
            "Kenworthy Performing Arts Centre, 508 S. Main St."
        ]

    def test_accepts_approved_off_campus_address(self):
        source = "The film is at the Kenworthy Performing Arts Centre."
        edited = (
            "Watch the film at the Kenworthy Performing Arts Centre, "
            "508 S. Main St."
        )

        assert detect_missing_approved_venue_addresses(source, edited) == []


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
