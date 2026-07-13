from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RevenueLine(BaseModel):
    """A single revenue or deduction line within a product."""

    model_config = ConfigDict(frozen=True)
    line_type: str
    revenue_type: str
    tax_deduct_code: str | None = None
    production_period: date
    property_volume: Decimal | None = None
    unit_price: Decimal | None = None

    property_gross_value: Decimal | None = None
    property_deductions: Decimal | None = None
    property_net_value: Decimal | None = None

    owner_interest: Decimal | None = None
    distribution_interest: Decimal | None = None

    owner_volume: Decimal | None = None

    owner_gross_value: Decimal | None = None
    owner_deductions: Decimal | None = None
    owner_net_value: Decimal

    @property
    def is_deduction(self) -> bool:
        return self.owner_net_value < 0


class RevenueProduct(BaseModel):
    """One product (Gas Sales, Oil, NGL, etc.) for a property."""

    model_config = ConfigDict(frozen=True)

    product: str

    lines: list[RevenueLine] = Field(default_factory=list)

    @property
    def total_owner_value(self) -> Decimal:
        return sum(
            (line.owner_net_value for line in self.lines),
            start=Decimal("0.00"),
        )


class RevenueProperty(BaseModel):
    """Revenue associated with a single producing property."""

    model_config = ConfigDict(frozen=True)
    property_code: str
    property_name: str
    county: str
    state: str
    api_number: str | None = None
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

    @property
    def accounting_period(self) -> date:
        return self.check_date.replace(day=1)

    @property
    def total_owner_value(self) -> Decimal:
        return sum(
            (prop.total_owner_value for prop in self.properties),
            start=Decimal("0.00"),
        )

    @model_validator(mode="after")
    def validate_totals(self):
        # if abs(self.total_owner_value - self.check_amount) > Decimal("0.01"):

        # TODO: Disable for now: raise ValueError(
        # f"Revenue lines total {self.total_owner_value} "
        # f"but check amount is {self.check_amount}"
        # TODO END: )
        return self
