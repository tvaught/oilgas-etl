from __future__ import annotations

import re

from oilgas.document import BlockType, DocumentBlock
from oilgas.layout import Layout
from oilgas.parsers.property_headers import ALL_PROPERTY_HEADER_PARSERS

PROPERTY_CODE = "property_code"
PROPERTY_NAME = "property_name"
STATE = "state"
COUNTY = "county"
API_NUMBER = "api_number"


class PropertyExtractor:
    """
    Splits a revenue statement into Property blocks.

    No business parsing occurs here.
    No regexes.
    No property metadata extraction.

    The only responsibility is segmentation.
    """

    def __init__(
        self,
        layout: Layout,
    ):

        self.layout = layout

        self.header_parsers = ALL_PROPERTY_HEADER_PARSERS

    def extract(
        self,
    ) -> list[DocumentBlock]:

        blocks: list[DocumentBlock] = []

        current: DocumentBlock | None = None

        for row in self.layout.rows:
            parser = next(
                (p for p in self.header_parsers if p.matches(row)),
                None,
            )

            #
            # New property begins.
            #
            if parser is not None:
                if current is not None:
                    current.end_row = current.rows[-1].index
                    blocks.append(current)

                metadata = parser.parse(row.text)

                if metadata is None:
                    raise ValueError(f"{parser.__class__.__name__} failed to parse:\n{row.text}")

                current = DocumentBlock(
                    type=BlockType.PROPERTY,
                    start_row=row.index,
                    end_row=row.index,
                    rows=[row],
                    metadata=metadata,
                )

                continue

            #
            # Continue current property.
            #
            if current is not None:
                current.rows.append(row)

        #
        # Finish final property.
        #
        if current is not None:
            current.end_row = current.rows[-1].index
            blocks.append(current)

        return blocks
