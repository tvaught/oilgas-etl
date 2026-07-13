from decimal import Decimal
from pathlib import Path

import pytest

from oilgas.database import Database
from oilgas.extractors.pdf import PDFExtractor
from oilgas.parsers.revenue import RevenueParser
from oilgas.repositories.revenue import RevenueRepository

HIGHMARK_STATEMENT = Path("data/raw/highmark/revenue/2026_06_24 Highmark.pdf")


@pytest.mark.skipif(
    not HIGHMARK_STATEMENT.exists(),
    reason="Highmark revenue PDF fixture is not available.",
)
def test_statement_check_amount_matches_sum_of_persisted_revenue_lines(tmp_path) -> None:
    db = Database(tmp_path / "oilgas.duckdb")
    db.initialize()

    try:
        document = PDFExtractor.load(HIGHMARK_STATEMENT)
        statement = RevenueParser().parse(
            document=document,
            source_file=HIGHMARK_STATEMENT.name,
        )

        repo = RevenueRepository(db.connection)
        assert repo.insert(HIGHMARK_STATEMENT, statement) is True

        row = db.execute(
            """
            SELECT
                rs.check_amount,
                sum(rl.owner_net_value) AS line_total
            FROM revenue_statement rs
            JOIN revenue_product rp
                ON rp.statement_id = rs.statement_id
            JOIN property p
                ON p.property_id = rp.property_id
            JOIN revenue_line rl
                ON rl.statement_id = rs.statement_id
                AND rl.product_id = rp.product_id
                AND rl.property_id = p.property_id
            WHERE rs.check_date = DATE '2026-06-22'
            GROUP BY
                rs.statement_id,
                rs.check_amount
            """
        ).fetchone()

        assert row is not None

        check_amount, line_total = row

        assert check_amount == Decimal("34.84")
        assert line_total == check_amount

    finally:
        db.close()
