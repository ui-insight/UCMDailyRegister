"""Deterministic checks run on the AI-edited copy, one function per rule.

Prompt instructions alone don't guarantee the model follows a rule, so the
mechanically verifiable rules are re-checked after every edit. Each check
here reads a ``CheckContext`` and returns ``Finding`` values naming the rule
they enforce. ``AIEditor.post_analyze`` keeps only findings whose rule is
active and decides their severity, so deactivating a rule in the app also
silences its check.

To add a check for a new editorial decision, write one function and append
it to ``OUTPUT_CHECKS`` (it reads only the edited copy) or ``SOURCE_CHECKS``
(it compares the edit with the submission; skipped when there is no
source). The order of the lists is the order flags are shown to editors.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

from app.config import settings
from app.utils.style_checks import (
    detect_abbreviated_months_without_date,
    detect_changed_event_call_to_action,
    detect_changed_official_names,
    detect_changed_source_date_conflicts,
    detect_cross_period_hyphen_ranges,
    detect_disallowed_ampersands,
    detect_event_detail_order_violations,
    detect_generic_destination_references,
    detect_headline_date_conflicts,
    detect_headline_echoes_lead,
    detect_indirect_contact_language,
    detect_inserted_weekday_mismatches,
    detect_introduced_audience_groups,
    detect_missing_anchored_requirements,
    detect_missing_approved_venue_addresses,
    detect_missing_broad_audience,
    detect_missing_contact_titles,
    detect_missing_information_options,
    detect_missing_near_term_weekdays,
    detect_missing_protected_organizations,
    detect_missing_relative_date_components,
    detect_missing_source_contacts,
    detect_missing_specific_audience_lead,
    detect_new_contact_channels,
    detect_new_contact_names,
    detect_noncanonical_campus_locations,
    detect_nonstandard_meridiems,
    detect_platform_names,
    detect_redundant_promotional_leads,
    detect_repeated_cta_phrases,
    detect_review_notes_in_copy,
    detect_standalone_event_detail_fragments,
    detect_twelve_oclock_meridiems,
    detect_unabbreviated_month_dates,
    detect_undefined_acronyms,
    detect_unconfirmed_dates,
    detect_unformatted_composition_titles,
    detect_unneeded_acronym_definitions,
    detect_weekday_date_conflicts,
    detect_weekday_date_mismatches,
    never_spell_out_acronyms,
    strip_html,
)


class Finding(NamedTuple):
    """A rule violation found in the edited copy.

    ``heuristic`` findings are always shown as warnings because the check
    can be wrong; exact checks take the rule's own severity.
    """

    rule_key: str
    message: str
    heuristic: bool = False


@dataclass(frozen=True)
class CheckContext:
    """Everything a check may read about one edit."""

    headline: str
    body: str
    category: str
    newsletter_type: str | None = None
    reference_date: date | None = None
    source_text: str = ""
    source_body: str = ""
    source_comparison_output: str = ""

    @property
    def text(self) -> str:
        """Headline and body without markup."""
        return strip_html(f"{self.headline}\n{self.body}")

    @property
    def body_source(self) -> str:
        """The submitted body, falling back to all submitted text."""
        return self.source_body or self.source_text

    @property
    def comparison_output(self) -> str:
        """Edited text plus embedded links, for checks that compare with the source."""
        return self.source_comparison_output or f"{self.headline}\n{self.body}"


Check = Callable[[CheckContext], Iterable[Finding]]


def _quoted(items: Iterable[str], limit: int | None = 5) -> str:
    return ", ".join(f"'{item}'" for item in list(items)[:limit])


def _each(rule_key: str, items: Iterable[str], message: str, *, heuristic: bool = False):
    """One finding per item; ``message`` is formatted with ``{}`` as the item."""
    return [Finding(rule_key, message.format(item), heuristic) for item in items]


def _listed(
    rule_key: str,
    items: list[str],
    message: str,
    *,
    heuristic: bool = False,
    limit: int | None = 5,
):
    """One finding listing the items (up to ``limit``), or none when there are none."""
    if not items:
        return []
    return [Finding(rule_key, message.format(_quoted(items, limit)), heuristic)]


# --- Checks on the edited copy alone ---------------------------------------


def review_notes_in_copy(ctx: CheckContext) -> list[Finding]:
    return _each(
        "review_flags",
        detect_review_notes_in_copy(ctx.text),
        "Move this review note to the flags list: '{}'",
    )


def headline_echoes_lead(ctx: CheckContext) -> list[Finding]:
    if not detect_headline_echoes_lead(ctx.headline, ctx.body):
        return []
    return [
        Finding(
            "headline_rules",
            "Headline begins with the same wording as the first sentence",
            heuristic=True,
        )
    ]


def month_abbreviations(ctx: CheckContext) -> list[Finding]:
    return _each(
        "ap_style_dates",
        detect_unabbreviated_month_dates(ctx.text),
        "Month should be abbreviated with a specific date: '{}'",
    ) + _each(
        "ap_style_dates",
        detect_abbreviated_months_without_date(ctx.text),
        "Month without a specific date should be spelled out: '{}'",
    )


def weekday_date_mismatches(ctx: CheckContext) -> list[Finding]:
    """Weekdays that don't match their dates, worded by who wrote them."""
    inserted = (
        detect_inserted_weekday_mismatches(
            ctx.source_text, ctx.text, reference_date=ctx.reference_date
        )
        if ctx.source_text
        else {}
    )
    conflicts = detect_weekday_date_conflicts(ctx.text, reference_date=ctx.reference_date)
    findings = []
    for found in detect_weekday_date_mismatches(ctx.text, reference_date=ctx.reference_date):
        if found not in inserted:
            message = f"Weekday does not match the calendar date: '{found}' [{conflicts[found]}]"
        elif inserted[found] is None:
            message = f"Added weekday is paired with a date that does not exist: '{found}'"
        else:
            message = (
                f"Added weekday does not match the calendar date: '{found}' "
                f"falls on a {inserted[found]}"
            )
        findings.append(Finding("ap_style_dates", message))
    return findings


def changed_source_date_conflicts(ctx: CheckContext) -> list[Finding]:
    if not ctx.source_text:
        return []
    changed = detect_changed_source_date_conflicts(
        ctx.source_text, ctx.text, reference_date=ctx.reference_date
    )
    return [
        Finding(
            "date_conflicts",
            f"Keep the submitted weekday and date as written: '{found}' [{note}]",
        )
        for found, note in changed.items()
    ]


def headline_date_conflicts(ctx: CheckContext) -> list[Finding]:
    return [
        Finding(
            "date_conflicts",
            "Headline date does not appear in the body [DATE CONFLICT: HEADLINE SAYS "
            f"{found.upper()}]",
            heuristic=True,
        )
        for found in detect_headline_date_conflicts(ctx.headline, ctx.body)
    ]


def unconfirmed_dates(ctx: CheckContext) -> list[Finding]:
    """Dates without a year that have passed or whose year is unclear (#410)."""
    found = detect_unconfirmed_dates(
        ctx.source_text,
        ctx.text,
        reference_date=ctx.reference_date,
        passed_window_days=settings.date_passed_window_days,
        year_unclear_after_days=settings.year_unclear_after_days,
    )
    return [
        Finding(
            "date_conflicts",
            f"Confirm this date with the submitter: '{found_date}' [{note}]",
            heuristic=True,
        )
        for found_date, note in found.items()
    ]


def missing_near_term_weekdays(ctx: CheckContext) -> list[Finding]:
    return _each(
        "day_of_week_with_dates",
        detect_missing_near_term_weekdays(ctx.text, reference_date=ctx.reference_date),
        "Near-term date is missing its weekday: '{}'",
    )


def time_formats(ctx: CheckContext) -> list[Finding]:
    return (
        _each(
            "ap_style_times",
            detect_nonstandard_meridiems(ctx.text),
            "Time should use lowercase a.m./p.m. with periods: '{}'",
        )
        + _each(
            "ap_style_times",
            detect_twelve_oclock_meridiems(ctx.text),
            "Use noon or midnight instead of '{}'",
        )
        + _each(
            "ap_style_times",
            detect_cross_period_hyphen_ranges(ctx.text),
            "Use 'to' for a time range that crosses a.m./p.m.: '{}'",
        )
    )


def event_detail_order(ctx: CheckContext) -> list[Finding]:
    return _each(
        "event_detail_ordering",
        detect_event_detail_order_violations(ctx.body),
        "Event details must put the time before the day and date: '{}'",
    ) + _each(
        "event_detail_ordering",
        detect_standalone_event_detail_fragments(ctx.body),
        "Keep event details in the same complete sentence as the event: '{}'",
        heuristic=True,
    )


def ampersands(ctx: CheckContext) -> list[Finding]:
    if not detect_disallowed_ampersands(ctx.text):
        return []
    return [Finding("ampersand_to_and", "Replace '&' with 'and'; Q&A is the only exception")]


def platform_names(ctx: CheckContext) -> list[Finding]:
    platforms = detect_platform_names(ctx.text)
    if not platforms:
        return []
    names = ", ".join(f"'{name}'" for name in sorted(set(platforms)))
    return [
        Finding(
            "online_not_platform",
            f"Platform name(s) {names} found — use 'online' unless the platform is essential",
            heuristic=True,
        )
    ]


def acronyms(ctx: CheckContext) -> list[Finding]:
    """The acronym order of checks (#381, #399)."""
    standalone = never_spell_out_acronyms(ctx.newsletter_type)
    body = strip_html(ctx.body)
    findings = []
    undefined = detect_undefined_acronyms(body, standalone)
    if undefined:
        findings.append(
            Finding(
                "spell_out_acronyms",
                "Acronym(s) never defined in the body as Full Name (ACRONYM): "
                + ", ".join(undefined[:5]),
                heuristic=True,
            )
        )
    for token in detect_unneeded_acronym_definitions(strip_html(ctx.headline), body, standalone):
        reason = (
            "is on the never-spell-out list; use it alone"
            if token in standalone
            else "is not used again; write the full name alone"
        )
        findings.append(Finding("spell_out_acronyms", f"Acronym '{token}' {reason}", True))
    return findings


def repeated_calls_to_action(ctx: CheckContext) -> list[Finding]:
    return _listed(
        "single_cta",
        detect_repeated_cta_phrases(ctx.text),
        "Call-to-action phrase(s) repeated: {}",
        heuristic=True,
        limit=None,
    )


def call_to_action_wording(ctx: CheckContext) -> list[Finding]:
    return (
        _each(
            "promotional_action_benefit_lead",
            detect_redundant_promotional_leads(ctx.body),
            "Promotional lead is passive or redundant: '{}'",
        )
        + _each(
            "cta_structure",
            detect_generic_destination_references(ctx.body),
            "Replace generic destination reference with descriptive linked text: '{}'",
        )
        + _each(
            "cta_structure",
            detect_indirect_contact_language(ctx.body),
            "Use direct information-first contact language instead of '{}'",
        )
    )


def job_listing_format(ctx: CheckContext) -> list[Finding]:
    if ctx.category != "job_opportunity":
        return []
    problems = [
        (bool(ctx.headline.strip()), "Jobs listing includes a headline — keep it body-only"),
        (
            re.search(r"\bMoscow\b", ctx.text) is not None,
            "Jobs listing mentions Moscow — omit the default location",
        ),
        ("\n" in ctx.body.strip(), "Jobs listing spans multiple lines — keep it on one line"),
    ]
    return [Finding("job_posting_format", message) for found, message in problems if found]


# --- Checks that compare the edit with the submission ----------------------


def changed_event_call_to_action(ctx: CheckContext) -> list[Finding]:
    return [
        Finding(
            "headline_reader_perspective",
            f'Headline changes the source event\'s intended action: "{action}"',
            heuristic=True,
        )
        for action in detect_changed_event_call_to_action(ctx.body_source, ctx.headline)
    ]


def missing_source_contacts(ctx: CheckContext) -> list[Finding]:
    return _listed(
        "preserve_purpose_contact_titles",
        detect_missing_source_contacts(ctx.source_text, ctx.comparison_output),
        "Source contact information missing from AI edit: {}",
    )


def invented_contacts(ctx: CheckContext) -> list[Finding]:
    return _listed(
        "no_fabricated_content",
        detect_new_contact_channels(ctx.source_text, ctx.comparison_output),
        "Contact information not found in submitted content: {}",
    ) + _listed(
        "no_fabricated_content",
        detect_new_contact_names(ctx.source_text, ctx.comparison_output),
        "Contact name(s) not found in submitted content: {}",
    )


def changed_official_names(ctx: CheckContext) -> list[Finding]:
    return _listed(
        "preserve_event_title_case",
        detect_changed_official_names(ctx.source_text, ctx.comparison_output),
        "Official or branded source name(s) changed or removed: {}",
    )


def missing_organizations(ctx: CheckContext) -> list[Finding]:
    return _each(
        "preserve_organizational_context",
        detect_missing_protected_organizations(ctx.body_source, ctx.body),
        "Source organization missing from AI-edited body: '{}'",
    )


def missing_contact_titles(ctx: CheckContext) -> list[Finding]:
    return _listed(
        "preserve_purpose_contact_titles",
        detect_missing_contact_titles(ctx.body_source, ctx.body),
        "Source contact title(s) missing from AI edit: {}",
    )


def missing_options_and_requirements(ctx: CheckContext) -> list[Finding]:
    return _each(
        "preserve_information_options",
        detect_missing_information_options(ctx.body_source, ctx.body),
        "Source information-seeking option missing from AI edit: '{}'",
    ) + _each(
        "preserve_action_deadlines",
        detect_missing_anchored_requirements(ctx.body_source, ctx.body),
        "Source requirement missing from AI edit: '{}'",
    )


def audience_scope(ctx: CheckContext) -> list[Finding]:
    return (
        _listed(
            "preserve_audience_scope",
            detect_missing_specific_audience_lead(ctx.body_source, ctx.body),
            "Specific source audience context missing from first sentence: {}",
        )
        + _each(
            "preserve_audience_scope",
            detect_missing_broad_audience(ctx.body_source, ctx.body),
            "Broad source invitation was narrowed or removed: '{}'",
        )
        + _each(
            "preserve_audience_scope",
            detect_introduced_audience_groups(ctx.source_text, ctx.body),
            "AI edit introduced an audience not stated in the source: '{}'",
        )
    )


def relative_dates(ctx: CheckContext) -> list[Finding]:
    return _each(
        "today_tomorrow",
        detect_missing_relative_date_components(ctx.body_source, ctx.body),
        "Retain both the relative date and its explicit calendar date: '{}'",
    )


def composition_titles(ctx: CheckContext) -> list[Finding]:
    return _each(
        "composition_title_format",
        detect_unformatted_composition_titles(ctx.source_text, ctx.headline, ctx.body),
        "Composition title needs AP quotation formatting: '{}'",
    )


def locations_and_venues(ctx: CheckContext) -> list[Finding]:
    return _each(
        "building_room_order",
        detect_noncanonical_campus_locations(ctx.body),
        "Use canonical building-before-room location: '{}'",
    ) + _each(
        "approved_off_campus_addresses",
        detect_missing_approved_venue_addresses(ctx.source_text, ctx.body),
        "Approved venue is missing its canonical address: '{}'",
    )


OUTPUT_CHECKS: list[Check] = [
    review_notes_in_copy,
    headline_echoes_lead,
    month_abbreviations,
    weekday_date_mismatches,
    changed_source_date_conflicts,
    headline_date_conflicts,
    unconfirmed_dates,
    missing_near_term_weekdays,
    time_formats,
    event_detail_order,
    ampersands,
    platform_names,
    acronyms,
    repeated_calls_to_action,
    call_to_action_wording,
    job_listing_format,
]

SOURCE_CHECKS: list[Check] = [
    changed_event_call_to_action,
    missing_source_contacts,
    invented_contacts,
    changed_official_names,
    missing_organizations,
    missing_contact_titles,
    missing_options_and_requirements,
    audience_scope,
    relative_dates,
    composition_titles,
    locations_and_venues,
]


def run_checks(ctx: CheckContext) -> list[Finding]:
    """All findings for one edit, in display order."""
    checks = OUTPUT_CHECKS + (SOURCE_CHECKS if ctx.source_text else [])
    return [finding for check in checks for finding in check(ctx)]
