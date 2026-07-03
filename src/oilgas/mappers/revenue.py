from __future__ import annotations

from uuid import UUID

from oilgas.document import DocumentBlock
from oilgas.models.header import RevenueHeader
from oilgas.models.parser import ParsedRow
from oilgas.models.revenue import (
    RevenueLine,
    RevenueProduct,
    RevenueProperty,
    RevenueStatement,
)
from oilgas.util.dates import (
    parse_check_date,
    parse_production_period,
)
from oilgas.util.numbers import parse_decimal, require_decimal


class RevenueMapper:
    """
    Converts parser output into business models.

    The parser discovers document structure.
    The mapper assigns business meaning.
    """

    #
    # ------------------------------------------------------------------
    # Revenue Line
    # ------------------------------------------------------------------
    #

    def line(
        self,
        row: ParsedRow,
    ) -> RevenueLine:

        return RevenueLine(
            revenue_type=row.fields["revenue_type"],
            production_period=parse_production_period(
                row.fields["production_period"],
            ),
            volume=parse_decimal(
                row.get("volume"),
            ),
            unit_price=parse_decimal(
                row.get("unit_price"),
            ),
            gross_value=parse_decimal(
                row.get("gross_value"),
            ),
            owner_interest=parse_decimal(
                row.get("owner_interest"),
            ),
            distribution_interest=parse_decimal(
                row.get("distribution_interest"),
            ),
            owner_volume=parse_decimal(
                row.get("owner_volume"),
            ),
            owner_value=require_decimal(
                row.fields["owner_value"],
                "owner_value",
            ),
        )

    #
    # ------------------------------------------------------------------
    # Product
    # ------------------------------------------------------------------
    #

    def product(
        self,
        block: DocumentBlock,
        rows: list[ParsedRow],
    ) -> RevenueProduct:

        return RevenueProduct(
            name=block.metadata["product"],
            lines=[self.line(r) for r in rows],
        )

    #
    # ------------------------------------------------------------------
    # Property
    # ------------------------------------------------------------------
    #

    def property(
        self,
        block: DocumentBlock,
        products: list[RevenueProduct],
    ) -> RevenueProperty:

        return RevenueProperty(
            property_code=block.metadata["property_code"],
            property_name=block.metadata["property_name"],
            county=block.metadata["county"],
            state=block.metadata["state"],
            operator_api=block.metadata.get("operator_api"),
            products=products,
        )

    #
    # ------------------------------------------------------------------
    # Statement
    # ------------------------------------------------------------------
    #

    def statement(
        self,
        header: RevenueHeader,
        properties: list[RevenueProperty],
        source_file: UUID | None = None,
    ) -> RevenueStatement:
        return RevenueStatement(
            operator=header.operator,
            owner_number=header.owner_number,
            check_number=header.check_number,
            check_date=header.check_date,
            accounting_period=accounting_period(
                header.check_date,
            ),
            check_amount=header.check_amount,
            properties=properties,
            source_file=source_file,
        )
