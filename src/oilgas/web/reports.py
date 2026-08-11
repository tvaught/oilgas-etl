from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from oilgas.web.filters import ReportFilters


@dataclass(frozen=True)
class FilterOptions:
    months: list[tuple[str, str]]
    operators: list[str]
    properties: list[str]
    products: list[str]
    cost_centers: list[str]


class ReportRepository:
    """SQL-first, read-only reporting queries against the application DuckDB."""

    def __init__(self, database_path: Path):
        if not database_path.is_file():
            raise FileNotFoundError(f"Database does not exist: {database_path}")
        self.database_path = database_path

    def dataframe(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> pd.DataFrame:
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            return connection.execute(sql, params).fetchdf()

    def filter_options(self) -> FilterOptions:
        return FilterOptions(
            months=self._months(),
            operators=self._strings("SELECT operator_name FROM operator ORDER BY operator_name"),
            properties=self._strings(
                "SELECT DISTINCT property_name FROM property ORDER BY property_name"
            ),
            products=self._strings("SELECT DISTINCT product FROM revenue_product ORDER BY product"),
            cost_centers=self._strings(
                """
                SELECT DISTINCT cost_center_name
                FROM jib_cost_center
                WHERE cost_center_name IS NOT NULL
                  AND cost_center_name <> ''
                ORDER BY cost_center_name
                """
            ),
        )

    def _months(self) -> list[tuple[str, str]]:
        months = self.dataframe(
            """
            SELECT DISTINCT report_month
            FROM (
                SELECT date_trunc('month', production_period)::DATE AS report_month
                FROM revenue_line
                UNION
                SELECT date_trunc('month', check_date)::DATE FROM revenue_statement
                UNION
                SELECT date_trunc('month', accounting_period)::DATE FROM jib_invoice
                UNION
                SELECT date_trunc('month', invoice_date)::DATE FROM jib_invoice
            )
            WHERE report_month IS NOT NULL
            ORDER BY report_month DESC
            """
        )
        return [
            (month.strftime("%Y-%m"), month.strftime("%b %Y"))
            for month in pd.to_datetime(months["report_month"])
        ]

    def overview(self, filters: ReportFilters) -> pd.DataFrame:
        return self.cashflow_rollup(filters)

    def cashflow_rollup(self, filters: ReportFilters) -> pd.DataFrame:
        """Roll monthly cashflow into the selected calendar reporting period."""
        monthly = self.net_cashflow(filters)
        if monthly.empty or filters.rollup == "monthly":
            return monthly

        rolled = monthly.copy()
        dates = pd.to_datetime(rolled["report_month"])
        if filters.rollup == "quarterly":
            rolled["report_month"] = dates.dt.to_period("Q").dt.start_time
            rolled["report_period"] = dates.dt.to_period("Q").astype(str)
        elif filters.rollup == "annual":
            rolled["report_month"] = dates.dt.to_period("Y").dt.start_time
            rolled["report_period"] = dates.dt.strftime("%Y")
        else:
            return monthly

        grouped = rolled.groupby(["report_month", "report_period"], as_index=False)[
            ["revenue_net", "jib_expense", "net_cashflow"]
        ].sum()
        return grouped.sort_values("report_month", ascending=False)

    def net_cashflow(self, filters: ReportFilters) -> pd.DataFrame:
        """Monthly cashflow roll-up with no property/cost-center allocation."""
        details = self.cashflow_details(filters)
        if details.empty:
            return pd.DataFrame(
                columns=["report_month", "revenue_net", "jib_expense", "net_cashflow"]
            )
        monthly = details.groupby("report_month", as_index=False)[
            ["revenue_net", "jib_expense"]
        ].sum()
        monthly["net_cashflow"] = monthly["revenue_net"] - monthly["jib_expense"]
        return monthly.sort_values("report_month", ascending=False)

    def cashflow_details(self, filters: ReportFilters) -> pd.DataFrame:
        """Independent revenue-property and JIB-cost-center roll-ups for drilldown."""
        revenue_date = self._revenue_date(filters.revenue_date_basis)
        jib_date = self._jib_date(filters.jib_date_basis)
        revenue_where, revenue_params = self._revenue_filters(filters, revenue_date)
        jib_where, jib_params = self._jib_filters(filters, jib_date)
        # The revenue and JIB branches are independent. A filter for one branch
        # suppresses unfiltered rows from the other; selecting both keeps both.
        revenue_select = "" if not filters.cost_centers or filters.properties else "AND FALSE"
        jib_select = "" if not filters.properties or filters.cost_centers else "AND FALSE"
        sql = f"""
            SELECT
                date_trunc('month', {revenue_date})::DATE AS report_month,
                'revenue' AS record_type,
                o.operator_name,
                p.property_name,
                p.property_code,
                NULL::TEXT AS cost_center_name,
                NULL::TEXT AS cost_center_code,
                SUM(rl.owner_net_value) AS revenue_net,
                0::DECIMAL(18, 2) AS jib_expense
            FROM revenue_line AS rl
            JOIN revenue_statement AS rs ON rs.statement_id = rl.statement_id
            JOIN operator AS o ON o.operator_id = rs.operator_id
            JOIN property AS p ON p.property_id = rl.property_id
            JOIN revenue_product AS rp ON rp.product_id = rl.product_id
            WHERE {revenue_where}
              {revenue_select}
            GROUP BY 1, 2, 3, 4, 5

            UNION ALL

            SELECT
                date_trunc('month', {jib_date})::DATE AS report_month,
                'jib expense' AS record_type,
                o.operator_name,
                NULL::TEXT AS property_name,
                NULL::TEXT AS property_code,
                jcc.cost_center_name,
                jcc.cost_center_code,
                0::DECIMAL(18, 2) AS revenue_net,
                SUM(jl.invoiced_amount) AS jib_expense
            FROM jib_line AS jl
            JOIN jib_invoice AS ji ON ji.invoice_id = jl.invoice_id
            JOIN operator AS o ON o.operator_id = ji.operator_id
            JOIN jib_cost_center AS jcc ON jcc.cost_center_id = jl.cost_center_id
            WHERE {jib_where}
              {jib_select}
            GROUP BY 1, 2, 3, 4, 5, 6, 7
            ORDER BY
                report_month DESC,
                operator_name,
                record_type,
                property_name,
                cost_center_code
        """
        details = self.dataframe(sql, [*revenue_params, *jib_params])
        details["net_cashflow"] = details["revenue_net"] - details["jib_expense"]
        return details

    def production_history(self, filters: ReportFilters) -> pd.DataFrame:
        date_column = self._revenue_date(filters.revenue_date_basis)
        where, params = self._revenue_filters(filters, date_column)
        if filters.adjustment_basis == "exclude":
            where += " AND rl.property_volume >= 0"
        sql = f"""
            SELECT
                date_trunc('month', {date_column})::DATE AS report_month,
                o.operator_name,
                p.property_name,
                rp.product,
                SUM(rl.property_volume) AS property_volume,
                SUM(rl.property_gross_value) AS property_gross_value,
                SUM(rl.owner_volume) AS owner_volume,
                SUM(rl.owner_net_value) AS owner_net_value,
                AVG(rl.distribution_interest) AS distribution_interest
            FROM revenue_line AS rl
            JOIN revenue_statement AS rs ON rs.statement_id = rl.statement_id
            JOIN operator AS o ON o.operator_id = rs.operator_id
            JOIN property AS p ON p.property_id = rl.property_id
            JOIN revenue_product AS rp ON rp.product_id = rl.product_id
            WHERE {where}
            GROUP BY 1, 2, 3, 4
            ORDER BY 1 DESC, 2, 3, 4
        """
        return self.dataframe(sql, params)

    def price_history(self, filters: ReportFilters) -> pd.DataFrame:
        date_column = self._revenue_date(filters.revenue_date_basis)
        where, params = self._revenue_filters(filters, date_column)
        sql = f"""
            SELECT
                date_trunc('month', {date_column})::DATE AS report_month,
                o.operator_name,
                p.property_name,
                rp.product,
                AVG(rl.unit_price) AS average_unit_price,
                COUNT(rl.unit_price) AS priced_line_count
            FROM revenue_line AS rl
            JOIN revenue_statement AS rs ON rs.statement_id = rl.statement_id
            JOIN operator AS o ON o.operator_id = rs.operator_id
            JOIN property AS p ON p.property_id = rl.property_id
            JOIN revenue_product AS rp ON rp.product_id = rl.product_id
            WHERE {where}
              AND rl.unit_price > 0
              AND rl.property_volume > 0
            GROUP BY 1, 2, 3, 4
            ORDER BY 1 DESC, 2, 3, 4
        """
        return self.dataframe(sql, params)

    def revenue_lines(self, filters: ReportFilters) -> pd.DataFrame:
        date_column = self._revenue_date(filters.revenue_date_basis)
        where, params = self._revenue_filters(filters, date_column)
        sql = f"""
            SELECT
                rs.check_number, rs.check_date, rs.accounting_period,
                o.operator_name, p.property_name, p.property_code, rp.product,
                rl.production_period, rl.line_type, rl.revenue_type, rl.tax_deduct_code,
                rl.property_volume, rl.unit_price, rl.property_gross_value,
                rl.property_deductions, rl.property_net_value, rl.distribution_interest,
                rl.owner_volume, rl.owner_gross_value, rl.owner_deductions, rl.owner_net_value,
                sf.filename, sf.source_file_id
            FROM revenue_line AS rl
            JOIN revenue_statement AS rs ON rs.statement_id = rl.statement_id
            JOIN operator AS o ON o.operator_id = rs.operator_id
            JOIN property AS p ON p.property_id = rl.property_id
            JOIN revenue_product AS rp ON rp.product_id = rl.product_id
            JOIN source_file AS sf ON sf.source_file_id = rs.source_file_id
            WHERE {where}
            ORDER BY rs.check_date DESC, rs.check_number DESC, p.property_name, rp.product
        """
        return self.dataframe(sql, params)

    def jib_lines(self, filters: ReportFilters) -> pd.DataFrame:
        date_column = self._jib_date(filters.jib_date_basis)
        where, params = self._jib_filters(filters, date_column)
        sql = f"""
            SELECT
                ji.invoice_number, ji.invoice_date, ji.accounting_period,
                o.operator_name, jcc.cost_center_code, jcc.cost_center_name,
                jl.afe, jl.cost_class, jl.account_group, jl.op_account, jl.minor_account,
                jl.description, v.vendor_name, jl.vendor_invoice, jl.activity_period,
                jl.partner_percent, jl.gross_amount, jl.invoiced_amount,
                sf.filename, sf.source_file_id
            FROM jib_line AS jl
            JOIN jib_invoice AS ji ON ji.invoice_id = jl.invoice_id
            JOIN operator AS o ON o.operator_id = ji.operator_id
            JOIN jib_cost_center AS jcc ON jcc.cost_center_id = jl.cost_center_id
            LEFT JOIN vendor AS v ON v.vendor_id = jl.vendor_id
            JOIN source_file AS sf ON sf.source_file_id = ji.source_file_id
            WHERE {where}
            ORDER BY
                ji.invoice_date DESC,
                ji.invoice_number DESC,
                jcc.cost_center_code,
                jl.display_order
        """
        return self.dataframe(sql, params)

    def source_path(self, source_file_id: str) -> Path | None:
        rows = self.dataframe(
            "SELECT filepath FROM source_file WHERE source_file_id = ?", [source_file_id]
        )
        if rows.empty or not rows.iloc[0, 0]:
            return None
        return Path(rows.iloc[0, 0])

    def _strings(self, sql: str) -> list[str]:
        return self.dataframe(sql).iloc[:, 0].dropna().tolist()

    @staticmethod
    def _revenue_date(basis: str) -> str:
        return "rs.check_date" if basis == "check" else "rl.production_period"

    @staticmethod
    def _jib_date(basis: str) -> str:
        return "ji.invoice_date" if basis == "invoice" else "ji.accounting_period"

    def _revenue_filters(self, filters: ReportFilters, date_column: str) -> tuple[str, list[Any]]:
        clauses = [f"{date_column} IS NOT NULL"]
        params: list[Any] = []
        self._append_in(clauses, params, "o.operator_name", filters.operators)
        self._append_in(clauses, params, "p.property_name", filters.properties)
        self._append_in(clauses, params, "rp.product", filters.products)
        self._append_dates(clauses, params, date_column, filters)
        return " AND ".join(clauses), params

    def _jib_filters(self, filters: ReportFilters, date_column: str) -> tuple[str, list[Any]]:
        clauses = [f"{date_column} IS NOT NULL"]
        params: list[Any] = []
        self._append_in(clauses, params, "o.operator_name", filters.operators)
        self._append_in(clauses, params, "jcc.cost_center_name", filters.cost_centers)
        self._append_dates(clauses, params, date_column, filters)
        return " AND ".join(clauses), params

    @staticmethod
    def _append_in(
        clauses: list[str], params: list[Any], column: str, values: tuple[str, ...]
    ) -> None:
        if values:
            clauses.append(f"{column} IN ({', '.join('?' for _ in values)})")
            params.extend(values)

    @staticmethod
    def _append_dates(
        clauses: list[str], params: list[Any], column: str, filters: ReportFilters
    ) -> None:
        if filters.start_month:
            clauses.append(f"{column} >= ?")
            params.append(filters.start_month)
        if filters.end_month:
            clauses.append(f"{column} < (? + INTERVAL '1 month')")
            params.append(filters.end_month)
