from __future__ import annotations

from dataclasses import dataclass


class ColumnMap:
    """revenue_type
    production_period
    volume
    price
    gross
    owner_interest
    distribution_interest
    owner_volume
    owner_value"""

    pass


@dataclass(slots=True)
class Column:
    name: str
    center_x: float

    def contains(self, x: float) -> bool:
        return self.x0 <= x < self.x1


DEFAULT_COLUMNS = [
    Column("revenue_type", 60),
    Column("production_period", 160),
    Column("volume", 422),
    Column("unit_price", 476),
    Column("gross_value", 531),
    Column("owner_interest", 586),
    Column("distribution_interest", 636),
    Column("owner_volume", 701),
    Column("owner_value", 756),
]
