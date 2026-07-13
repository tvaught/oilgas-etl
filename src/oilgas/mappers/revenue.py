from __future__ import annotations

from uuid import UUID

from oilgas.document import DocumentBlock
from oilgas.models.header import RevenueHeader
from oilgas.models.revenue import (
    RevenueLine,
    RevenueProduct,
    RevenueProperty,
    RevenueStatement,
)
from oilgas.parsers.parser_models import ParsedRow
from oilgas.parsers.property import (
    API_NUMBER,
    COUNTY,
    PROPERTY_CODE,
    PROPERTY_NAME,
    STATE,
)
from oilgas.util.dates import parse_production_period
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
            line_type=row.fields["line_type"].text,
            revenue_type=row.fields["revenue_type"].text,
            tax_deduct_code=row.get("tax_deduct_code"),
            production_period=parse_production_period(
                row.fields["production_period"].text,
            ),
            property_volume=parse_decimal(
                row.get("property_volume"),
            ),
            unit_price=parse_decimal(
                row.get("unit_price"),
            ),
            property_gross_value=parse_decimal(
                row.get("property_gross_value"),
            ),
            property_deductions=parse_decimal(
                row.get("property_deductions"),
            ),
            property_net_value=parse_decimal(
                row.get("property_net_value"),
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
            owner_gross_value=parse_decimal(
                row.get("owner_gross_value"),
            ),
            owner_deductions=parse_decimal(
                row.get("owner_deductions"),
            ),
            owner_net_value=require_decimal(row.get("owner_net_value"), "owner_net_value"),
        )

    #
    # ------------------------------------------------------------------
    # Product
    # ------------------------------------------------------------------
    #

    def product(
        self,
        block: DocumentBlock,
        lines: list[RevenueLine],
    ) -> RevenueProduct:

        return RevenueProduct(
            product=block.metadata["product"],
            lines=lines,
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
            property_code=block.meta(PROPERTY_CODE),
            property_name=block.meta(PROPERTY_NAME),
            county=block.meta(COUNTY),
            state=block.meta(STATE),
            api_number=block.meta(API_NUMBER),
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
            check_amount=header.check_amount,
            properties=properties,
        )
