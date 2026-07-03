from __future__ import annotations

from decimal import Decimal, InvalidOperation


def remove_thousands(text: str) -> str:
    return text.replace(",", "")


def is_accounting_negative(text: str) -> bool:
    return text.startswith("(") and text.endswith(")")


def normalize_number(text: str) -> str:
    """
    Converts:

        (95.97)   -> -95.97
        1,234.56  -> 1234.56
    """

    value = text.strip()

    negative = is_accounting_negative(value)

    value = value.strip("()")
    value = remove_thousands(value)

    if negative:
        value = "-" + value

    return value


def parse_decimal(text: str | None) -> Decimal | None:

    if text is None:
        return None

    text = text.strip()

    if text == "":
        return None

    try:
        return Decimal(normalize_number(text))

    except InvalidOperation:
        return None


def require_decimal(text: str | None, field_name: str) -> Decimal:
    value = parse_decimal(text)

    if value is None:
        raise ValueError(f"Missing required decimal field: {field_name}")

    return value


def parse_int(text: str | None) -> int | None:

    d = parse_decimal(text)

    return int(d) if d is not None else None


def parse_float(text: str | None) -> float | None:

    d = parse_decimal(text)

    return float(d) if d is not None else None


def parse_percent(text: str | None) -> Decimal | None:
    return parse_decimal(text)
