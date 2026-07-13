from pathlib import Path

from oilgas.extractors.models import PDFDocument, PDFPage, PDFWord
from oilgas.parsers.product import ProductExtractor
from oilgas.parsers.revenue import RevenueParser


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


def page(number: int, rows: list[str]) -> PDFPage:
    words = []

    for row_index, text in enumerate(rows):
        y = 20 + row_index * 10

        for word_index, token in enumerate(text.split()):
            words.append(word(token, 20 + word_index * 10, y, word_index))

    return PDFPage(
        number=number,
        width=800,
        height=600,
        rotation=0,
        text="\n".join(rows),
        words=words,
    )


def test_property_block_continues_across_page_break_before_next_property() -> None:
    document = PDFDocument(
        path=Path("statement.pdf"),
        page_count=2,
        pages=[
            page(
                1,
                [
                    "Property: 10*20345 FJLU TR 853 GAS/NGL 7/04, State: TX, County: HENDERSON",
                    "GAS SALES",
                    "WORKING INTEREST Apr 26 263.73 2.19 578.27 0.14852000 0.14852000 39.17 85.88",
                    "TEXAS SEVERANCE TAX Apr 26 (42.06) 0.14852000 0.14852000 (6.25)",
                    "TRANSPORTATION Apr 26 (20.28) 0.14852000 0.14852000 (3.01)",
                    "Total GAS SALES 39.17 76.62",
                    "NATURAL GAS LIQUIDS",
                    "WORKING INTEREST Apr 26 13.35 42.88 572.41 0.14852000 0.14852000 1.98 85.01",
                    "CONFIDENTIAL - footer text",
                ],
            ),
            page(
                2,
                [
                    "Check Number 139639 Owner 16556 WHITE HAT EXPLORATION LTD "
                    "Operator HIGHMARK ENERGY OPERATING LLC",
                    "Generated for: White Hat Exploration Ltd Ltd",
                    "Property Values Owner Share",
                    "Production Owner Distribution",
                    "Type BTU Volume Price Value Volume Value",
                    "Date Interest Interest",
                    "TEXAS SEVERANCE TAX Apr 26 (41.58) 0.14852000 0.14852000 (6.18)",
                    "TRANSPORTATION Apr 26 (17.95) 0.14852000 0.14852000 (2.67)",
                    "Total NATURAL GAS LIQUIDS 1.98 76.16",
                    "Total Property 152.78",
                    "Property: 10*20346 FJLU TR 854, State: TX, County: HENDERSON",
                    "GAS SALES",
                ],
            ),
        ],
    )

    property_blocks = RevenueParser()._property_blocks(document)

    fjlu_853 = property_blocks[0]
    product_blocks = ProductExtractor(fjlu_853).extract()
    ngl = product_blocks[1]
    ngl_text = ngl.text

    assert fjlu_853.metadata["property_name"] == "FJLU TR 853 GAS/NGL 7/04"
    assert "TEXAS SEVERANCE TAX Apr 26 (41.58)" in ngl_text
    assert "TRANSPORTATION Apr 26 (17.95)" in ngl_text
    assert "Check Number 139639" not in ngl_text
    assert "Generated for:" not in ngl_text
    assert property_blocks[1].metadata["property_name"] == "FJLU TR 854"
