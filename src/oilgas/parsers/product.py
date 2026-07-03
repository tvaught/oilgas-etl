from __future__ import annotations

from oilgas.document import BlockType, DocumentBlock

PRODUCT_TOTAL_PREFIX = "Total "


class ProductExtractor:
    """
    Splits a Property block into Product blocks.

    Input:
        Property DocumentBlock

    Output:
        list[DocumentBlock(type=PRODUCT)]
    """

    def extract(
        self,
        property_block: DocumentBlock,
    ) -> list[DocumentBlock]:

        blocks: list[DocumentBlock] = []

        current_rows = []

        start_row = None

        current_product = None

        #
        # Skip the property header.
        #
        for row in property_block.rows[1:]:
            text = row.text.strip()

            #
            # Ignore blank rows.
            #
            if not text:
                continue

            #
            # Total Property terminates the final product.
            #
            if text.startswith("Total Property"):
                if current_rows:
                    blocks.append(
                        DocumentBlock(
                            type=BlockType.PRODUCT,
                            start_row=start_row,
                            end_row=current_rows[-1].index,
                            rows=current_rows,
                            metadata={
                                "product": current_product,
                            },
                        )
                    )

                break

            #
            # Product totals terminate the current product.
            #
            if text.startswith(PRODUCT_TOTAL_PREFIX) and current_product is not None:
                current_rows.append(row)

                blocks.append(
                    DocumentBlock(
                        type=BlockType.PRODUCT,
                        start_row=start_row,
                        end_row=row.index,
                        rows=current_rows,
                        metadata={
                            "product": current_product,
                        },
                    )
                )

                current_rows = []

                current_product = None

                continue

            #
            # Detect a new product.
            #
            if (
                current_product is None
                and text.isupper()
                and "INTEREST" not in text
                and "TRANSPORTATION" not in text
                and "SEVERANCE" not in text
                and "WORKING" not in text
            ):
                current_product = text
                start_row = row.index
                current_rows = [row]
                continue

            #
            # Inside a product.
            #
            if current_product is not None:
                current_rows.append(row)

        return blocks
