# Current Project Status

## Snapshot

`oilgas-etl` is a Python/DuckDB ETL for oil & gas accounting PDFs. It currently supports:

- EnergyLink-style revenue statements.
- Highmark EnergyLink `Operator Invoice - JIB` packages.

Primary commands:

```bash
uv sync
uv run pytest
uv run oilgas init
uv run oilgas ingest <path>
uv run oilgas parse <pdf>
uv run oilgas jib parse <pdf>
uv run oilgas jib ingest <path>
```

Last known full test result: `29 passed`.

## Implemented

### Revenue ETL

- Parses revenue statements into statement/property/product/line models and persists to DuckDB.
- Duplicate detection uses `source_file.sha256` linked to `revenue_statement`.
- Page-break-aware property/product parsing retains detail rows that continue at top of next page.
- `JOINT INTEREST BILLING` is allowed as a product heading.
- Continuation-aware line parsing handles bare continuation codes: `TRN`, `MIS`, `TRT`, `GAT`.
- Bare continuation rows merge into prior `SEV` or `MIS` base rows.
- Interest-qualified rows like `WI TRN` remain independent.
- Regression tests include persisted revenue statement totals: `sum(revenue_line.owner_net_value) == revenue_statement.check_amount`.

Key files:

- `src/oilgas/parsers/revenue.py`
- `src/oilgas/parsers/revenue_line.py`
- `src/oilgas/parsers/product.py`
- `src/oilgas/repositories/revenue.py`
- `src/oilgas/models/revenue.py`

### JIB ETL

- Phase 1 Highmark JIB parser/repository/schema implemented.
- Parser skips leading `Statement of Account` pages and starts at `Operator Invoice - JIB` summary/detail data.
- Captures invoice header, cost center summary rows, cost center detail rows, cost class/account group context, vendor metadata, gross amount, and invoiced amount.
- Expenses are stored as positive `invoiced_amount`; credits/reversals keep source sign.
- Duplicate detection skips by `operator_id + invoice_number`.
- Generic `oilgas ingest` can classify and dispatch Highmark JIB PDFs.
- Non-Highmark JIB samples currently return no invoice and are skipped.

Key files:

- `src/oilgas/models/jib.py`
- `src/oilgas/parsers/jib.py`
- `src/oilgas/repositories/jib.py`
- `sql/004_jib.sql`
- `src/oilgas/cli.py`
- `src/oilgas/classifier.py`

Validated Highmark fixture ingest into a temp DB:

- 50 invoices
- 48,518 JIB detail lines
- `sum(jib_invoice.invoice_total) == sum(jib_line.invoiced_amount) == 181042.71`

### Reporting App MVP

- Local read-only Flask/Bokeh app is available through `uv run oilgas app`.
- Uses direct read-only DuckDB SQL via `src/oilgas/web/reports.py`; no ORM.
- Current pages: overview/cashflow, production history, price history, revenue audit, and JIB audit.
- Filters are URL query parameters only (shareable, no persisted session state), including dates, operator, property, product, and cost center. Production reports include adjustments by default.
- Net cashflow is rolled up only by month. Drilldown keeps revenue properties and JIB cost centers as separate records; no automatic matching or expense allocation is performed.
- Audit rows link to the original PDF through `source_file.filepath`; raw PDFs must be present on the app machine.
- Numeric table values are right-aligned and formatted with local thousands separators; missing/NaN values render as `--`. CSV and XLSX exports work. PNG/SVG Bokeh export and generated PDF report packages are not yet implemented.
- The app binds to `127.0.0.1` by default and has no authentication.

## Current Focus / Next Steps

1. Add audit/export support, preferably Excel or CSV first:
   - `revenue_lines`
   - `revenue_check_totals`
   - `jib_lines`
   - `jib_invoice_totals`
   - `jib_cost_center_totals`
2. Add SQL reporting views:
   - monthly revenue
   - monthly JIB expense
   - monthly cashflow: revenue minus JIB expense
   - JIB expense by operator/cost center/vendor/cost class/account group
3. Add simple schema migration support; currently old DBs may need rebuild after schema changes.
4. Add parser support for non-Highmark JIB samples:
   - `data/raw/finley/jib/`
   - `data/raw/chevron/jib/`
5. Continue adding narrow regression fixtures for parser edge cases.

## Agent Guidance

- Prefer deterministic, explicit parser rules over broad heuristics.
- Keep financial validation strict; fail ambiguous financial detail rows unless explicitly handled.
- Preserve normalized field names and existing behavior unless intentionally changing it.
- Keep Highmark JIB behavior isolated from future Chevron/Finley parsers.
- Do not map JIB cost centers to revenue `property`; they are separate concepts.
- Do not assume full-project Ruff is clean; targeted Ruff checks have passed for recently touched JIB files, but older files have existing lint issues.
