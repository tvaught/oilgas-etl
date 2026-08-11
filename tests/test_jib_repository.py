from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from oilgas.database import Database
from oilgas.extractors.pdf import PDFExtractor
from oilgas.models.jib import JIBCostCenterSummary, JIBInvoice, JIBLine
from oilgas.parsers.jib import JIBParser
from oilgas.repositories.jib import JIBRepository

HIGHMARK_JIB = Path("data/raw/highmark/jib/2026_06_15 Highmark.pdf")


def invoice() -> JIBInvoice:
    return JIBInvoice(
        operator="HIGHMARK ENERGY OPERATING LLC",
        invoice_number="INV-1",
        invoice_date=date(2026, 6, 15),
        accounting_period=date(2026, 6, 1),
        invoice_total=Decimal("100.00"),
        cost_centers=[
            JIBCostCenterSummary(
                cost_center_code="CC-1", invoiced_amount=Decimal("100.00"), display_order=1
            )
        ],
        lines=[
            JIBLine(
                cost_center_code="CC-1",
                op_account="1000",
                description="Test expense",
                activity_period=date(2026, 6, 1),
                partner_percent=Decimal("1"),
                gross_amount=Decimal("100.00"),
                invoiced_amount=Decimal("100.00"),
                display_order=1,
            )
        ],
    )


def test_duplicate_invoice_with_new_source_does_not_create_an_orphan_source_file(tmp_path) -> None:
    original_pdf = tmp_path / "invoice-original.pdf"
    replacement_pdf = tmp_path / "invoice-replacement.pdf"
    original_pdf.write_bytes(b"original invoice bytes")
    replacement_pdf.write_bytes(b"replacement invoice bytes")
    db = Database(tmp_path / "oilgas.duckdb")
    db.initialize()
    try:
        repo = JIBRepository(db.connection)
        assert repo.insert(original_pdf, invoice())
        assert not repo.insert(replacement_pdf, invoice())
        assert db.scalar("SELECT count(*) FROM source_file") == 1
        assert db.scalar("SELECT count(*) FROM jib_invoice") == 1
    finally:
        db.close()


@pytest.mark.skipif(
    not HIGHMARK_JIB.exists(),
    reason="Highmark JIB PDF fixture is not available.",
)
def test_jib_repository_inserts_invoice_lines_and_skips_duplicates(tmp_path) -> None:
    db = Database(tmp_path / "oilgas.duckdb")
    db.initialize()

    try:
        document = PDFExtractor.load(HIGHMARK_JIB)
        invoice = JIBParser().parse(document, HIGHMARK_JIB.name)
        assert invoice is not None

        repo = JIBRepository(db.connection)

        assert repo.insert(HIGHMARK_JIB, invoice) is True
        assert repo.insert(HIGHMARK_JIB, invoice) is False

        row = db.execute(
            """
            SELECT
                ji.invoice_total,
                sum(jl.invoiced_amount) AS line_total,
                count(*) AS line_count
            FROM jib_invoice ji
            JOIN jib_line jl
                ON jl.invoice_id = ji.invoice_id
            WHERE ji.invoice_number = '10*05-AR-3084'
            GROUP BY
                ji.invoice_id,
                ji.invoice_total
            """
        ).fetchone()

        assert row is not None
        assert row[0] == row[1]
        assert row[2] > 300
        assert db.scalar("SELECT count(*) FROM jib_invoice") == 1

    finally:
        db.close()
