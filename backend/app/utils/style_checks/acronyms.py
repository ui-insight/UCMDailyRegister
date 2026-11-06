"""Acronyms: the order of checks for spelling out and never-spell-out lists (#381, #399)."""

import re

_ACRONYM_TOKEN = re.compile(r"\b[A-Z]{2,6}\b")
_ROMAN_NUMERAL = re.compile(r"^[IVXLCDM]+$")
# Acronyms AP or campus usage treats as standing on their own.
_KNOWN_ACRONYMS = {
    "AP", "US", "USA", "TDR", "RSVP", "GPA", "ID", "PDF", "FAQ", "HR", "IT",
    "TV", "AV", "GED", "ADA", "FYI", "AM", "PM", "AI", "GPS", "FBI", "NASA",
}
# UCM's never-spell-out lists (#381): the acronym stands alone, even on
# first reference, with no parenthetical definition.
NEVER_SPELL_OUT_ACRONYMS = {"IMCI", "IRIC", "COBRE", "INBRE", "EPSCoR", "ISUB"}
MYUI_NEVER_SPELL_OUT_ACRONYMS = {"CALS", "CAA", "ICCU", "LHSOM"}
# Acronym-shaped: starts with a capital and has at least one more capital,
# so EPSCoR matches but ordinary words such as (Online) do not.
_PARENTHETICAL_ACRONYM = re.compile(r"\(([A-Z](?=[a-z]*[A-Z])[A-Za-z]{1,7})\)")


def never_spell_out_acronyms(newsletter_type: str | None) -> set[str]:
    """Return the acronyms UCM never spells out for a newsletter."""
    if newsletter_type == "myui":
        return NEVER_SPELL_OUT_ACRONYMS | MYUI_NEVER_SPELL_OUT_ACRONYMS
    return set(NEVER_SPELL_OUT_ACRONYMS)


def detect_undefined_acronyms(body: str, standalone: set[str] | None = None) -> list[str]:
    """Heuristic: find acronyms the body never defines as Full Name (ACRONYM).

    Roman numerals (job classifications such as III), widely recognized
    acronyms and the ``standalone`` never-spell-out list are skipped. A token
    counts as defined when it appears in parentheses anywhere in the body, the
    shape the acronym rule requires.
    """
    skipped = _KNOWN_ACRONYMS | (standalone or set())
    tokens = set(_ACRONYM_TOKEN.findall(body))
    return sorted(
        token
        for token in tokens
        if token not in skipped
        and not _ROMAN_NUMERAL.fullmatch(token)
        and f"({token})" not in body
    )


def detect_unneeded_acronym_definitions(
    headline: str,
    body: str,
    standalone: set[str] | None = None,
) -> list[str]:
    """Heuristic: find parenthetical acronyms the copy does not need (#381).

    A definition such as Full Name (ACRONYM) belongs only when the acronym
    appears again later in the body or in the headline. Acronyms on the
    ``standalone`` never-spell-out list should never be defined at all.
    """
    standalone = standalone or set()
    unneeded = set()
    for match in _PARENTHETICAL_ACRONYM.finditer(body):
        token = match.group(1)
        if token in standalone:
            unneeded.add(token)
            continue
        token_pattern = re.compile(rf"\b{re.escape(token)}\b")
        reused_in_body = token_pattern.search(body, match.end()) is not None
        if not reused_in_body and not token_pattern.search(headline):
            unneeded.add(token)
    return sorted(unneeded)
