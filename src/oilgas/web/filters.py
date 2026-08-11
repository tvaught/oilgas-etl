from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from flask import Request


@dataclass(frozen=True)
class ReportFilters:
    start_month: date | None = None
    end_month: date | None = None
    operators: tuple[str, ...] = ()
    properties: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    cost_centers: tuple[str, ...] = ()
    revenue_date_basis: str = "production"
    jib_date_basis: str = "accounting"
    adjustment_basis: str = "include"
    cumulative: bool = False
    rollup: str = "monthly"

    @property
    def start_month_value(self) -> str:
        return self.start_month.strftime("%Y-%m") if self.start_month else ""

    @property
    def end_month_value(self) -> str:
        return self.end_month.strftime("%Y-%m") if self.end_month else ""

    @classmethod
    def from_request(cls, request: Request) -> ReportFilters:
        return cls(
            start_month=parse_month(request.args.get("start_month")),
            end_month=parse_month(request.args.get("end_month")),
            operators=tuple(request.args.getlist("operator")),
            properties=tuple(request.args.getlist("property")),
            products=tuple(request.args.getlist("product")),
            cost_centers=tuple(request.args.getlist("cost_center")),
            revenue_date_basis=request.args.get("revenue_date", "production"),
            jib_date_basis=request.args.get("jib_date", "accounting"),
            adjustment_basis=request.args.get("adjustments", "include"),
            cumulative=request.args.get("cumulative") == "1",
            rollup=_parse_rollup(request.args.get("rollup")),
        )


def _parse_rollup(value: str | None) -> str:
    return value if value in {"monthly", "quarterly", "annual"} else "monthly"


def parse_month(value: str | None) -> date | None:
    if not value:
        return None
    try:
        year, month = (int(part) for part in value.split("-", maxsplit=1))
        return date(year, month, 1)
    except (TypeError, ValueError):
        return None
