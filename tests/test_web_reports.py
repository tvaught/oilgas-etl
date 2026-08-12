from datetime import date
from decimal import Decimal

from oilgas.database import Database
from oilgas.models.revenue import RevenueLine, RevenueProduct, RevenueProperty, RevenueStatement
from oilgas.repositories.revenue import RevenueRepository
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


def test_owner_revenue_history_breaks_out_product_categories_and_properties(tmp_path) -> None:
    database_path = tmp_path / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    try:
        repository = RevenueRepository(database.connection)
        products = (
            ("GAS SALES", "Gas", "North Well", "P-1", "100.00", "-10.00", "90.00"),
            ("NATURAL GAS LIQUIDS", "NGL", "North Well", "P-1", "50.00", "-5.00", "45.00"),
            ("OIL", "Oil", "South Well", "P-2", "200.00", "-20.00", "180.00"),
        )
        for index, (product, _, property_name, property_code, gross, deductions, net) in enumerate(
            products, start=1
        ):
            pdf = tmp_path / f"statement-{index}.pdf"
            pdf.write_bytes(product.encode())
            line = RevenueLine(
                line_type="WI",
                revenue_type="SEV",
                production_period=date(2026, 6, 1),
                owner_gross_value=Decimal(gross),
                owner_deductions=Decimal(deductions),
                owner_net_value=Decimal(net),
            )
            statement = RevenueStatement(
                operator="Test Operator",
                owner_number="OWNER-1",
                check_number=f"CHECK-{index}",
                check_date=date(2026, 7, 1),
                check_amount=Decimal(net),
                properties=[
                    RevenueProperty(
                        property_code=property_code,
                        property_name=property_name,
                        county="Test",
                        state="TX",
                        products=[RevenueProduct(product=product, lines=[line])],
                    )
                ],
            )
            assert repository.insert(pdf, statement)
    finally:
        database.close()

    report = ReportRepository(database_path)
    data = report.owner_revenue_history(ReportFilters())

    assert data[
        [
            "product_category",
            "property_name",
            "owner_gross_value",
            "owner_deductions",
            "owner_net_value",
        ]
    ].values.tolist() == [
        ["Gas", "North Well", 100.0, -10.0, 90.0],
        ["NGL", "North Well", 50.0, -5.0, 45.0],
        ["Oil", "South Well", 200.0, -20.0, 180.0],
    ]
    assert report.owner_revenue_history(ReportFilters(products=("OIL",)))[
        "product_category"
    ].tolist() == ["Oil"]
