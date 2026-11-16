"""Keep each link on the call-to-action words that carry it (#478).

Submitters often give a link in the link fields with call-to-action words
("Learn more and sign up") and also paste the same address into the body.
The AI edit then tends to show the address itself as link text, split the
call to action, or link the same page twice. UCM's rules:

1. When the body repeats a link-field address, drop the written-out address
   and let the call-to-action words carry the link.
2. Never show an address as link text, and link each address once per item.
3. One address with one call to action is a single call to action, even when
   the words name more than one action.

``repair_links`` applies the fixes it can make safely to an AI-edited body;
``link_problems`` describes what is left for staff. Staff copy in Final
Edit is never passed through here, so an address staff put back by hand
stays as written.

Bodies use the inline anchor format read by ``app.utils.body_links``. The
repair works on the visible words: anchors it doesn't change are copied
through exactly as written.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.utils.body_links import (
    ANCHOR_PATTERN,
    BARE_URL_PATTERN,
    is_safe_destination,
    link_key,
    trim_url,
)

_INNER_TAG = re.compile(r"<[^>]+>")
# Key for anchors whose destination isn't https or mailto; never edited.
_UNSAFE = "\0unsafe"
_QUOTE_CLASSES = {"'": "['‘’]", '"': "[\"“”]"}

# Words that leave a sentence hanging when the address after them is removed.
_DANGLING = re.compile(
    r"\b(?:to|at|via|on|visit|visiting|see|view|go|the|a|an|and|or|from|"
    r"through|by|for|in|of|with|website|site|page|webpage|link|here)\s*$",
    re.IGNORECASE,
)
# A sentence that only points at the address: "Visit https://...",
# "For more information, see the website at https://...".
_POINTER_ONLY = re.compile(
    r"^\s*(?:(?:for\s+(?:more\s+)?(?:information|info|details)|to\s+learn\s+more)"
    r"\s*,?\s*)?(?:please\s+)?(?:visit|go\s+to|see|check\s+out|head\s+to|"
    r"navigate\s+to|view|refer\s+to)(?:\s+(?:the|our|this)\s+(?:[\w-]+\s+)?"
    r"(?:website|web\s*site|web\s*page|page|site|link))?(?:\s+(?:online\s+)?at)?"
    r"\s*:?\s*$",
    re.IGNORECASE,
)
_INFO_AVAILABLE = re.compile(
    r"^\s*(?:more\s+|additional\s+|further\s+)?(?:information|info|details)"
    r"(?:\s+(?:is|are)\s+available)?(?:\s+online)?(?:\s+at)?\s*:?\s*$",
    re.IGNORECASE,
)
# What joins an address to the words before it: "sign up at", "online at",
# "here:", a dash. Removed with the address.
_CONNECTOR = re.compile(
    r"(?:\s+here)?(?:,?\s+(?:online\s+)?(?:at|via)|\s*[:–—]|\s+-)\s*$",
    re.IGNORECASE,
)
# Words that may stand before "at|via|: <address>" when the address goes:
# the call to action itself, which then carries the link.
_CTA_ENDING = re.compile(
    r"\b(?:learn\s+more|read\s+more|find\s+out\s+more|sign\s+up|register|"
    r"apply|rsvp|enroll|donate|subscribe|reserve\s+(?:a\s+|your\s+)?(?:spot|seat|space)|"
    r"(?:get|buy|purchase)\s+(?:your\s+)?tickets|more\s+(?:information|info|details)|"
    r"details|information|registration|tickets)\W*$",
    re.IGNORECASE,
)
_MID_CONNECTOR = re.compile(r",?\s+(?:online\s+)?(?:at|via)\s*$", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)|\n")

REPAIR_DESCRIPTION = (
    "Removed the written-out web address so the call-to-action words carry the link"
)
CTA_LINK_DESCRIPTION = "Put the link on the submitted call-to-action words"


@dataclass
class _Piece:
    """A run of visible words; ``key`` is set when the words are a link."""

    text: str
    key: str | None = None
    href: str | None = None
    raw: str | None = None  # original markup, reused while the piece is unchanged

    @property
    def is_bare(self) -> bool:
        """A link whose words are a web address."""
        return self.key is not None and _is_address(self.text)

    def render(self) -> str:
        if self.raw is not None:
            return self.raw
        if self.key is None:
            return self.text
        return f'<a href="{html.escape(self.href or "", quote=True)}">{self.text}</a>'


def _is_address(text: str) -> bool:
    words = trim_url(_INNER_TAG.sub("", html.unescape(text)).strip())
    return bool(words) and BARE_URL_PATTERN.fullmatch(words) is not None


def _parse(body: str) -> list[_Piece]:
    pieces: list[_Piece] = []
    last = 0
    for match in ANCHOR_PATTERN.finditer(body):
        if match.start() > last:
            pieces.append(_Piece(body[last:match.start()]))
        raw_href = next(group for group in match.groups()[:3] if group is not None)
        href = html.unescape(raw_href).strip()
        words = match.group(4)
        if is_safe_destination(href):
            pieces.append(_Piece(words, link_key(href), href, match.group(0)))
        else:
            pieces.append(_Piece(words, _UNSAFE, href, match.group(0)))
        last = match.end()
    if last < len(body):
        pieces.append(_Piece(body[last:]))
    return pieces


def _render(pieces: list[_Piece]) -> str:
    return "".join(piece.render() for piece in pieces)


def _visible(pieces: list[_Piece]) -> str:
    return "".join(piece.text for piece in pieces)


def _bounds(pieces: list[_Piece]) -> list[tuple[int, int]]:
    bounds, offset = [], 0
    for piece in pieces:
        bounds.append((offset, offset + len(piece.text)))
        offset += len(piece.text)
    return bounds


def _split(pieces: list[_Piece], at: int) -> list[_Piece]:
    """Split the plain piece containing visible offset ``at``."""
    out = []
    for piece, (start, end) in zip(pieces, _bounds(pieces)):
        if piece.key is None and start < at < end:
            cut = at - start
            out += [_Piece(piece.text[:cut]), _Piece(piece.text[cut:])]
        else:
            out.append(piece)
    return out


def _links_for(pieces: list[_Piece], key: str, *, bare: bool) -> list[int]:
    return [
        index
        for index, piece in enumerate(pieces)
        if piece.key == key and piece.is_bare == bare
    ]


def _delete(pieces: list[_Piece], start: int, end: int, key: str) -> list[_Piece] | None:
    """Delete visible text; only plain text and bare links to ``key`` may go."""
    pieces = _split(_split(pieces, start), end)
    out = []
    for piece, (lo, hi) in zip(pieces, _bounds(pieces)):
        inside = start <= lo and hi <= end and hi > lo
        if not inside:
            if piece.key is not None and lo < end and hi > start:
                return None  # would cut into a link
            out.append(piece)
        elif piece.key is not None and not (piece.key == key and piece.is_bare):
            return None  # would delete a real link
    return out


def _cta_pattern(cta: str) -> re.Pattern[str]:
    words = []
    for word in cta.split():
        words.append("".join(_QUOTE_CLASSES.get(char, re.escape(char)) for char in word))
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)", re.IGNORECASE)


def _wrap_cta(pieces: list[_Piece], key: str, href: str, cta: str) -> list[_Piece] | None:
    """Link the call-to-action words, merging any part already linked to ``key``.

    Returns None when the words aren't in the body, are already the link,
    touch another link, or the address is already linked elsewhere (that
    would link it twice).
    """
    if not cta.strip() or _is_address(cta):
        return None
    visible = _visible(pieces)
    for match in _cta_pattern(cta).finditer(visible):
        start, end = match.span()
        bounds = _bounds(pieces)
        # Grow the span to cover any link to the same page it touches.
        for piece, (lo, hi) in zip(pieces, bounds):
            if piece.key == key and not piece.is_bare and lo < end and hi > start:
                start, end = min(start, lo), max(end, hi)
        touched = [
            (piece, lo, hi)
            for piece, (lo, hi) in zip(pieces, bounds)
            if lo < end and hi > start
        ]
        if any(piece.key not in (None, key) or piece.is_bare for piece, _, _ in touched):
            continue
        if len(touched) == 1 and touched[0][0].key == key:
            return None  # already carries the link
        elsewhere = [
            index
            for index in _links_for(pieces, key, bare=False)
            if not (start <= bounds[index][0] and bounds[index][1] <= end)
        ]
        if elsewhere:
            return None
        hrefs = [piece.href for piece, _, _ in touched if piece.key == key]
        split = _split(_split(pieces, start), end)
        before, linked, after = [], [], []
        for piece, (lo, hi) in zip(split, _bounds(split)):
            (before if hi <= start else after if lo >= end else linked).append(piece)
        words = "".join(piece.text for piece in linked)
        return before + [_Piece(words, key, hrefs[0] if hrefs else href)] + after
    return None


def _occurrences(pieces: list[_Piece], key: str) -> list[tuple[int, int]]:
    """Visible spans where the address for ``key`` is written out."""
    spans = []
    for piece, (lo, _hi) in zip(pieces, _bounds(pieces)):
        if piece.key == key and piece.is_bare:
            spans.append((lo, lo + len(piece.text)))
        elif piece.key is None:
            for match in BARE_URL_PATTERN.finditer(piece.text):
                text = trim_url(match.group(0))
                if link_key(text) == key:
                    spans.append((lo + match.start(), lo + match.start() + len(text)))
    return spans


_QUOTE_FOLD = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})


def _ends_with_cta(kept: str, cta_texts: list[str]) -> bool:
    """Whether the words kept before a removed address are a call to action."""
    def fold(text: str) -> str:
        return " ".join(text.translate(_QUOTE_FOLD).lower().split())

    tail = fold(kept)
    if any(cta.strip() and tail.endswith(fold(cta)) for cta in cta_texts):
        return True
    return bool(_CTA_ENDING.search(kept))


def _removal_span(
    visible: str, start: int, end: int, cta_texts: list[str] | None = None
) -> tuple[int, int] | None:
    """The visible span to delete with the address, or None when unsure.

    Handles: the address in parentheses; a sentence that only points at the
    address ("Visit ...", "More information is available at ..."); and
    "<words> at|via|online at|here:|— <address>", where the words before stay.
    """
    sentence_start = 0
    for match in _SENTENCE_END.finditer(visible, 0, start):
        sentence_start = match.end()
    after_end = _SENTENCE_END.search(visible, end)
    sentence_end = after_end.start() if after_end else len(visible)
    left = visible[sentence_start:start]
    right = visible[end:sentence_end]
    at_end = not right.strip()

    if visible[start - 1:start] == "(" and visible[end:end + 1] == ")":
        lead = len(visible[:start - 1]) - len(visible[:start - 1].rstrip())
        return start - 1 - lead, end + 1

    if at_end and (not left.strip() or _POINTER_ONLY.match(left) or _INFO_AVAILABLE.match(left)):
        if after_end is not None and after_end.group() != "\n":
            sentence_end = after_end.end()
        trailing = len(visible[sentence_end:]) - len(visible[sentence_end:].lstrip(" \t"))
        if sentence_end + trailing < len(visible) and visible[sentence_end + trailing] != "\n":
            lead = len(left) - len(left.lstrip())
            return sentence_start + lead, sentence_end + trailing
        lead = len(visible[:sentence_start]) - len(visible[:sentence_start].rstrip(" \t"))
        return sentence_start - lead, sentence_end

    # Otherwise only "<call to action> at|via|: <address>" is reworked. An
    # address that is the sentence's information ("The code is <address>",
    # "The meeting is at <address>") stays, and link_problems flags it.
    connector = (_CONNECTOR if at_end else _MID_CONNECTOR).search(left)
    if not connector:
        return None
    kept = left[: connector.start()]
    if not kept.strip() or _DANGLING.search(kept) or not _ends_with_cta(kept, cta_texts or []):
        return None
    return sentence_start + connector.start(), end


def _repair_key(
    pieces: list[_Piece],
    key: str,
    ctas: list[tuple[str, str]],
) -> tuple[list[_Piece], list[str]] | None:
    """Fix one destination; None when nothing changed or the link would be lost."""
    notes: list[str] = []

    def try_ctas(current: list[_Piece]) -> list[_Piece]:
        for href, cta in ctas:
            wrapped = _wrap_cta(current, key, href, cta)
            if wrapped is not None:
                if CTA_LINK_DESCRIPTION not in notes:
                    notes.append(CTA_LINK_DESCRIPTION)
                return wrapped
        return current

    work = try_ctas(pieces)
    removed = False
    # Last first, so the earlier spans keep their offsets.
    for start, end in reversed(_occurrences(work, key)):
        span = _removal_span(_visible(work), start, end, [cta for _href, cta in ctas])
        candidate = None if span is None else _delete(work, *span, key)
        if candidate is not None:
            work, removed = candidate, True
    # Removing "at <address>" can bring split call-to-action words together.
    work = try_ctas(work)
    if removed:
        notes.insert(0, REPAIR_DESCRIPTION)
    if not notes or not _links_for(work, key, bare=False):
        return None
    return work, notes


def repair_links(body: str, links: Iterable[dict]) -> tuple[str, list[str]]:
    """Apply UCM's link rules to an AI-edited body (#478).

    ``links`` are the submission's link fields, as ``{"url", "anchor_text"}``.
    For every destination that is linked in the body or given in a link
    field, a written-out copy of its address is removed when the sentence
    can be safely reworked, and the submitted call-to-action words are
    linked when they appear in the body. Returns the body and a change note
    per kind of fix; the body is unchanged when nothing could be fixed safely.
    """
    pieces = _parse(body)
    ctas: dict[str, list[tuple[str, str]]] = {}
    keys: list[str] = []
    for link in links:
        url = (link.get("url") or "").strip()
        if not url or not is_safe_destination(url):
            continue
        key = link_key(url)
        ctas.setdefault(key, [])
        if link.get("anchor_text"):
            ctas[key].append((url, str(link["anchor_text"]).strip()))
        if key not in keys:
            keys.append(key)
    for piece in pieces:
        if piece.key and piece.key != _UNSAFE and piece.key not in keys:
            keys.append(piece.key)

    notes: list[str] = []
    for key in keys:
        result = _repair_key(pieces, key, ctas.get(key, []))
        if result is None:
            continue
        pieces, key_notes = result
        notes += [note for note in key_notes if note not in notes]
    if not notes:
        return body, []
    return _render(pieces), notes


def link_problems(body: str) -> list[str]:
    """Link problems left in an AI-edited body, as messages for staff."""
    pieces = _parse(body)
    linked_words: dict[str, str] = {}
    counts: dict[str, int] = {}
    for piece in pieces:
        if piece.key and piece.key != _UNSAFE:
            counts[piece.key] = counts.get(piece.key, 0) + 1
            if not piece.is_bare:
                linked_words.setdefault(piece.key, _INNER_TAG.sub("", piece.text))

    problems: list[str] = []
    for piece in pieces:
        if piece.key is None:
            for match in BARE_URL_PATTERN.finditer(piece.text):
                address = trim_url(match.group(0))
                words = linked_words.get(link_key(address))
                if words:
                    problems.append(
                        f"Web address '{address}' repeats the link on '{words}'. "
                        "Remove it and rework the sentence."
                    )
                else:
                    problems.append(
                        f"Web address written out as text: '{address}'. Link "
                        "descriptive words instead, unless UCM is running the "
                        "address as written."
                    )
        elif piece.is_bare:
            problems.append(
                f"Link text is a web address: '{_INNER_TAG.sub('', piece.text)}'. "
                "Link the call-to-action words instead."
            )
    for piece in pieces:
        if piece.key and counts.get(piece.key, 0) > 1 and not piece.is_bare:
            problems.append(
                f"'{piece.href}' is linked {counts[piece.key]} times. Link it once."
            )
            counts[piece.key] = 0
    return problems
