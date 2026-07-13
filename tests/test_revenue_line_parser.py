from decimal import Decimal

import pytest

from oilgas.document import BlockType, DocumentBlock
from oilgas.extractors.models import PDFWord
from oilgas.layout.rows import LayoutRow
from oilgas.parsers.parser_models import ParsedRow
from oilgas.parsers.revenue_line import (
    LINE_TYPE,
    OWNER_NET_VALUE,
    OWNER_VOLUME,
    REVENUE_TYPE,
    RevenueLineExtractor,
)
from oilgas.util.numbers import parse_decimal


def parsed_row(
    line_type: str,
    owner_net_value: str | None = None,
    owner_volume: str | None = None,
) -> ParsedRow:
    row = ParsedRow()
    row.add(LINE_TYPE, line_type, 100)
    row.add(REVENUE_TYPE, line_type, 100)

    if owner_net_value is not None:
        row.add(OWNER_NET_VALUE, owner_net_value, 760)

    if owner_volume is not None:
        row.add(OWNER_VOLUME, owner_volume, 712)

    return row


def extractor() -> RevenueLineExtractor:
    return RevenueLineExtractor.__new__(RevenueLineExtractor)


def word(
    text: str,
    center_x: float,
    y: float,
    index: int,
) -> PDFWord:
    return PDFWord(
        text=text,
        x0=center_x - 1,
        y0=y,
        x1=center_x + 1,
        y1=y + 1,
        block=0,
        line=0,
        word=index,
    )


def row(
    index: int,
    y: float,
    tokens: list[tuple[str, float]],
) -> LayoutRow:
    return LayoutRow(
        index=index,
        y=y,
        words=[word(text, center_x, y, i) for i, (text, center_x) in enumerate(tokens)],
    )


def test_normalize_owner_net_value_moves_bare_trn_owner_volume() -> None:
    parser = extractor()
    record = parsed_row("TRN", owner_volume="(15.79)")

    parser._normalize_owner_net_value(record)

    assert record.get(OWNER_VOLUME) is None
    assert record.get(OWNER_NET_VALUE) == "(15.79)"


def test_interest_qualified_trn_is_not_continuation() -> None:
    parser = extractor()
    record = parsed_row("WI TRN", owner_net_value="0.02")

    assert parser._is_continuation(record) is False


def test_bare_trn_is_continuation() -> None:
    parser = extractor()
    record = parsed_row("TRN", owner_net_value="(15.79)")

    assert parser._is_continuation(record) is True


def test_bare_gat_is_continuation() -> None:
    parser = extractor()
    record = parsed_row("GAT", owner_volume="0.01")

    parser._normalize_owner_net_value(record)

    assert record.get(OWNER_VOLUME) is None
    assert record.get(OWNER_NET_VALUE) == "0.01"
    assert parser._is_continuation(record) is True


def test_merge_into_previous_adds_owner_net_value() -> None:
    parser = extractor()
    previous = parsed_row("WI SEV", owner_net_value="304.18")
    continuation = parsed_row("TRN", owner_net_value="(15.79)")

    parser._merge_into_previous(previous, continuation)

    assert parse_decimal(previous.get(OWNER_NET_VALUE)) == Decimal("288.39")


def test_merge_into_previous_allows_mis_base_row() -> None:
    parser = extractor()
    previous = parsed_row("WI MIS", owner_net_value="0.10")
    continuation = parsed_row("TRN", owner_net_value="(0.08)")

    parser._merge_into_previous(previous, continuation)

    assert parse_decimal(previous.get(OWNER_NET_VALUE)) == Decimal("0.02")


def test_merge_into_previous_rejects_unrelated_previous() -> None:
    parser = extractor()
    previous = parsed_row("WI TRN", owner_net_value="0.02")
    continuation = parsed_row("TRN", owner_net_value="(15.79)")

    with pytest.raises(ValueError, match="previous SEV or MIS"):
        parser._merge_into_previous(previous, continuation)


def test_extract_suppresses_continuation_rows() -> None:
    product_block = DocumentBlock(
        type=BlockType.PRODUCT,
        start_row=0,
        end_row=2,
        metadata={"product": "OIL"},
        rows=[
            row(0, 10, [("OIL", 40)]),
            row(
                1,
                20,
                [
                    ("Dec", 30),
                    ("21", 50),
                    ("WI", 90),
                    ("SEV", 130),
                    ("0.15691470", 203.8),
                    ("0.00", 516.8),
                    ("304.18", 758.4),
                ],
            ),
            row(
                2,
                30,
                [
                    ("Dec", 30),
                    ("21", 50),
                    ("TRN", 138.5),
                    ("0.15691470", 203.8),
                    ("0.00", 516.8),
                    ("(15.79)", 711.8),
                ],
            ),
        ],
    )

    rows = RevenueLineExtractor(product_block).extract()

    assert len(rows) == 1
    assert rows[0].get(LINE_TYPE) == "WI SEV"
    assert parse_decimal(rows[0].get(OWNER_NET_VALUE)) == Decimal("288.39")
