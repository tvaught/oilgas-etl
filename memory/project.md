# Oil & Gas Revenue and JIB ETL

## Objective

Build a deterministic, auditable ETL pipeline that converts oil and gas accounting PDFs into normalized DuckDB data for validation, reporting, Excel/Power Query review, and future analytics.

Supported document families:

- EnergyLink-style revenue statements.
- Highmark EnergyLink `Operator Invoice - JIB` packages.

## Pipeline

```text
PDF
  -> PDFExtractor / layout analysis
  -> DocumentClassifier
  -> document-specific parser
  -> Pydantic models
  -> repository validation + duplicate detection
  -> DuckDB tables/views
  -> SQL / Excel / analytics
```

Core commands:

```bash
uv run oilgas init
uv run oilgas ingest <path>
uv run oilgas parse <pdf>
uv run oilgas jib parse <pdf>
uv run oilgas jib ingest <path>
uv run pytest
```

## Design Principles

- Deterministic parser rules are preferred over fuzzy heuristics.
- Source layout is authoritative.
- Preserve source signs/values where meaningful.
- Store normalized business data, not raw coordinates/text, for now.
- Validate financial totals and fail loudly on ambiguous detail rows.
- Keep parser-specific behavior isolated by document/operator format.

## Revenue Model

Revenue output is conceptually:

```text
RevenueStatement
  -> RevenueProperty
    -> RevenueProduct
      -> RevenueLine
```

Important fields include check number/date/amount, operator, property, product, production period, owner/distribution interest, owner volume, deductions, and owner net value.

Important behavior:

- Duplicate detection uses `source_file.sha256` and existing statement linkage.
- Page breaks can split property/product sections; parser builds property blocks across pages.
- Bare continuation codes `TRN`, `MIS`, `TRT`, `GAT` merge into prior logical `SEV` or `MIS` rows.
- Interest-qualified rows such as `WI TRN` are independent.
- `JOINT INTEREST BILLING` can be a product heading.

Revenue validation target:

```text
sum(revenue_line.owner_net_value) == revenue_statement.check_amount
```

## JIB Model

Phase 1 JIB support targets Highmark only.

JIB output is conceptually:

```text
JIBInvoice
  -> JIBCostCenterSummary
  -> JIBLine
```

Important invoice fields:

- operator
- owner_number
- invoice_number
- invoice_date
- accounting_period
- invoice_total

Important cost center/detail fields:

- cost_center_code
- cost_center_name
- afe
- description
- cost_class
- account_group
- op_account
- minor_account
- vendor_name
- vendor_invoice
- activity_period
- partner_percent
- gross_amount
- invoiced_amount

Accounting conventions:

- JIB expenses are stored positive in `invoiced_amount`.
- Credits/reversals retain source sign.
- JIB cost centers are not revenue properties and should not be inserted into `property`.
- Cashflow reporting should compute revenue minus JIB expense.

Duplicate JIB detection:

```text
operator_id + invoice_number
```

JIB validation targets:

- summary invoiced total equals invoice total.
- detail invoiced total equals invoice total.
- detail totals by cost center equal summary totals by cost center, after aggregating duplicate summary rows.

## DuckDB Tables

Important table groups:

- `source_file`
- `operator`
- `property`
- `revenue_statement`
- `revenue_product`
- `revenue_line`
- `jib_invoice`
- `jib_cost_center`
- `jib_cost_center_summary`
- `jib_line`
- `vendor`

Schema files are in `sql/`. There is no migration system yet; rebuilding the DB may be required after schema changes.

## Reporting App

The initial web MVP lives in `src/oilgas/web/` and is started with:

```bash
uv run oilgas app
```

Technology choices:

- Flask with server-rendered Jinja templates.
- Bokeh embedded in Flask pages; no Bokeh server or external Plotly service.
- Direct read-only DuckDB SQL in `ReportRepository`, not an ORM.
- CSV/XLSX exports (`openpyxl`) of report data.
- Source PDF route resolves the existing `source_file.filepath`; PDFs are not stored as DuckDB BLOBs.

Implemented reports/pages:

- monthly revenue, JIB expense, and net cashflow;
- production history using property gross and recorded owner fields;
- simple-average source unit-price history, excluding non-positive price/volume values;
- revenue and JIB detail audit tables with source PDF links.

Cashflow is rolled up by month without property-to-JIB matching. Its drilldown shows revenue by operator/property and JIB expense by operator/cost center as separate records; no expense is allocated automatically.

Future web work:

- printable/PDF evidence packages and Bokeh PNG/SVG export;
- trailing-12-month deficit dashboard for prudent-operator analysis;
- authentication before non-local deployment;
- prudent-operator deficit analysis by operator/property/cost center;

## Testing / Coverage

Relevant tests include revenue parser/repository/totals, JIB parser/repository, classifier, hashing, and parser model tests.

Recently added coverage tests:

- `tests/test_classifier.py`
- `tests/test_hashing.py`
- `tests/test_parser_model.py`

Last known suite result: `29 passed`.
