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

        self.mapper = RevenueMapper()

    def parse(
        self,
        document: PDFDocument,
        source_file: str,
    ) -> RevenueStatement:

        #
        # Revenue statements are currently one page.
        #
        page1 = document.pages[0]

        #
        # Header
        #
        header = None

        for page in document.pages:
            layout = Layout(page)

            if layout.find_phrase("Check Number") is None:
                continue

            header = HeaderExtractor(layout).extract()
            break

        if header is None:
            raise ValueError("Could not locate statement header.")

        properties: list[RevenueProperty] = []

        #
        # Property blocks
        #
        for page in document.pages:
            layout = Layout(page)

            property_blocks = PropertyExtractor(layout).extract()
            print(f"{len(property_blocks)=}")
            #
            # Walk properties
            #
            if not property_blocks:
                continue

            for property_block in property_blocks:
                print(property_block.metadata["property_name"])
                product_blocks = ProductExtractor(property_block).extract()

                products: list[RevenueProduct] = []
                print(f"{len(product_blocks)=}")
                #
                # Walk products
                #
                for product_block in product_blocks:
                    parsed_rows = RevenueLineExtractor(product_block).extract()

                    lines = [self.mapper.line(row) for row in parsed_rows]

                    product = self.mapper.product(
                        product_block,
                        lines,
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
