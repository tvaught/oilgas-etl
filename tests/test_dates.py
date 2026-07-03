from datetime import date

from oilgas.util.dates import parse_production_period


def test_period():

    assert parse_production_period("Nov 25") == date(
        2025,
        11,
        1,
    )
