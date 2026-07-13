from datetime import date
from decimal import Decimal

from oilgas.database import Database
from oilgas.models.revenue import RevenueStatement
from oilgas.repositories.revenue import RevenueRepository


def statement() -> RevenueStatement:
    return RevenueStatement(
        operator="XTO Energy",
        owner_number="OWNER-1",
        check_number="CHECK-1",
        check_date=date(2022, 1, 29),
        check_amount=Decimal("123.45"),
        properties=[],
    )


def test_duplicate_source_file_is_skipped(tmp_path) -> None:
    pdf = tmp_path / "statement.pdf"
    pdf.write_bytes(b"same statement bytes")

    db = Database(tmp_path / "oilgas.duckdb")
    db.initialize()

    try:
        repo = RevenueRepository(db.connection)

        assert repo.is_imported(pdf) is False
        assert repo.insert(pdf, statement()) is True
        assert repo.is_imported(pdf) is True
        assert repo.insert(pdf, statement()) is False

        source_file_count = db.scalar("SELECT count(*) FROM source_file")
        statement_count = db.scalar("SELECT count(*) FROM revenue_statement")

        assert source_file_count == 1
        assert statement_count == 1

    finally:
        db.close()


def test_same_content_different_filename_is_skipped(tmp_path) -> None:
    pdf1 = tmp_path / "statement-a.pdf"
    pdf2 = tmp_path / "statement-b.pdf"
    pdf1.write_bytes(b"same statement bytes")
    pdf2.write_bytes(b"same statement bytes")

    db = Database(tmp_path / "oilgas.duckdb")
    db.initialize()

    try:
        repo = RevenueRepository(db.connection)

        assert repo.insert(pdf1, statement()) is True
        assert repo.insert(pdf2, statement()) is False

        source_file_count = db.scalar("SELECT count(*) FROM source_file")
        statement_count = db.scalar("SELECT count(*) FROM revenue_statement")

        assert source_file_count == 1
        assert statement_count == 1

    finally:
        db.close()
