"""Read the inline links in an edited newsletter body.

Edited bodies are plain text in which a link is an HTML anchor wrapped around
the exact words that carry it: ``Visit <a href="https://...">the site</a>.``
This module is the backend's single reader of that format, so export and any
validation agree on which words are linked and where they point.

Only https and mailto destinations are honored, matching the Editor's rules
(frontend/src/utils/bodyLinks.ts). An anchor with any other destination, or a
stray anchor tag, degrades to its plain words: no raw HTML ever reaches a
reader.
"""

import html
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from app.utils.hyperlinks import URL_PATTERN, unwrap_tracking_url

_ANCHOR = re.compile(
    r"""<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))[^>]*>(.*?)</a\s*>""",
    re.IGNORECASE | re.DOTALL,
)
_STRAY_ANCHOR_TAG = re.compile(r"</?a\b[^>]*>", re.IGNORECASE)
_INNER_TAG = re.compile(r"<[^>]+>")
_EMAIL = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


LinkFindingKind = Literal["unsafe_link", "tracking_link", "bare_url", "missing_submitted_link"]


@dataclass(frozen=True)
class LinkFinding:
    """A link problem staff should resolve before a newsletter is exported."""

    Kind: LinkFindingKind
    Text: str | None = None
    Href: str | None = None
    # For tracking links: the real destination behind the wrapper.
    Suggested_Href: str | None = None


@dataclass(frozen=True)
class BodySegment:
    """A run of body text; ``href`` is set when the words are a link."""

    text: str
    href: str | None = None


def is_safe_destination(url: str) -> bool:
    """True for https URLs with a host and no credentials, and plain mailto addresses."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return False
    scheme = parts.scheme.lower()
    if scheme == "https":
        return bool(parts.hostname) and parts.username is None and parts.password is None
    if scheme == "mailto":
        return bool(_EMAIL.match(parts.path)) and not parts.query and not parts.fragment
    return False


def _plain(text: str) -> str:
    return _STRAY_ANCHOR_TAG.sub("", text)


def parse_body(body: str) -> list[BodySegment]:
    """Split a body into plain and linked segments, in order."""
    segments: list[BodySegment] = []
    last_end = 0
    for match in _ANCHOR.finditer(body):
        if match.start() > last_end:
            segments.append(BodySegment(_plain(body[last_end : match.start()])))
        raw_href = next(group for group in match.groups()[:3] if group is not None)
        href = html.unescape(raw_href).strip()
        # Words stay as written, matching the Builder preview; only the
        # attribute value is entity-decoded, as a browser would.
        words = _INNER_TAG.sub("", match.group(4))
        segments.append(BodySegment(words, href if is_safe_destination(href) else None))
        last_end = match.end()
    if last_end < len(body):
        segments.append(BodySegment(_plain(body[last_end:])))
    return [segment for segment in segments if segment.text]


def _canonical(url: str) -> str:
    return unwrap_tracking_url(url.strip()).rstrip("/").lower()


def check_body(body: str, submitted_urls: Iterable[str] = ()) -> list[LinkFinding]:
    """Find link problems in a body: what export would drop, misdirect or expose.

    - unsafe_link: an anchor whose destination is not https or mailto, so it
      exports as plain words.
    - tracking_link: a destination wrapped by an email security gateway
      (Proofpoint, Safe Links, ...); readers would bounce through it.
    - bare_url: a web address written out as text instead of linked words.
    - missing_submitted_link: a link the submitter supplied that no longer
      appears in the body.
    """
    findings: list[LinkFinding] = []
    linked: set[str] = set()
    for match in _ANCHOR.finditer(body):
        raw_href = next(group for group in match.groups()[:3] if group is not None)
        href = html.unescape(raw_href).strip()
        words = _INNER_TAG.sub("", match.group(4))
        if not is_safe_destination(href):
            findings.append(LinkFinding("unsafe_link", words, href))
            continue
        linked.add(_canonical(href))
        real = unwrap_tracking_url(href)
        if real != href:
            findings.append(LinkFinding("tracking_link", words, href, real))

    for segment in parse_body(body):
        if segment.href is None:
            for url in URL_PATTERN.finditer(segment.text):
                findings.append(LinkFinding("bare_url", Href=url.group(0).rstrip(".,;:")))

    for url in submitted_urls:
        if url and _canonical(url) not in linked:
            findings.append(LinkFinding("missing_submitted_link", Href=url))
    return findings
