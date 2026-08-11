from datetime import date

from flask import Flask, request

from oilgas.web.filters import ReportFilters, parse_month


def test_parse_month_accepts_valid_months_and_rejects_invalid_values() -> None:
    assert parse_month("2026-06") == date(2026, 6, 1)
    assert parse_month("2026-13") is None
    assert parse_month("June 2026") is None
    assert parse_month(None) is None


def test_report_filters_preserve_repeated_dimensions_and_normalize_rollup() -> None:
    app = Flask(__name__)
    with app.test_request_context(
        "/?start_month=2026-01&end_month=2026-06"
        "&operator=Highmark&operator=XTO"
        "&property=Well+A&product=OIL&cost_center=CC+A"
        "&cumulative=1&rollup=invalid"
    ):
        filters = ReportFilters.from_request(request)

    assert filters.start_month == date(2026, 1, 1)
    assert filters.end_month == date(2026, 6, 1)
    assert filters.operators == ("Highmark", "XTO")
    assert filters.properties == ("Well A",)
    assert filters.products == ("OIL",)
    assert filters.cost_centers == ("CC A",)
    assert filters.cumulative is True
    assert filters.rollup == "monthly"
