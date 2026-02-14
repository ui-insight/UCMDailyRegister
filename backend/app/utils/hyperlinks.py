"""Parse submitter notes for hyperlink instructions.

Submitters often include link information in their notes like:
- "Link 'Register here' to https://example.com/register"
- "Hyperlink the word 'website' to https://uidaho.edu"
- "Please link to: https://example.com"
- Raw URLs that need to be detected
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedLink:
    url: str
    anchor_text: str | None = None
    source: str = "submitter_notes"  # "submitter_notes" or "body_text"


# Match URLs (http/https)
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\),]+",
    re.IGNORECASE,
)

# Match patterns like: link "text" to URL, hyperlink "text" to URL
LINK_INSTRUCTION_PATTERN = re.compile(
    r"""(?:link|hyperlink)\s+          # keyword
    (?:['\"]([^'\"]+)['\"]|            # quoted anchor text
    (?:the\s+(?:word|phrase|text)\s+)?  # optional "the word/phrase/text"
    ['\"]([^'\"]+)['\"])               # quoted text after "the word"
    \s+to\s+                           # "to"
    (https?://[^\s<>\"'\),]+)          # URL
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Match patterns like: link to URL, link: URL
LINK_TO_PATTERN = re.compile(
    r"(?:link|hyperlink|url|website)\s*(?:to|:)\s*(https?://[^\s<>\"'\),]+)",
    re.IGNORECASE,
)


def parse_submitter_notes(notes: str) -> list[ParsedLink]:
    """Extract link instructions from submitter notes.

    Handles patterns like:
    - Explicit anchor text: 'Link "Register here" to https://...'
    - Generic link-to: 'link to https://...'
    - Raw URLs
    """
    if not notes:
        return []

    links: list[ParsedLink] = []
    matched_urls: set[str] = set()

    # First pass: explicit anchor text instructions
    for match in LINK_INSTRUCTION_PATTERN.finditer(notes):
        anchor = match.group(1) or match.group(2)
        url = match.group(3)
        if url not in matched_urls:
            links.append(ParsedLink(url=url, anchor_text=anchor))
            matched_urls.add(url)

    # Second pass: link-to patterns without explicit anchor
    for match in LINK_TO_PATTERN.finditer(notes):
        url = match.group(1)
        if url not in matched_urls:
            links.append(ParsedLink(url=url, anchor_text=None))
            matched_urls.add(url)

    # Third pass: remaining bare URLs
    for match in URL_PATTERN.finditer(notes):
        url = match.group(0)
        # Clean trailing punctuation
        url = url.rstrip(".,;:")
        if url not in matched_urls:
            links.append(ParsedLink(url=url, anchor_text=None))
            matched_urls.add(url)

    return links


def extract_urls_from_body(body: str) -> list[ParsedLink]:
    """Extract raw URLs from submission body text."""
    if not body:
        return []

    links = []
    for match in URL_PATTERN.finditer(body):
        url = match.group(0).rstrip(".,;:")
        links.append(ParsedLink(url=url, anchor_text=None, source="body_text"))
    return links
