from datetime import date

from oilgas.database import Database
from oilgas.web.filters import ReportFilters
from oilgas.web.reports import ReportRepository


def test_product_filter_excludes_unfiltered_jib_expenses(tmp_path) -> None:
    database_path = tmp_path / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    try:
        database.execute(
            "INSERT INTO operator (operator_id, operator_name) VALUES (?, ?)",
            ("00000000-0000-0000-0000-000000000001", "Test Operator"),
        )
        database.execute(
            """
            INSERT INTO source_file (
                source_file_id, filename, filepath, sha256, filesize, document_type
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000002",
                "revenue.pdf",
                "/tmp/revenue.pdf",
                "a",
                1,
                "revenue",
            ),
        )
        database.execute(
            """
            INSERT INTO source_file (
                source_file_id, filename, filepath, sha256, filesize, document_type
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("00000000-0000-0000-0000-000000000003", "jib.pdf", "/tmp/jib.pdf", "b", 1, "jib"),
        )
        database.execute(
            """
            INSERT INTO property (property_id, operator_id, property_code, property_name)
            VALUES (?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000004",
                "00000000-0000-0000-0000-000000000001",
                "P-1",
                "Test Well",
            ),
        )
        database.execute(
            """
            INSERT INTO revenue_statement (
                statement_id, source_file_id, operator_id, check_number, check_date, check_amount
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000005",
                "00000000-0000-0000-0000-000000000002",
                "00000000-0000-0000-0000-000000000001",
                "C-1",
                date(2026, 6, 1),
                150,
            ),
        )
        database.execute(
            """
            INSERT INTO revenue_product (
                product_id, statement_id, property_id, product, display_order
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000006",
                "00000000-0000-0000-0000-000000000005",
                "00000000-0000-0000-0000-000000000004",
                "OIL",
                1,
            ),
        )
        database.execute(
            """
            INSERT INTO revenue_line (
                line_id, statement_id, property_id, product_id, line_type, revenue_type,
                production_period, owner_net_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000007",
                "00000000-0000-0000-0000-000000000005",
                "00000000-0000-0000-0000-000000000004",
                "00000000-0000-0000-0000-000000000006",
                "WI",
                "OIL",
                date(2026, 6, 1),
                150,
            ),
        )
        database.execute(
            """
            INSERT INTO jib_invoice (
                invoice_id, source_file_id, operator_id, invoice_number, invoice_date,
                accounting_period, invoice_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000008",
                "00000000-0000-0000-0000-000000000003",
                "00000000-0000-0000-0000-000000000001",
                "I-1",
                date(2026, 6, 1),
                date(2026, 6, 1),
                100,
            ),
        )
        database.execute(
            """
            INSERT INTO jib_cost_center (
                cost_center_id, operator_id, cost_center_code, cost_center_name
            ) VALUES (?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000009",
                "00000000-0000-0000-0000-000000000001",
                "CC-1",
                "Test Cost Center",
            ),
        )
        database.execute(
            """
            INSERT INTO jib_line (
                line_id, invoice_id, cost_center_id, op_account, description, activity_period,
                partner_percent, gross_amount, invoiced_amount, display_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "00000000-0000-0000-0000-000000000010",
                "00000000-0000-0000-0000-000000000008",
                "00000000-0000-0000-0000-000000000009",
                "1000",
                "Test expense",
                date(2026, 6, 1),
                1,
                100,
                100,
                1,
            ),
        )
    finally:
        database.close()

    details = ReportRepository(database_path).cashflow_details(ReportFilters(products=("OIL",)))

    assert details["record_type"].tolist() == ["revenue"]
    assert details.iloc[0]["revenue_net"] == 150
    assert details.iloc[0]["jib_expense"] == 0
