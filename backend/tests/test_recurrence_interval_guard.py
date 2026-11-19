"""expand_recurrence must not hang on a nonpositive interval (#488 review)."""

from datetime import date

import pytest

from app.services.recurrence_service import expand_recurrence


@pytest.mark.parametrize("bad_interval", [0, -1, -3])
@pytest.mark.parametrize(
    ("recurrence_type", "anchor", "expected"),
    [
        ("weekly", date(2027, 1, 4), [date(2027, 1, 4), date(2027, 1, 11), date(2027, 1, 18)]),
        ("monthly_date", date(2027, 1, 15), [date(2027, 1, 15), date(2027, 2, 15), date(2027, 3, 15)]),
        # 2nd Tuesday of each month
        ("monthly_nth_weekday", date(2027, 1, 12), [date(2027, 1, 12), date(2027, 2, 9), date(2027, 3, 9)]),
    ],
)
def test_nonpositive_interval_behaves_like_one(bad_interval, recurrence_type, anchor, expected):
    occurrences = expand_recurrence(
        anchor=anchor,
        recurrence_type=recurrence_type,
        interval=bad_interval,
        from_date=expected[0],
        to_date=expected[-1],
    )
    assert occurrences == expected
