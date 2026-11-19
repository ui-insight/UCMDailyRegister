"""AP-style date formatting for newsletter output.

AP abbreviates January, February, August, September, October, November and
December when they appear with a specific day ("Nov. 18, 2026") and always
spells out March through July. Days are never zero-padded.
"""

from datetime import date

AP_MONTHS = {
    1: "Jan.",
    2: "Feb.",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "Aug.",
    9: "Sept.",
    10: "Oct.",
    11: "Nov.",
    12: "Dec.",
}


def ap_month_day(value: date) -> str:
    """Return the AP month and day, e.g. "Nov. 18" or "March 3"."""
    return f"{AP_MONTHS[value.month]} {value.day}"


def ap_date(value: date) -> str:
    """Return the full AP date with year, e.g. "Nov. 18, 2026"."""
    return f"{ap_month_day(value)}, {value.year}"
