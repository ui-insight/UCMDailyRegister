"""Deterministic post-edit style checks for AI-edited copy.

The AI editing pipeline injects the active style rules into the system prompt,
but prompt text alone cannot guarantee compliance: Joy's Aug. 10 production
feedback (issues #299 and #300) showed the model violating rules that were
active in the prompt at the time. The detectors here cover the subset of those
rules that can be verified mechanically — AP month abbreviation, a.m./p.m.
formatting, platform names, undefined acronyms, repeated calls to action and
the Jobs single-line contract, plus high-confidence source contacts,
organizations, titles, audience qualifiers, composition titles, canonical
locations, information paths, promotional leads and anchored requirements —
so a violation surfaces as a flag on the AI version regardless of whether the
model honored the prompt.

Each detector is a pure function over edited text and returns the offending
fragments. Mapping findings to flags (and gating on whether the corresponding
rule is active) happens in the AIEditor, keeping these functions independent
of the database. Detectors marked heuristic can produce false positives and
should be surfaced as warnings, never errors.

The detectors are grouped by topic in this package; import them from here.
"""

from app.utils.style_checks.text import (
    strip_html,
)
from app.utils.style_checks.dates import (
    detect_unabbreviated_month_dates,
    detect_abbreviated_months_without_date,
    detect_nonstandard_meridiems,
    detect_twelve_oclock_meridiems,
    detect_cross_period_hyphen_ranges,
    detect_missing_relative_date_components,
    detect_weekday_date_mismatches,
    detect_inserted_weekday_mismatches,
    date_conflict_note,
    detect_weekday_date_conflicts,
    detect_changed_source_date_conflicts,
    detect_headline_date_conflicts,
    change_contradicts_final_dates,
    detect_missing_near_term_weekdays,
)
from app.utils.style_checks.events import (
    detect_event_detail_order_violations,
    detect_standalone_event_detail_fragments,
    detect_changed_event_call_to_action,
)
from app.utils.style_checks.acronyms import (
    NEVER_SPELL_OUT_ACRONYMS,
    MYUI_NEVER_SPELL_OUT_ACRONYMS,
    never_spell_out_acronyms,
    detect_undefined_acronyms,
    detect_unneeded_acronym_definitions,
)
from app.utils.style_checks.wording import (
    detect_disallowed_ampersands,
    detect_platform_names,
    detect_repeated_cta_phrases,
    detect_review_notes_in_copy,
    detect_headline_echoes_lead,
    detect_redundant_promotional_leads,
    detect_generic_destination_references,
    detect_indirect_contact_language,
)
from app.utils.style_checks.audience import (
    detect_missing_specific_audience_lead,
    detect_missing_broad_audience,
    detect_introduced_audience_groups,
)
from app.utils.style_checks.names import (
    detect_unformatted_composition_titles,
    detect_noncanonical_campus_locations,
    detect_missing_approved_venue_addresses,
    detect_missing_protected_organizations,
    detect_changed_official_names,
)
from app.utils.style_checks.contacts import (
    detect_missing_source_contacts,
    detect_new_contact_channels,
    detect_new_contact_names,
    detect_missing_contact_titles,
    detect_missing_information_options,
    detect_missing_anchored_requirements,
)

__all__ = [
    "strip_html",
    "detect_unabbreviated_month_dates",
    "detect_abbreviated_months_without_date",
    "detect_nonstandard_meridiems",
    "detect_twelve_oclock_meridiems",
    "detect_cross_period_hyphen_ranges",
    "detect_missing_relative_date_components",
    "detect_weekday_date_mismatches",
    "detect_inserted_weekday_mismatches",
    "date_conflict_note",
    "detect_weekday_date_conflicts",
    "detect_changed_source_date_conflicts",
    "detect_headline_date_conflicts",
    "change_contradicts_final_dates",
    "detect_missing_near_term_weekdays",
    "detect_event_detail_order_violations",
    "detect_standalone_event_detail_fragments",
    "detect_changed_event_call_to_action",
    "NEVER_SPELL_OUT_ACRONYMS",
    "MYUI_NEVER_SPELL_OUT_ACRONYMS",
    "never_spell_out_acronyms",
    "detect_undefined_acronyms",
    "detect_unneeded_acronym_definitions",
    "detect_disallowed_ampersands",
    "detect_platform_names",
    "detect_repeated_cta_phrases",
    "detect_review_notes_in_copy",
    "detect_headline_echoes_lead",
    "detect_redundant_promotional_leads",
    "detect_generic_destination_references",
    "detect_indirect_contact_language",
    "detect_missing_specific_audience_lead",
    "detect_missing_broad_audience",
    "detect_introduced_audience_groups",
    "detect_unformatted_composition_titles",
    "detect_noncanonical_campus_locations",
    "detect_missing_approved_venue_addresses",
    "detect_missing_protected_organizations",
    "detect_changed_official_names",
    "detect_missing_source_contacts",
    "detect_new_contact_channels",
    "detect_new_contact_names",
    "detect_missing_contact_titles",
    "detect_missing_information_options",
    "detect_missing_anchored_requirements",
]
