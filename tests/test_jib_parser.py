from decimal import Decimal
from pathlib import Path

import pytest

from oilgas.extractors.pdf import PDFExtractor
from oilgas.parsers.jib import JIBParser
from oilgas.util.operators import canonical_operator_name

HIGHMARK_JIB = Path("data/raw/highmark/jib/2026_06_15 Highmark.pdf")
FINLEY_STATEMENT_ONLY = Path("data/raw/finley/jib/2022_10_18 Finley.pdf")
SPLIT_HEADER_HIGHMARK_JIB = Path("data/raw/highmark/jib/2025_07_15 Highmark.pdf")


@pytest.mark.skipif(
    not HIGHMARK_JIB.exists(),
    reason="Highmark JIB PDF fixture is not available.",
)
def test_parse_highmark_jib_invoice_package() -> None:
    document = PDFExtractor.load(HIGHMARK_JIB)
    invoice = JIBParser().parse(document, HIGHMARK_JIB.name)

    assert invoice is not None
    assert invoice.operator == "HIGHMARK ENERGY OPERATING LLC"
    assert invoice.owner_number == "16556"
    assert invoice.invoice_number == "10*05-AR-3084"
    assert invoice.invoice_total == Decimal("3385.40")
    assert invoice.summary_total == invoice.invoice_total
    assert invoice.line_total == invoice.invoice_total
    assert len(invoice.cost_centers) == 7
    assert len(invoice.lines) > 300

    first_line = invoice.lines[0]
    assert first_line.cost_center_code == "10*18634"
    assert first_line.afe == "10*26022477 TUBING REPAIR"
    assert first_line.vendor_name == "JOE R. MAY OILFIELD PIPE & SUPPLY, LTD."
    assert first_line.vendor_invoice == "05-OI-693"


def test_canonical_operator_name_removes_highmark_comma_variant() -> None:
    assert canonical_operator_name("HIGHMARK ENERGY OPERATING, LLC") == (
        "HIGHMARK ENERGY OPERATING LLC"
    )


def test_parse_operator_from_accounting_row() -> None:
    assert JIBParser()._parse_operator("16556 HIGHMARK ENERGY OPERATING LLC") == (
        "HIGHMARK ENERGY OPERATING LLC"
    )


@pytest.mark.skipif(
    not SPLIT_HEADER_HIGHMARK_JIB.exists(),
    reason="Highmark JIB PDF fixture is not available.",
)
def test_parse_highmark_jib_with_split_owner_operator_header() -> None:
    document = PDFExtractor.load(SPLIT_HEADER_HIGHMARK_JIB)
    invoice = JIBParser().parse(document, SPLIT_HEADER_HIGHMARK_JIB.name)

    assert invoice is not None
    assert invoice.operator == "HIGHMARK ENERGY OPERATING LLC"
    assert invoice.invoice_number == "10*06-AR-2072"


@pytest.mark.skipif(
    not FINLEY_STATEMENT_ONLY.exists(),
    reason="Finley statement-only JIB fixture is not available.",
)
def test_statement_of_account_without_invoice_is_skipped() -> None:
    document = PDFExtractor.load(FINLEY_STATEMENT_ONLY)

    assert JIBParser().parse(document, FINLEY_STATEMENT_ONLY.name) is None
