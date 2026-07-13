from oilgas.document import BlockType, DocumentBlock
from oilgas.extractors.models import PDFWord
from oilgas.layout.rows import LayoutRow
from oilgas.parsers.product import ProductExtractor


def word(text: str, x: float, y: float, index: int) -> PDFWord:
    return PDFWord(
        text=text,
        x0=x,
        y0=y,
        x1=x + 1,
        y1=y + 1,
        block=0,
        line=0,
        word=index,
    )


def row(index: int, text: str) -> LayoutRow:
    y = 20 + index * 10
    return LayoutRow(
        index=index,
        y=y,
        words=[word(token, 20 + i * 10, y, i) for i, token in enumerate(text.split())],
    )


def test_joint_interest_billing_is_product_heading() -> None:
    property_block = DocumentBlock(
        type=BlockType.PROPERTY,
        start_row=0,
        end_row=4,
        metadata={
            "property_code": "10*JIBNET",
            "property_name": "JIB NETTING WELL",
            "state": "TX",
            "county": "UNKNOWN",
            "api_number": None,
        },
        rows=[
            row(0, "Property: 10*JIBNET JIB NETTING WELL, State: TX, County: UNKNOWN"),
            row(1, "JOINT INTEREST BILLING"),
            row(2, "WORKING INTEREST May 26 0.00 0.00 1.00000000 1.00000000 0.00 (1,307.69)"),
            row(3, "Total JOINT INTEREST BILLING 0.00 (1,307.69)"),
            row(4, "Total Property (1,307.69)"),
        ],
    )

    product_blocks = ProductExtractor(property_block).extract()

    assert len(product_blocks) == 1
    assert product_blocks[0].metadata["product"] == "JOINT INTEREST BILLING"
    assert "WORKING INTEREST May 26" in product_blocks[0].text
