from __future__ import annotations

from datetime import date

from dateutil import parser

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_check_date(value: str) -> date:
    """
    Parse a statement check date.

    Example:
        January 20, 2026
    """

    return parser.parse(value).date()


def require_check_date(value: str | None) -> date:

    if value is None:
        raise ValueError("Missing check date.")

    return parse_check_date(value)


def parse_production_period(value: str) -> date:
    """
    Parse a production period.

    Examples:
        Nov 25
        Jan 26

    Returns the first day of the production month.
    """

    dt = parser.parse(value)

    return date(
        dt.year,
        dt.month,
        1,
    )


def require_production_period(
    value: str | None,
) -> date:

    if value is None:
        raise ValueError("Missing production period.")

    return parse_production_period(value)


def accounting_period(
    check_date: date,
) -> date:
    """
    Convert a check date into its accounting period.

    Example:
        2026-01-20 -> 2026-01-01
    """

    return date(
        check_date.year,
        check_date.month,
        1,
    )


def first_day_of_month(d: date) -> date:

    return date(
        d.year,
        d.month,
        1,
    )
