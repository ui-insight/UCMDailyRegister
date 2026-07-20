"""Tests for deterministic text post-processing utilities."""

import pytest

from app.utils.text import to_sentence_case


@pytest.mark.parametrize(
    ("headline", "expected"),
    [
        (
            "Attend Elizabeth Bradfield reading from SoFar",
            "Attend Elizabeth Bradfield reading from SoFar",
        ),
        ('"visit Copy Print Center"', '"Visit Copy Print Center"'),
        ("meet Creative Services", "Meet Creative Services"),
        ("2026 UCM planning session", "2026 UCM planning session"),
        ("", ""),
    ],
)
def test_to_sentence_case_preserves_model_casing(headline: str, expected: str):
    assert to_sentence_case(headline) == expected
