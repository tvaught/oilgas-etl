from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class JIBCostCenterSummary(BaseModel):
    cost_center_code: str
    cost_center_name: str | None = None
    afe: str | None = None
    description: str | None = None
    gross_amount: Decimal | None = None
    cash_call_amount: Decimal | None = None
    invoiced_amount: Decimal
    display_order: int


class JIBLine(BaseModel):
    cost_center_code: str
    cost_center_name: str | None = None
    afe: str | None = None
    cost_class: str | None = None
    account_group: str | None = None
    op_account: str
    minor_account: str | None = None
    description: str
    vendor_name: str | None = None
    vendor_invoice: str | None = None
    activity_period: date
    partner_percent: Decimal
    gross_amount: Decimal
    invoiced_amount: Decimal
    display_order: int


class JIBInvoice(BaseModel):
    operator: str
    owner_number: str | None = None
    invoice_number: str
    invoice_date: date
    accounting_period: date
    invoice_total: Decimal
    payment_status: str | None = None
    cost_centers: list[JIBCostCenterSummary] = Field(default_factory=list)
    lines: list[JIBLine] = Field(default_factory=list)

    @property
    def line_total(self) -> Decimal:
        return sum(
            (line.invoiced_amount for line in self.lines),
            start=Decimal("0.00"),
        )

    @property
    def summary_total(self) -> Decimal:
        return sum(
            (summary.invoiced_amount for summary in self.cost_centers),
            start=Decimal("0.00"),
        )

    @model_validator(mode="after")
    def validate_totals(self):
        if abs(self.summary_total - self.invoice_total) > Decimal("0.01"):
            raise ValueError(
                f"JIB summary total {self.summary_total} does not match "
                f"invoice total {self.invoice_total}."
            )

        if not self.lines:
            raise ValueError("JIB invoice contains no detail lines.")

        if abs(self.line_total - self.invoice_total) > Decimal("0.01"):
            raise ValueError(
                f"JIB detail total {self.line_total} does not match "
                f"invoice total {self.invoice_total}."
            )

        summary_by_cost_center: dict[str, Decimal] = {}
        for summary in self.cost_centers:
            summary_by_cost_center.setdefault(summary.cost_center_code, Decimal("0.00"))
            summary_by_cost_center[summary.cost_center_code] += summary.invoiced_amount

        line_by_cost_center: dict[str, Decimal] = {}
        for line in self.lines:
            line_by_cost_center.setdefault(line.cost_center_code, Decimal("0.00"))
            line_by_cost_center[line.cost_center_code] += line.invoiced_amount

        for cost_center_code, summary_amount in summary_by_cost_center.items():
            line_amount = line_by_cost_center.get(cost_center_code, Decimal("0.00"))
            if abs(line_amount - summary_amount) > Decimal("0.01"):
                raise ValueError(
                    f"JIB cost center {cost_center_code} detail total {line_amount} "
                    f"does not match summary total {summary_amount}."
                )

        return self
