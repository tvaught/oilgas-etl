from __future__ import annotations

from oilgas.extractors.models import PDFDocument
from oilgas.layout import Layout
from oilgas.mappers.revenue import RevenueMapper
from oilgas.models.revenue import (
    RevenueProduct,
    RevenueProperty,
    RevenueStatement,
)
from oilgas.parsers.header import HeaderExtractor
from oilgas.parsers.product import ProductExtractor
from oilgas.parsers.property import PropertyExtractor
from oilgas.parsers.revenue_line import RevenueLineExtractor


class RevenueParser:
    def __init__(self):

        self.header_extractor = HeaderExtractor()

        self.property_extractor = PropertyExtractor()

        self.product_extractor = ProductExtractor()

        self.line_extractor = RevenueLineExtractor()

        self.mapper = RevenueMapper()

    def parse(
        self,
        document: PDFDocument,
    ) -> RevenueStatement:

        #
        # Revenue statements are currently one page.
        #
        page = document.pages[0]

        layout = Layout(page)

        #
        # Header
        #
        header = self.header_extractor.extract(layout)

        #
        # Property blocks
        #
        property_blocks = self.property_extractor.extract(layout)

        properties: list[RevenueProperty] = []

        #
        # Walk properties
        #
        for property_block in property_blocks:
            product_blocks = self.product_extractor.extract(
                property_block,
            )

            products: list[RevenueProduct] = []

            #
            # Walk products
            #
            for product_block in product_blocks:
                parsed_rows = self.line_extractor.extract(
                    product_block,
                )

                product = self.mapper.product(
                    product_block,
                    parsed_rows,
                )

                products.append(product)

            property_model = self.mapper.property(
                property_block,
                products,
            )

            properties.append(property_model)

        #
        # Build statement
        #
        return self.mapper.statement(
            header=header,
            properties=properties,
        )
