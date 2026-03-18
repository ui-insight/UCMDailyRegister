"""Parse submitter notes for hyperlink instructions.

Submitters often include link information in their notes like:
- "Link 'Register here' to https://example.com/register"
- "Hyperlink the word 'website' to https://uidaho.edu"
- "Please link to: https://example.com"
- Raw URLs that need to be detected

Also handles automatic unwrapping of email security gateway tracking URLs
(Proofpoint URLDefense, Microsoft Safe Links, Mimecast, Barracuda).
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger(__name__)


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


def unwrap_tracking_url(url: str) -> str:
    """Unwrap email security gateway tracking URLs to their original destination.

    Supports:
    - Proofpoint URLDefense v3 (urldefense.com/v3/__<url>__)
    - Proofpoint URLDefense v2 (urldefense.proofpoint.com/v2/url?u=<encoded>)
    - Microsoft Safe Links (safelinks.protection.outlook.com/?url=<encoded>)
    - Mimecast (protect-*.mimecast.com/s/<encoded-url>/)
    - Barracuda (linkprotect.cudasvc.com/url?a=<encoded>)

    Returns the original URL if a tracking wrapper is detected, otherwise
    returns the input unchanged.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Proofpoint URLDefense v3
        if "urldefense" in hostname and "/v3/__" in url:
            # Real URL sits between /v3/__ and the next __
            after_prefix = url.split("/v3/__", 1)[1]
            original = after_prefix.split("__", 1)[0]
            if original.startswith("http"):
                logger.info("Unwrapped Proofpoint v3 URL: %s → %s", url, original)
                return original

        # Proofpoint URLDefense v2
        if "urldefense" in hostname and "/v2/" in url:
            params = parse_qs(parsed.query)
            if "u" in params:
                encoded = params["u"][0]
                # v2 encoding: hex-encoded special chars as -XX, underscores → slashes
                # First decode hex sequences (-XX → character), then underscores → slashes
                original = re.sub(
                    r"-([0-9A-Fa-f]{2})",
                    lambda m: chr(int(m.group(1), 16)),
                    encoded,
                ).replace("_", "/")
                if original.startswith("http"):
                    logger.info("Unwrapped Proofpoint v2 URL: %s → %s", url, original)
                    return original

        # Microsoft Safe Links
        if hostname == "safelinks.protection.outlook.com":
            params = parse_qs(parsed.query)
            if "url" in params:
                original = unquote(params["url"][0])
                logger.info("Unwrapped Microsoft Safe Links URL: %s → %s", url, original)
                return original

        # Mimecast
        if "mimecast.com" in hostname and "/s/" in parsed.path:
            # Path format: /s/<base64-encoded-url>/
            path_parts = parsed.path.split("/s/", 1)
            if len(path_parts) > 1:
                encoded_part = path_parts[1].rstrip("/")
                # Mimecast sometimes URL-encodes the destination
                original = unquote(encoded_part)
                if original.startswith("http"):
                    logger.info("Unwrapped Mimecast URL: %s → %s", url, original)
                    return original

        # Barracuda
        if hostname == "linkprotect.cudasvc.com":
            params = parse_qs(parsed.query)
            if "a" in params:
                original = unquote(params["a"][0])
                logger.info("Unwrapped Barracuda URL: %s → %s", url, original)
                return original

    except Exception:
        logger.warning("Failed to unwrap tracking URL: %s", url, exc_info=True)

    return url


def _clean_url(url: str) -> str:
    """Strip trailing punctuation and unwrap any tracking URL wrapper."""
    url = url.rstrip(".,;:")
    return unwrap_tracking_url(url)


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
        url = _clean_url(match.group(3))
        if url not in matched_urls:
            links.append(ParsedLink(url=url, anchor_text=anchor))
            matched_urls.add(url)

    # Second pass: link-to patterns without explicit anchor
    for match in LINK_TO_PATTERN.finditer(notes):
        url = _clean_url(match.group(1))
        if url not in matched_urls:
            links.append(ParsedLink(url=url, anchor_text=None))
            matched_urls.add(url)

    # Third pass: remaining bare URLs
    for match in URL_PATTERN.finditer(notes):
        url = _clean_url(match.group(0))
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
        url = _clean_url(match.group(0))
        links.append(ParsedLink(url=url, anchor_text=None, source="body_text"))
    return links
