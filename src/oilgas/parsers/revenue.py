from __future__ import annotations

from oilgas.document import BlockType, DocumentBlock
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
from oilgas.parsers.property_headers import ALL_PROPERTY_HEADER_PARSERS
from oilgas.parsers.revenue_line import RevenueLineExtractor


class RevenueParser:
    def __init__(
        self,
        debug: bool = False,
    ):

        self.debug = debug
        self.mapper = RevenueMapper()

    def parse(
        self,
        document: PDFDocument,
        source_file: str,
    ) -> RevenueStatement:

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
        property_blocks = self._property_blocks(document)
        self._debug(f"{len(property_blocks)=}")

        for property_block in property_blocks:
            self._debug(property_block.metadata["property_name"])
            product_blocks = ProductExtractor(property_block).extract()

            products: list[RevenueProduct] = []
            self._debug(f"{len(product_blocks)=}")
            #
            # Walk products
            #
            for product_block in product_blocks:
                parsed_rows = RevenueLineExtractor(
                    product_block,
                    debug=self.debug,
                ).extract()

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

    def _property_blocks(
        self,
        document: PDFDocument,
    ) -> list[DocumentBlock]:
        blocks: list[DocumentBlock] = []
        current: DocumentBlock | None = None

        for page in document.pages:
            layout = Layout(page)

            for row in layout.rows:
                if self._is_page_furniture(row.text):
                    continue

                parser = next(
                    (p for p in ALL_PROPERTY_HEADER_PARSERS if p.matches(row)),
                    None,
                )

                if parser is not None:
                    if current is not None:
                        current.end_row = current.rows[-1].index
                        blocks.append(current)

                    metadata = parser.parse(row.text)

                    if metadata is None:
                        raise ValueError(
                            f"{parser.__class__.__name__} failed to parse:\n{row.text}"
                        )

                    current = DocumentBlock(
                        type=BlockType.PROPERTY,
                        start_row=row.index,
                        end_row=row.index,
                        rows=[row],
                        metadata=metadata,
                    )
                    continue

                if current is not None:
                    current.rows.append(row)

        if current is not None:
            current.end_row = current.rows[-1].index
            blocks.append(current)

        return blocks

    def _is_page_furniture(
        self,
        text: str,
    ) -> bool:
        text = text.strip()

        if not text:
            return True

        prefixes = (
            "EnergyLink Revenue Statement",
            "Owner Operator Check",
            "Check Number ",
            "CONFIDENTIAL",
            "Generated for:",
            "Property Values Owner Share",
            "Production Owner Distribution",
            "Type BTU Volume Price Value Volume Value",
            "Date Interest Interest",
            "© ",
            "Represented Unit of Measure:",
        )

        return text.startswith(prefixes)

    def _debug(
        self,
        message: object,
    ) -> None:
        if self.debug:
            print(message)
