from decimal import Decimal
from pathlib import Path

import pytest

from oilgas.extractors.pdf import PDFExtractor
from oilgas.parsers.jib import JIBParser

HIGHMARK_JIB = Path("data/raw/highmark/jib/2026_06_15 Highmark.pdf")
FINLEY_STATEMENT_ONLY = Path("data/raw/finley/jib/2022_10_18 Finley.pdf")


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


@pytest.mark.skipif(
    not FINLEY_STATEMENT_ONLY.exists(),
    reason="Finley statement-only JIB fixture is not available.",
)
def test_statement_of_account_without_invoice_is_skipped() -> None:
    document = PDFExtractor.load(FINLEY_STATEMENT_ONLY)

    assert JIBParser().parse(document, FINLEY_STATEMENT_ONLY.name) is None
