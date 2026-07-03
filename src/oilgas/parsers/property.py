from __future__ import annotations

from oilgas.document import BlockType, DocumentBlock
from oilgas.layout import Layout


class PropertyExtractor:
    """
    Splits a revenue statement into Property blocks.

    No business parsing occurs here.
    No regexes.
    No property metadata extraction.

    The only responsibility is segmentation.
    """

    def __init__(self, layout: Layout):
        self.layout = layout

    def extract(self) -> list[DocumentBlock]:

        blocks: list[DocumentBlock] = []

        current_rows = []
        start_row = None

        for row in self.layout.rows:
            #
            # Beginning of a new property section
            #
            if row.text.startswith("Property:"):
                #
                # Finish previous block
                #
                if current_rows:
                    blocks.append(
                        DocumentBlock(
                            type=BlockType.PROPERTY,
                            start_row=start_row,
                            end_row=current_rows[-1].index,
                            rows=current_rows,
                        )
                    )

                current_rows = [row]
                start_row = row.index

            #
            # Continue current property
            #
            elif current_rows:
                current_rows.append(row)

        #
        # Finish last block
        #
        if current_rows:
            blocks.append(
                DocumentBlock(
                    type=BlockType.PROPERTY,
                    start_row=start_row,
                    end_row=current_rows[-1].index,
                    rows=current_rows,
                )
            )

        return blocks
