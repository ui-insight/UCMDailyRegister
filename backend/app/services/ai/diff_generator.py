"""Generate structured diffs between original and AI-edited text."""

import difflib
from dataclasses import dataclass, field


@dataclass
class DiffSegment:
    """A segment of text that is either unchanged, added, or removed."""
    type: str  # "equal", "insert", "delete", "replace"
    original: str = ""
    modified: str = ""


@dataclass
class TextDiff:
    """Structured diff between two texts."""
    segments: list[DiffSegment] = field(default_factory=list)
    change_count: int = 0
    similarity_ratio: float = 1.0


def generate_word_diff(original: str, modified: str) -> TextDiff:
    """Generate a word-level diff between original and modified text.

    Returns a TextDiff with segments showing what changed.
    """
    if original == modified:
        return TextDiff(
            segments=[DiffSegment(type="equal", original=original, modified=original)],
            change_count=0,
            similarity_ratio=1.0,
        )

    orig_words = original.split()
    mod_words = modified.split()

    matcher = difflib.SequenceMatcher(None, orig_words, mod_words)
    ratio = matcher.ratio()

    segments: list[DiffSegment] = []
    change_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        orig_chunk = " ".join(orig_words[i1:i2])
        mod_chunk = " ".join(mod_words[j1:j2])

        if tag == "equal":
            segments.append(DiffSegment(type="equal", original=orig_chunk, modified=mod_chunk))
        elif tag == "replace":
            segments.append(DiffSegment(type="replace", original=orig_chunk, modified=mod_chunk))
            change_count += 1
        elif tag == "insert":
            segments.append(DiffSegment(type="insert", original="", modified=mod_chunk))
            change_count += 1
        elif tag == "delete":
            segments.append(DiffSegment(type="delete", original=orig_chunk, modified=""))
            change_count += 1

    return TextDiff(segments=segments, change_count=change_count, similarity_ratio=ratio)


def generate_line_diff(original: str, modified: str) -> list[dict]:
    """Generate a line-level unified diff for display.

    Returns list of dicts with 'type' (context/add/remove) and 'text'.
    """
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(orig_lines, mod_lines, lineterm="")
    result = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            continue
        elif line.startswith("@@"):
            continue
        elif line.startswith("+"):
            result.append({"type": "add", "text": line[1:]})
        elif line.startswith("-"):
            result.append({"type": "remove", "text": line[1:]})
        else:
            result.append({"type": "context", "text": line[1:] if line.startswith(" ") else line})

    return result


def diff_to_dict(diff: TextDiff) -> dict:
    """Convert a TextDiff to a JSON-serializable dict."""
    return {
        "segments": [
            {"type": s.type, "original": s.original, "modified": s.modified}
            for s in diff.segments
        ],
        "change_count": diff.change_count,
        "similarity_ratio": round(diff.similarity_ratio, 4),
    }
