"""Text utilities for headline case conversion, first-person detection, and event detail detection."""

import re

# Words that should stay lowercase in title case (AP style)
TITLE_CASE_LOWERCASE = {
    "a", "an", "and", "as", "at", "but", "by", "for", "in", "nor",
    "of", "on", "or", "so", "the", "to", "up", "yet",
}

# First-person pronouns and possessives
FIRST_PERSON_PATTERNS = re.compile(
    r"\b(I|me|my|mine|myself|we|us|our|ours|ourselves)\b", re.IGNORECASE
)

# Common event detail indicators
TIME_PATTERN = re.compile(
    r"\b\d{1,2}(?::\d{2})?\s*(?:a\.m\.|p\.m\.|am|pm)"
    r"|\bnoon\b|\bmidnight\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?:Jan\.?|Feb\.?|Mar\.?|March|Apr\.?|April|May|June?|July?|Aug\.?|Sept?\.?|Oct\.?|Nov\.?|Dec\.?)\s+\d{1,2}\b"
    r"|\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"
    r"|\b(?:today|tomorrow)\b",
    re.IGNORECASE,
)
LOCATION_PATTERN = re.compile(
    r"\b(?:room|building|hall|center|commons|library|auditorium|arena|"
    r"stadium|theater|theatre|gym|lab|lounge|ballroom|SUB|ISUB|"
    r"Kibbie|Pitman|Admin|TLC|Bruce|Menard|Idaho Commons|"
    r"Teaching Learning Center)\b",
    re.IGNORECASE,
)


def to_sentence_case(text: str) -> str:
    """Convert a headline to sentence case (capitalize first word and proper nouns only).

    Since we can't reliably detect proper nouns, this lowercases everything
    except the first character and known proper nouns/acronyms.
    """
    if not text:
        return text

    # Known proper nouns and acronyms to preserve
    preserve = {
        "University of Idaho", "U of I", "Idaho", "Moscow", "Boise",
        "Coeur d'Alene", "Vandal", "Vandals", "ASUI", "UCM", "UI",
        "ISUB", "SUB", "Kibbie", "Pitman", "TLC", "VandalStar",
        "PeopleAdmin", "VandalWeb", "USA", "NCAA", "AP", "HR",
    }

    # Start by lowercasing everything
    result = text[0].upper() + text[1:].lower() if len(text) > 1 else text.upper()

    # Restore preserved terms
    for term in preserve:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        for match in pattern.finditer(text):
            original = match.group()
            start = match.start()
            end = match.end()
            # Find the corresponding position in result
            result = result[:start] + original + result[end:]

    return result


def to_title_case(text: str) -> str:
    """Convert a headline to AP-style title case.

    Capitalizes all words except short prepositions, conjunctions, and articles,
    unless they are the first or last word.
    """
    if not text:
        return text

    words = text.split()
    result = []
    for i, word in enumerate(words):
        # Always capitalize first and last word
        if i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        elif word.lower() in TITLE_CASE_LOWERCASE:
            result.append(word.lower())
        else:
            result.append(word.capitalize())
    return " ".join(result)


def detect_first_person(text: str) -> list[dict]:
    """Find first-person pronoun usage in text.

    Returns list of dicts with 'word', 'position', 'context' keys.
    """
    findings = []
    for match in FIRST_PERSON_PATTERNS.finditer(text):
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        findings.append({
            "word": match.group(),
            "position": match.start(),
            "context": f"...{text[start:end]}...",
        })
    return findings


def detect_exclamation_marks(text: str) -> list[dict]:
    """Find exclamation marks in text."""
    findings = []
    for i, char in enumerate(text):
        if char == "!":
            start = max(0, i - 20)
            end = min(len(text), i + 20)
            findings.append({
                "position": i,
                "context": f"...{text[start:end]}...",
            })
    return findings


def check_event_details(text: str) -> dict:
    """Check whether text contains required event details (time, date, location).

    Returns dict with 'has_time', 'has_date', 'has_location', 'missing' keys.
    """
    has_time = bool(TIME_PATTERN.search(text))
    has_date = bool(DATE_PATTERN.search(text))
    has_location = bool(LOCATION_PATTERN.search(text))

    missing = []
    if not has_time:
        missing.append("time")
    if not has_date:
        missing.append("date")
    if not has_location:
        missing.append("location")

    return {
        "has_time": has_time,
        "has_date": has_date,
        "has_location": has_location,
        "missing": missing,
    }


def is_event_category(category: str) -> bool:
    """Check if a submission category typically requires event details."""
    return category in ("calendar_event", "faculty_staff", "student")
