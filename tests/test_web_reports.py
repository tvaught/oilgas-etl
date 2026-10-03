from datetime import date
from decimal import Decimal

import pytest

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


def test_owner_revenue_derived_gross_and_deductions_reconcile_to_payable_net(tmp_path) -> None:
    database_path = tmp_path / "oilgas.duckdb"
    pdf = tmp_path / "statement.pdf"
    pdf.write_bytes(b"owner revenue")
    database = Database(database_path)
    database.initialize()
    try:
        statement = RevenueStatement(
            operator="Test Operator",
            owner_number="OWNER-1",
            check_number="CHECK-1",
            check_date=date(2026, 7, 1),
            check_amount=Decimal("130.00"),
            properties=[
                RevenueProperty(
                    property_code="P-1",
                    property_name="Test Well",
                    county="Test",
                    state="TX",
                    products=[
                        RevenueProduct(
                            product="OIL",
                            lines=[
                                RevenueLine(
                                    line_type="WI SEV",
                                    revenue_type="WI SEV",
                                    production_period=date(2026, 6, 1),
                                    owner_gross_value=Decimal("100.00"),
                                    owner_deductions=Decimal("-10.00"),
                                    owner_net_value=Decimal("90.00"),
                                ),
                                RevenueLine(
                                    line_type="WORKING INTEREST",
                                    revenue_type="WORKING INTEREST",
                                    production_period=date(2026, 6, 1),
                                    owner_net_value=Decimal("50.00"),
                                ),
                                RevenueLine(
                                    line_type="TRANSPORTATION",
                                    revenue_type="TRANSPORTATION",
                                    production_period=date(2026, 6, 1),
                                    owner_net_value=Decimal("-10.00"),
                                ),
                                RevenueLine(
                                    line_type="TRN",
                                    revenue_type="TRN",
                                    production_period=date(2026, 6, 1),
                                    owner_deductions=Decimal("-3.00"),
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        assert RevenueRepository(database.connection).insert(pdf, statement)
    finally:
        database.close()

    row = ReportRepository(database_path).owner_revenue_history(ReportFilters()).iloc[0]

    assert row["owner_gross_value"] == Decimal("150.00")
    assert row["owner_deductions"] == Decimal("-20.00")
    assert row["owner_net_value"] == Decimal("130.00")
    assert row["owner_gross_value"] + row["owner_deductions"] == row["owner_net_value"]
    assert row["detail_only_owner_deductions"] == Decimal("-3.00")


def test_cashflow_excludes_jib_netting_property_but_owner_revenue_preserves_it(tmp_path) -> None:
    database_path = tmp_path / "oilgas.duckdb"
    pdf = tmp_path / "statement.pdf"
    pdf.write_bytes(b"netting well")
    database = Database(database_path)
    database.initialize()
    try:
        statement = RevenueStatement(
            operator="Test Operator",
            owner_number="OWNER-1",
            check_number="CHECK-1",
            check_date=date(2026, 7, 1),
            check_amount=Decimal("70.00"),
            properties=[
                RevenueProperty(
                    property_code="P-1",
                    property_name="Producing Well",
                    county="Test",
                    state="TX",
                    products=[
                        RevenueProduct(
                            product="OIL",
                            lines=[
                                RevenueLine(
                                    line_type="WORKING INTEREST",
                                    revenue_type="WORKING INTEREST",
                                    production_period=date(2026, 6, 1),
                                    owner_net_value=Decimal("100.00"),
                                )
                            ],
                        )
                    ],
                ),
                RevenueProperty(
                    property_code="10*JIBNET",
                    property_name="JIB NETTING WELL",
                    county="Test",
                    state="TX",
                    products=[
                        RevenueProduct(
                            product="JOINT INTEREST BILLING",
                            lines=[
                                RevenueLine(
                                    line_type="WORKING INTEREST",
                                    revenue_type="WORKING INTEREST",
                                    production_period=date(2026, 6, 1),
                                    owner_net_value=Decimal("-30.00"),
                                )
                            ],
                        )
                    ],
                ),
            ],
        )
        assert RevenueRepository(database.connection).insert(pdf, statement)
    finally:
        database.close()

    repository = ReportRepository(database_path)
    cashflow = repository.net_cashflow(ReportFilters())
    owner_revenue = repository.owner_revenue_history(ReportFilters())

    assert cashflow.iloc[0]["revenue_net"] == Decimal("100.00")
    assert cashflow.iloc[0]["net_cashflow"] == Decimal("100.00")
    assert owner_revenue["property_code"].tolist() == ["10*JIBNET", "P-1"]
    assert owner_revenue["owner_net_value"].sum() == Decimal("70.00")


def test_property_list_uses_latest_valid_ownership_decimals_and_flags_changes(tmp_path) -> None:
    database_path = tmp_path / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    try:
        repository = RevenueRepository(database.connection)
        for index, (check_date, owner_interest, distribution_interest) in enumerate(
            [
                (date(2026, 1, 15), "0.12500000", "0.10000000"),
                (date(2026, 2, 15), "0.15000000", "0.12000000"),
            ],
            start=1,
        ):
            pdf = tmp_path / f"ownership-{index}.pdf"
            pdf.write_bytes(str(index).encode())
            statement = RevenueStatement(
                operator="Test Operator",
                owner_number="OWNER-1",
                check_number=f"OWNERSHIP-{index}",
                check_date=check_date,
                check_amount=Decimal("100.00"),
                properties=[
                    RevenueProperty(
                        property_code="P-1",
                        property_name="Test Well",
                        county="Test",
                        state="TX",
                        products=[
                            RevenueProduct(
                                product="OIL",
                                lines=[
                                    RevenueLine(
                                        line_type="WORKING INTEREST",
                                        revenue_type="WORKING INTEREST",
                                        production_period=check_date.replace(day=1),
                                        owner_interest=Decimal(owner_interest),
                                        distribution_interest=Decimal(distribution_interest),
                                        owner_net_value=Decimal("100.00"),
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
            assert repository.insert(pdf, statement)
    finally:
        database.close()

    data = ReportRepository(database_path).property_list(ReportFilters())

    assert len(data) == 1
    row = data.iloc[0]
    assert row["owner_interest"] == pytest.approx(0.15)
    assert row["distribution_interest"] == pytest.approx(0.12)
    assert row["first_observation_date"].date() == date(2026, 1, 1)
    assert row["latest_observation_date"].date() == date(2026, 2, 1)
    assert row["ownership_decimal_count"] == 2
    assert row["ownership_status"] == "changed"


def test_monthly_revenue_reconciliation_includes_costs_without_double_counting_details(
    tmp_path,
) -> None:
    database_path = tmp_path / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    try:
        repository = RevenueRepository(database.connection)
        primary_lines = [
            ("WORKING INTEREST", "120.00", None),
            ("PRODUCTION TAX", "-10.00", None),
            ("TRANSPORTATION", "-5.00", None),
            ("CORRECTION", "-2.00", None),
            ("TRN", None, "-3.00"),
        ]
        for index, (line_type, net, deductions) in enumerate(primary_lines, start=1):
            pdf = tmp_path / f"primary-{index}.pdf"
            pdf.write_bytes(line_type.encode())
            statement = RevenueStatement(
                operator="Test Operator",
                owner_number="OWNER-1",
                check_number=f"PRIMARY-{index}",
                check_date=date(2026, 7, 1),
                check_amount=Decimal(net or "0.00"),
                properties=[
                    RevenueProperty(
                        property_code=f"P-{index}",
                        property_name=f"Test Well {index}",
                        county="Test",
                        state="TX",
                        products=[
                            RevenueProduct(
                                product="OIL",
                                lines=[
                                    RevenueLine(
                                        line_type=line_type,
                                        revenue_type=line_type,
                                        production_period=date(2026, 6, 1),
                                        owner_deductions=(
                                            Decimal(deductions) if deductions is not None else None
                                        ),
                                        owner_net_value=Decimal(net) if net is not None else None,
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
            assert repository.insert(pdf, statement)
    finally:
        database.close()

    data = ReportRepository(database_path).revenue_reconciliation(ReportFilters())

    assert len(data) == 1
    row = data.iloc[0]
    assert row["statement_count"] == 5
    assert row["check_amount"] == Decimal("103.00")
    assert row["income_net"] == Decimal("120.00")
    assert row["tax_net"] == Decimal("-10.00")
    assert row["deduction_net"] == Decimal("-5.00")
    assert row["adjustment_net"] == Decimal("-2.00")
    assert row["reported_net"] == Decimal("103.00")
    assert row["check_variance"] == Decimal("0.00")
    assert row["detail_only_deductions"] == Decimal("-3.00")
    assert row["detail_only_deduction_line_count"] == 1
    assert row["reconciliation_status"] == "reconciled"
