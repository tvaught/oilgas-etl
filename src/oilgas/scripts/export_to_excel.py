from pathlib import Path

import duckdb
import pandas as pd

DB = Path("data/oilgas.duckdb")
OUT = Path("data/audit/oilgas_audit.xlsx")

OUT.parent.mkdir(parents=True, exist_ok=True)

queries = {
    "revenue_lines": """
        SELECT
          o.operator_name,
          rs.owner_number,
          rs.check_number,
          rs.check_date,
          rs.accounting_period,
          rs.check_amount,
          p.property_code,
          p.property_name,
          p.county,
          p.state,
          rp.product,
          rl.production_period,
          rl.line_type,
          rl.revenue_type,
          rl.tax_deduct_code,
          rl.property_volume,
          rl.unit_price,
          rl.property_gross_value,
          rl.property_deductions,
          rl.property_net_value,
          rl.owner_interest,
          rl.distribution_interest,
          rl.owner_volume,
          rl.owner_gross_value,
          rl.owner_deductions,
          rl.owner_net_value
        FROM revenue_line AS rl
        JOIN revenue_statement AS rs
          ON rs.statement_id = rl.statement_id
        JOIN operator AS o
          ON o.operator_id = rs.operator_id
        JOIN property AS p
          ON p.property_id = rl.property_id
        JOIN revenue_product AS rp
          ON rp.product_id = rl.product_id
        ORDER BY
          rs.check_date,
          o.operator_name,
          rs.check_number,
          p.property_name,
          rp.product,
          rl.production_period,
          rl.line_type
    """,
    "revenue_check_totals": """
        SELECT
          o.operator_name,
          rs.owner_number,
          rs.check_number,
          rs.check_date,
          rs.accounting_period,
          rs.check_amount,
          SUM(rl.owner_net_value) AS line_owner_net_total,
          rs.check_amount - SUM(rl.owner_net_value) AS variance,
          COUNT(*) AS line_count
        FROM revenue_statement AS rs
        JOIN operator AS o
          ON o.operator_id = rs.operator_id
        JOIN revenue_line AS rl
          ON rl.statement_id = rs.statement_id
        GROUP BY
          o.operator_name,
          rs.owner_number,
          rs.check_number,
          rs.check_date,
          rs.accounting_period,
          rs.check_amount
        ORDER BY
          rs.check_date,
          o.operator_name,
          rs.check_number
    """,
    "jib_lines": """
        SELECT
          o.operator_name,
          ji.owner_number,
          ji.invoice_number,
          ji.invoice_date,
          ji.accounting_period,
          ji.invoice_total,
          jcc.cost_center_code,
          jcc.cost_center_name,
          jl.afe,
          jl.cost_class,
          jl.account_group,
          jl.op_account,
          jl.minor_account,
          jl.description,
          v.vendor_name,
          jl.vendor_invoice,
          jl.activity_period,
          jl.partner_percent,
          jl.gross_amount,
          jl.invoiced_amount
        FROM jib_line AS jl
        JOIN jib_invoice AS ji
          ON ji.invoice_id = jl.invoice_id
        JOIN operator AS o
          ON o.operator_id = ji.operator_id
        JOIN jib_cost_center AS jcc
          ON jcc.cost_center_id = jl.cost_center_id
        LEFT JOIN vendor AS v
          ON v.vendor_id = jl.vendor_id
        ORDER BY
          ji.invoice_date,
          o.operator_name,
          ji.invoice_number,
          jcc.cost_center_code,
          jl.display_order
    """,
    "jib_invoice_totals": """
        SELECT
          o.operator_name,
          ji.owner_number,
          ji.invoice_number,
          ji.invoice_date,
          ji.accounting_period,
          ji.invoice_total,
          SUM(jl.invoiced_amount) AS line_invoiced_total,
          ji.invoice_total - SUM(jl.invoiced_amount) AS variance,
          COUNT(*) AS line_count
        FROM jib_invoice AS ji
        JOIN operator AS o
          ON o.operator_id = ji.operator_id
        JOIN jib_line AS jl
          ON jl.invoice_id = ji.invoice_id
        GROUP BY
          o.operator_name,
          ji.owner_number,
          ji.invoice_number,
          ji.invoice_date,
          ji.accounting_period,
          ji.invoice_total
        ORDER BY
          ji.invoice_date,
          o.operator_name,
          ji.invoice_number
    """,
    "jib_cost_center_totals": """
        WITH line_totals AS (
          SELECT
            ji.invoice_id,
            jl.cost_center_id,
            SUM(jl.gross_amount) AS line_gross_total,
            SUM(jl.invoiced_amount) AS line_invoiced_total,
            COUNT(*) AS line_count
          FROM jib_invoice AS ji
          JOIN jib_line AS jl
            ON jl.invoice_id = ji.invoice_id
          GROUP BY
            ji.invoice_id,
            jl.cost_center_id
        ),

        summary_totals AS (
          SELECT
            invoice_id,
            cost_center_id,
            SUM(invoiced_amount) AS summary_invoiced_total
          FROM jib_cost_center_summary
          GROUP BY
            invoice_id,
            cost_center_id
        )

        SELECT
          o.operator_name,
          ji.owner_number,
          ji.invoice_number,
          ji.invoice_date,
          ji.accounting_period,
          jcc.cost_center_code,
          jcc.cost_center_name,
          lt.line_gross_total,
          lt.line_invoiced_total,
          st.summary_invoiced_total,
          st.summary_invoiced_total - lt.line_invoiced_total AS variance,
          lt.line_count
        FROM line_totals AS lt
        JOIN jib_invoice AS ji
          ON ji.invoice_id = lt.invoice_id
        JOIN operator AS o
          ON o.operator_id = ji.operator_id
        JOIN jib_cost_center AS jcc
          ON jcc.cost_center_id = lt.cost_center_id
        LEFT JOIN summary_totals AS st
          ON st.invoice_id = lt.invoice_id
         AND st.cost_center_id = lt.cost_center_id
        ORDER BY
          ji.invoice_date,
          o.operator_name,
          ji.invoice_number,
          jcc.cost_center_code
    """,
}

con = duckdb.connect(str(DB))

with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
    for sheet_name, query in queries.items():
        df = con.execute(query).fetchdf()
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Wrote {OUT}")
