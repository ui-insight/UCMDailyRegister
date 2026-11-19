"""Parse submitter notes for hyperlink instructions.

Submitters often include link information in their notes like:
- "Link 'Register here' to https://example.com/register"
- "Hyperlink the word 'website' to https://uidaho.edu"
- "Please link to: https://example.com"
- Raw URLs that need to be detected

Also handles automatic unwrapping of email security gateway tracking URLs
(Proofpoint URLDefense, Microsoft Safe Links, Mimecast, Barracuda).
"""

import html
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


# Hosts of email security gateways that wrap links (#530). A host matches
# when it is one of these or a subdomain of one, such as the regional Safe
# Links hosts "nam12.", "eur03." or "gcc02.safelinks.protection.outlook.com"
# (#520). The match is anchored on the parsed hostname, so a look-alike such
# as "safelinks.protection.outlook.com.evil.example" is not a gateway.
_PROOFPOINT_HOSTS = ("urldefense.com", "urldefense.proofpoint.com")
_SAFE_LINKS_HOST = "safelinks.protection.outlook.com"
_MIMECAST_HOST = "mimecast.com"
_BARRACUDA_HOST = "linkprotect.cudasvc.com"
_GATEWAY_HOST = re.compile(
    r"(?:^|\.)(?:urldefense\.com|urldefense\.proofpoint\.com|"
    r"safelinks\.protection\.outlook\.com|mimecast\.com|linkprotect\.cudasvc\.com)$",
    re.IGNORECASE,
)

# A wrapped link written out in text, with or without its scheme
# ("urldefense.com/v3/__https:/example.com__;!!x$"). The lookbehind keeps a
# gateway name inside another address ("evil.example/safelinks...") from
# matching (#520).
WRAPPED_URL_PATTERN = re.compile(
    r"(?<![\w.@/%-])(?:https?://)?(?:[a-z0-9-]+\.)*"
    r"(?:urldefense(?:\.proofpoint)?\.com|safelinks\.protection\.outlook\.com|"
    r"mimecast\.com|linkprotect\.cudasvc\.com)/[^\s<>\"']*",
    re.IGNORECASE,
)

WRAPPED_LINK_NOTE = "LINK WRAPPED: CONFIRM REAL URL"


def _with_scheme(url: str) -> str:
    if re.match(r"https?:", url, re.IGNORECASE):
        return url
    return f"https://{url}"


def is_wrapped_url(url: str) -> bool:
    """True when ``url`` goes through an email security gateway."""
    try:
        hostname = urlparse(_with_scheme(url.strip())).hostname or ""
    except ValueError:
        return False
    return bool(_GATEWAY_HOST.search(hostname))


def _destination(candidate: str) -> str | None:
    """A recovered address, if it is a complete http(s) URL; else None.

    The address may itself be wrapped; ``_unwrap`` peels the next layer.
    """
    # Restore the double slash Proofpoint drops: "https:/example.com".
    candidate = re.sub(r"^(https?):/*", r"\1://", candidate.strip(), flags=re.IGNORECASE)
    if "*" in candidate or any(ch.isspace() for ch in candidate):
        return None
    try:
        parts = urlparse(candidate)
    except ValueError:
        return None
    host = parts.hostname or ""
    if parts.scheme.lower() not in ("http", "https") or "." not in host:
        return None
    return candidate


def _first_param(url: str, name: str) -> str | None:
    values = parse_qs(urlparse(url).query).get(name)
    return values[0] if values else None


def resolve_tracking_url(url: str) -> str | None:
    """The real destination of a link, unwrapping email security gateways.

    Returns ``url`` unchanged when it isn't wrapped, the destination when it
    can be recovered reliably, and None when it is wrapped but the real
    address can't be recovered (Proofpoint "*" placeholders, a cut-off
    link, an opaque Mimecast token). Never guesses (#530).

    Supports Proofpoint URLDefense v3 and v2, Microsoft Safe Links,
    Mimecast and Barracuda.
    """
    if not is_wrapped_url(url):
        return url
    full = _with_scheme(url.strip())
    real = _unwrap(full)
    # Log only the wrapper type, never the address: it can carry personal
    # data and tokens.
    wrapper = _wrapper_name(full)
    if real is None:
        logger.info("Could not recover the destination of a %s link", wrapper)
    else:
        logger.info("Unwrapped %s link", wrapper)
    return real


def _host_is(hostname: str, *domains: str) -> bool:
    """True when ``hostname`` is one of ``domains`` or a subdomain of one."""
    hostname = hostname.lower().rstrip(".")
    return any(hostname == d or hostname.endswith("." + d) for d in domains)


def _wrapper_name(full: str) -> str:
    hostname = urlparse(full).hostname or ""
    if _host_is(hostname, *_PROOFPOINT_HOSTS):
        return "Proofpoint"
    if _host_is(hostname, _SAFE_LINKS_HOST):
        return "Microsoft Safe Links"
    if _host_is(hostname, _MIMECAST_HOST):
        return "Mimecast"
    return "Barracuda"


# How many gateways deep a link may be wrapped, e.g. Safe Links around
# Proofpoint when a message passed through two mail systems.
_MAX_NESTING = 3


def _unwrap(full: str, depth: int = 0) -> str | None:
    """The destination of a wrapped link, or None; ``full`` has a scheme."""
    real = _unwrap_once(full)
    if real is None or not is_wrapped_url(real):
        return real
    if depth + 1 >= _MAX_NESTING:
        return None
    return _unwrap(_with_scheme(real), depth + 1)


def _unwrap_once(full: str) -> str | None:
    try:
        hostname = urlparse(full).hostname or ""
        proofpoint = _host_is(hostname, *_PROOFPOINT_HOSTS)
        if proofpoint and "/v3/__" in full:
            # The address sits between the first "__" and the "__;" after it.
            embedded, closed, _ = full.split("/v3/__", 1)[1].partition("__;")
            if not closed:
                embedded, closed, _ = embedded.partition("__")
            if not closed:
                return None
            return _destination(embedded)
        if proofpoint and "/v2/" in full:
            encoded = _first_param(full, "u")
            if not encoded:
                return None
            # v2: "-XX" is a hex-escaped character and "_" stands for "/".
            decoded = re.sub(
                r"-([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), encoded.replace("_", "/")
            )
            return _destination(decoded)
        if _host_is(hostname, _SAFE_LINKS_HOST):
            # parse_qs decodes %3A and %2F and drops "&data=" and later parameters.
            target = _first_param(full, "url")
            if target and re.match(r"https?%3A", target, re.IGNORECASE):
                # Encoded twice (a forwarded or re-wrapped link): the scheme
                # is still escaped, so decode once more.
                target = unquote(target)
            return _destination(target) if target else None
        if _host_is(hostname, _MIMECAST_HOST) and "/s/" in full:
            # Mimecast tokens are usually opaque; only a URL-encoded address is used.
            token = urlparse(full).path.split("/s/", 1)[1].rstrip("/")
            return _destination(unquote(token))
        if _host_is(hostname, _BARRACUDA_HOST):
            # parse_qs has already decoded the parameter once.
            target = _first_param(full, "a")
            return _destination(target) if target else None
    except ValueError:
        logger.warning("Failed to unwrap tracking URL")
    return None


def unwrap_tracking_url(url: str) -> str:
    """The real destination of a wrapped link, or ``url`` unchanged.

    A wrapped link whose destination can't be recovered is returned as is;
    use ``resolve_tracking_url`` to tell that case apart.
    """
    return resolve_tracking_url(url) or url


def unwrap_links_in_text(text: str) -> tuple[str, list[str]]:
    """Replace wrapped links in plain text or HTML with their real destinations.

    Covers anchors (``<a href="...">words</a>``) and addresses written out
    as text. A link whose destination can't be recovered is removed: an
    anchor keeps its words unlinked, and a written-out address is dropped.
    Returns the new text and the words or addresses that lost a link, for
    staff to confirm (#530).
    """
    if not text:
        return text, []
    unrecoverable: list[str] = []

    def anchor(match: re.Match) -> str:
        raw = next(group for group in match.groups()[:3] if group is not None)
        href = html.unescape(raw).strip()
        if not is_wrapped_url(href):
            return match.group(0)
        real = resolve_tracking_url(href)
        if real is None:
            unrecoverable.append(re.sub(r"<[^>]+>", "", match.group(4)).strip() or href)
            return match.group(4)
        return match.group(0).replace(raw, html.escape(real, quote=True), 1)

    def written(match: re.Match) -> str:
        url = match.group(0).rstrip(".,;:!?)]}\u201d\u2019")
        trailing = match.group(0)[len(url):]
        real = resolve_tracking_url(url)
        if real is None:
            unrecoverable.append(url)
            return trailing
        return real + trailing

    # Anchors first; then written-out addresses outside any tag.
    from app.utils.body_links import ANCHOR_PATTERN

    text = ANCHOR_PATTERN.sub(anchor, text)
    parts = re.split(r"(<[^>]+>)", text)
    text = "".join(
        part if part.startswith("<") else WRAPPED_URL_PATTERN.sub(written, part)
        for part in parts
    )
    # A dropped address can leave doubled spaces or a space before punctuation.
    if unrecoverable:
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)
    return text, unrecoverable


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
