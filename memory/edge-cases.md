# Known Parsing Edge Cases

## Revenue

### Bare Continuation Transactions

Known bare continuation codes:

- `TRN`
- `MIS`
- `TRT`
- `GAT`

These are not independent rows when they lack an interest-qualified prefix such as `WI`, `RI`, or `OR`. They merge into the previous logical base row when the base row ends in:

- `SEV`
- `MIS`

Merge behavior:

- add continuation `owner_net_value` to the base row.
- preserve base row metadata.
- suppress continuation row from final output.

Interest-qualified rows such as `WI TRN` stay independent.

### Owner Net Normalization

Some XTO/Chevron-style bare continuation or deduction rows place the only owner-level amount in a coordinate slot closer to `owner_volume` than `owner_net_value`.

Current parser normalizes `owner_volume` to `owner_net_value` when `owner_net_value` is missing for bare:

- `TRN`
- `MIS`
- `TRT`
- `GAT`
- `DEDUCT`

### Page Breaks

Revenue properties/products can continue across page breaks before the next `Property:` header. The parser builds property blocks across the document and skips repeated page furniture so top-of-page detail rows are not orphaned.

### Product Heading Ambiguity

`JOINT INTEREST BILLING` contains `INTEREST` but is a valid product heading on Highmark revenue statements. Keep explicit handling for it.

## JIB

### Statement of Account Pages

Highmark JIB packages may begin with `Statement of Account` pages listing outstanding invoices. These are ignored. Parsing begins at the first Highmark `Operator Invoice - JIB` invoice summary/detail page.

Statement-of-account-only PDFs and unsupported non-Highmark JIB PDFs currently return no parsed invoice and are skipped.

### Duplicate Cost Centers in Summary

A summary can have multiple rows for the same cost center, for example one AFE-specific row plus one non-AFE row. Validation must aggregate summary rows by cost center before comparing to detail totals.

### Repeated Detail Headers

Highmark detail pages repeat headers such as:

- `Statement`
- `Partner Operator Invoice`
- `Invoice Number ...`
- `Op Accounting Month ...`
- `Cost Center ...`
- column headers

The parser skips these rows. Repeated `Cost Center` headers for the same cost center should not reset pending vendor/detail continuation state.

### Vendor and Description Continuations

Vendor metadata may appear after a detail row using `~` separators, e.g.:

```text
JOE R. MAY OILFIELD PIPE & SUPPLY, LTD.~05-OI-693~~~~~~
```

The parser stores `vendor_name` and `vendor_invoice` from these rows.

Plain free-text continuation rows without `~` are appended to the prior line description.

### Cost Class / Account Group Context

Highmark detail pages include context headings that apply to following lines until replaced.

Known cost classes include:

- `Capital`
- `Expense`
- `Leasehold`

Known account group examples include:

- `RWO-REMEDIAL WORKOVER`
- `LOE-LEASE OPERATING EXPENSE`
- `Lease Operating Expense`
- `Plug and Abandon`

### Unsupported Formats

Finley and Chevron JIB samples exist in `data/raw/finley/jib/` and `data/raw/chevron/jib/`, but are not supported yet. Add separate parser logic rather than broadening Highmark rules.

## Reporting: Property / Cost Center Rollups

Revenue properties and JIB cost centers are different source concepts. The reporting app does not match or allocate them. Cashflow is rolled up by month only; monthly drilldown shows independent revenue-property and JIB-cost-center records.

Plant/general costs therefore remain visible as independent cost-center expenses.

## Reporting: Source PDFs

Audit links resolve `source_file.filepath`, which is an absolute ingestion-time path. If the reporting app is run on another machine, the raw PDF directory must be copied/synced to an equivalent available location or the link returns unavailable.

## General Rule

When uncertain, keep deterministic behavior, fail on ambiguous financial rows, and add narrow edge-case handling with tests rather than broad heuristics.
