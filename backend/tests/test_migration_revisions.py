"""Every Alembic revision ID is unique and the chain has one head."""

import re
from collections import Counter
from pathlib import Path


VERSIONS = Path(__file__).parents[1] / "alembic" / "versions"
_REVISION = re.compile(r"^revision\s*(?::[^=]+)?=\s*[\"'](\w+)[\"']", re.MULTILINE)
_DOWN = re.compile(r"^down_revision\s*(?::[^=]+)?=\s*(.+)$", re.MULTILINE)


def _revisions() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in VERSIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        match = _REVISION.search(text)
        assert match, f"{path.name} has no revision ID"
        down = _DOWN.search(text)
        found.setdefault(match.group(1), []).append(
            down.group(1) if down else "None"
        )
    return found


def test_revision_ids_are_unique():
    counts = Counter()
    for path in VERSIONS.glob("*.py"):
        match = _REVISION.search(path.read_text(encoding="utf-8"))
        counts[match.group(1)] += 1
    assert [rev for rev, count in counts.items() if count > 1] == []


def test_migration_chain_has_one_head():
    revisions = _revisions()
    referenced = set()
    for downs in revisions.values():
        for down in downs:
            referenced.update(re.findall(r"[\"'](\w+)[\"']", down))
    heads = [rev for rev in revisions if rev not in referenced]
    assert len(heads) == 1, heads
