from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RevenueLine(BaseModel):
    """A single revenue or deduction line within a product."""

    model_config = ConfigDict(frozen=True)

    revenue_type: str

    production_period: date

    volume: Decimal | None = None

    unit_price: Decimal | None = None

    gross_value: Decimal | None = None

    owner_interest: Decimal | None = None

    distribution_interest: Decimal | None = None

    owner_volume: Decimal | None = None

    owner_value: Decimal

    @property
    def is_deduction(self) -> bool:
        return self.owner_value < 0


class RevenueProduct(BaseModel):
    """One product (Gas Sales, Oil, NGL, etc.) for a property."""

    model_config = ConfigDict(frozen=True)

    name: str

    lines: list[RevenueLine] = Field(default_factory=list)

    @property
    def total_owner_value(self) -> Decimal:
        return sum(
            (line.owner_value for line in self.lines),
            start=Decimal("0.00"),
        )


class RevenueProperty(BaseModel):
    """Revenue associated with a single producing property."""

    model_config = ConfigDict(frozen=True)

    property_code: str

    property_name: str

    county: str

    state: str

    operator_api: str | None = None

    products: list[RevenueProduct] = Field(default_factory=list)

    @property
    def total_owner_value(self) -> Decimal:
        return sum(
            (product.total_owner_value for product in self.products),
            start=Decimal("0.00"),
        )


class RevenueStatement(BaseModel):
    """Entire revenue statement (one check stub)."""

    model_config = ConfigDict(frozen=True)
    operator: str
    owner_number: str
    check_number: str
    check_date: date
    check_amount: Decimal
    properties: list[RevenueProperty] = Field(default_factory=list)
    source_file: str | None = None

    @property
    def total_owner_value(self) -> Decimal:
        return sum(
            (prop.total_owner_value for prop in self.properties),
            start=Decimal("0.00"),
        )

    @model_validator(mode="after")
    def validate_totals(self):
        if abs(self.total_owner_value - self.check_amount) > Decimal("0.01"):
            raise ValueError(
                f"Revenue lines total {self.total_owner_value} "
                f"but check amount is {self.check_amount}"
            )
        return self
