# Current Project Status

## Completed

### Revenue ETL

* Revenue parser extracts normalized transaction fields and persists revenue statements to DuckDB.
* Continuation-aware revenue parsing is implemented.
* Known XTO continuation codes currently include:
  * `TRN`
  * `MIS`
  * `TRT`
  * `GAT`
* Bare continuation rows merge into the previous logical `SEV` or `MIS` base row.
* Interest-qualified rows such as `WI TRN` remain independent rows.
* Page-break-aware revenue property parsing is implemented so property/product rows that continue at the top of the next page are retained.
* `JOINT INTEREST BILLING` is recognized as a revenue product heading when it appears on Highmark revenue statements.
* Revenue duplicate detection is implemented using `source_file.sha256` and statement linkage.
* Revenue statement total regression test validates that persisted `revenue_line.owner_net_value` sums to `revenue_statement.check_amount` for the Highmark June 2026 fixture.

### JIB ETL

* Phase 1 Highmark EnergyLink JIB ETL is implemented.
* JIB parser ignores Statement of Account pages and parses Highmark `Operator Invoice - JIB` invoice packages.
* Highmark JIB parsing captures:
  * operator
  * owner_number
  * invoice_number
  * invoice_date
  * accounting_period
  * invoice_total
  * cost center summary rows
  * cost center detail lines
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
* JIB expenses are stored as positive expenses; credits/reversals retain source sign.
* JIB duplicate detection skips by `operator_id + invoice_number`.
* Statement-of-account-only or non-Highmark JIB PDFs return no invoice and are skipped by JIB ingest.
* `oilgas jib parse` and `oilgas jib ingest` commands are available.
* Generic `oilgas ingest` can classify and dispatch Highmark JIB PDFs.
* Full Highmark JIB fixture directory currently imports successfully into a temporary DuckDB:
  * 50 invoices
  * 48,518 JIB detail lines
  * total invoice amount equals total detail `invoiced_amount` across imported fixtures.

## Current Focus

Stabilize JIB reporting and downstream analytics after Phase 1 Highmark JIB ingestion.

## Remaining Work

* Add SQL views for monthly cashflow:
  * revenue owner net value
  * JIB invoiced expense
  * revenue minus JIB expense
* Add JIB reporting views by:
  * operator
  * accounting_period
  * cost_center
  * vendor
  * cost_class
  * account_group
* Add additional parser subclasses for non-Highmark JIB formats:
  * Chevron sample in `data/raw/chevron/jib/`
  * Finley sample in `data/raw/finley/jib/`
* Decide whether existing databases need migration support or should be rebuilt from schema during early development.
* Continue expanding regression fixtures as new JIB/revenue edge cases are discovered.

## Instructions for Future Coding Agents

Before changing parser logic:

* preserve existing normalized field names
* preserve deterministic parsing behavior
* avoid replacing explicit rules with broad heuristics
* add new edge cases by extending isolated detection/parsing helpers
* keep validation strict for financial totals
* treat correctness and auditability as more important than parser brevity

When modifying JIB parsing:

* keep Highmark parser behavior isolated from future Chevron/Finley parsers
* do not map JIB cost centers to revenue properties
* store JIB expenses as positive `invoiced_amount` values
* preserve source signs for credits/reversals
* fail on unrecognized financial detail rows unless there is explicit continuation handling
