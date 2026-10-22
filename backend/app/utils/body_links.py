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
from dataclasses import dataclass
from urllib.parse import urlsplit

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
