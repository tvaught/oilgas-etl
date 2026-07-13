# Oil & Gas Revenue and JIB ETL

## Objective

Build a robust ETL pipeline that converts oil and gas accounting PDFs into normalized structured data suitable for DuckDB storage, validation, reporting, and Excel/Power Query analytics.

Current supported document families:

* EnergyLink-style revenue statements
* Highmark EnergyLink JIB invoice packages

The parser should tolerate statement layout variation while producing deterministic, auditable records.

## High-Level Pipeline

```text
PDF
  ↓
Document extraction / OCR
  ↓
Token stream with coordinates
  ↓
Document-specific parser
  ↓
Normalized business models
  ↓
Validation
  ↓
DuckDB
  ↓
SQL views / Excel / analytics
```

## Core Design Principles

* Parsing should be deterministic.
* Parsing rules should be explicit rather than heuristic whenever possible.
* Intermediate parsed structures should be inspectable for debugging.
* Preserve original source values whenever practical.
* Normalize only after the parser has correctly identified semantic fields.
* Financial imports should validate totals and fail loudly on ambiguous detail rows.

## Revenue ETL

Revenue parser output is organized as:

```text
RevenueStatement
  → RevenueProperty
    → RevenueProduct
      → RevenueLine
```

Typical revenue line fields include:

* line_type
* revenue_type
* tax_deduct_code
* production_period
* property_volume
* unit_price
* property_net_value
* owner_interest
* distribution_interest
* owner_volume
* owner_net_value

Important revenue behavior:

* Page-break-aware property parsing keeps property/product lines together across pages.
* Continuation records are merged into their prior logical transaction and suppressed from final output.
* Current bare continuation codes include `TRN`, `MIS`, `TRT`, and `GAT`.
* Continuations can merge into prior `SEV` or `MIS` base rows.

## JIB ETL

Phase 1 JIB support targets Highmark EnergyLink `Operator Invoice - JIB` packages.

JIB parser output is organized as:

```text
JIBInvoice
  → JIBCostCenterSummary
  → JIBLine
```

Highmark JIB packages may begin with Statement of Account pages. These are skipped. The parser starts from the invoice summary page and then parses cost-center detail pages.

JIB invoice fields include:

* operator
* owner_number
* invoice_number
* invoice_date
* accounting_period
* invoice_total

JIB cost center summary fields include:

* cost_center_code
* cost_center_name
* afe
* description
* gross_amount
* cash_call_amount
* invoiced_amount
* display_order

JIB detail line fields include:

* cost_center_code
* cost_center_name
* afe
* cost_class
* account_group
* op_account
* minor_account
* description
* vendor_name
* vendor_invoice
* activity_period
* partner_percent
* gross_amount
* invoiced_amount
* display_order

JIB accounting convention:

* Expenses are stored as positive `invoiced_amount` values.
* Credits/reversals retain their source sign.
* Cashflow reporting should compute revenue minus JIB expense, e.g.:

```text
net_cashflow = revenue_owner_net_value - jib_invoiced_amount
```

## DuckDB Storage

Important table groups:

* `source_file`
* `operator`
* `revenue_statement`
* `revenue_product`
* `revenue_line`
* `jib_invoice`
* `jib_cost_center`
* `jib_cost_center_summary`
* `jib_line`
* `vendor`

JIB cost centers are operator-specific and are not treated as revenue properties.

## Validation Philosophy

Revenue validation should compare statement check amount to summed line owner net values.

JIB validation should compare:

* sum of cost center summary `invoiced_amount` to invoice total
* sum of detail line `invoiced_amount` to invoice total
* sum of detail line `invoiced_amount` by cost center to summary totals by cost center

## Parser Philosophy

The parser should identify the semantic meaning of each line before attempting to merge or normalize records.

Future parser improvements should extend existing rules and parser-specific helpers rather than replacing working behavior.
