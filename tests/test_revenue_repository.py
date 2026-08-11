from datetime import date
from decimal import Decimal

from oilgas.database import Database
from oilgas.models.revenue import RevenueProperty, RevenueStatement
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


def test_existing_property_metadata_is_retained_without_blocking_import(tmp_path) -> None:
    first_pdf = tmp_path / "statement-a.pdf"
    second_pdf = tmp_path / "statement-b.pdf"
    first_pdf.write_bytes(b"first statement")
    second_pdf.write_bytes(b"second statement")
    original_property = RevenueProperty(
        property_code="P-1",
        property_name="Original Well",
        county="Original County",
        state="TX",
        api_number="42-001-00001",
    )
    corrected_property = original_property.model_copy(
        update={
            "property_name": "Corrected Well",
            "county": "Corrected County",
            "state": "NM",
            "api_number": "30-001-00001",
        }
    )

    db = Database(tmp_path / "oilgas.duckdb")
    db.initialize()
    try:
        repo = RevenueRepository(db.connection)
        assert repo.insert(
            first_pdf, statement().model_copy(update={"properties": [original_property]})
        )
        assert repo.insert(
            second_pdf, statement().model_copy(update={"properties": [corrected_property]})
        )

        row = db.execute(
            """
            SELECT property_name, county, state, api_number
            FROM property
            WHERE property_code = 'P-1'
            """
        ).fetchone()
        assert row == ("Original Well", "Original County", "TX", "42-001-00001")
        assert db.scalar("SELECT count(*) FROM revenue_statement") == 2
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
