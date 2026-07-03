from decimal import Decimal, InvalidOperation

from oilgas.util.numbers import parse_decimal


def test_accounting_number():

    assert parse_decimal("(95.97)") == Decimal("-95.97")


def test_remove_commas():

    assert parse_decimal("2,583.61") == Decimal("2583.61")
