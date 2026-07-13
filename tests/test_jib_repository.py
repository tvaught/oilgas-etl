from pathlib import Path

import pytest

from oilgas.database import Database
from oilgas.extractors.pdf import PDFExtractor
from oilgas.parsers.jib import JIBParser
from oilgas.repositories.jib import JIBRepository

HIGHMARK_JIB = Path("data/raw/highmark/jib/2026_06_15 Highmark.pdf")


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
