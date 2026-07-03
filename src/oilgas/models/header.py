from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class RevenueHeader(BaseModel):
    owner_number: str
    operator: str
    check_number: str
    check_date: date
    check_amount: Decimal
