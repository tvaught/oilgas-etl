# Known Parsing Edge Cases

## Revenue: Continuation Transactions

A revenue tax/deduction/base row may be followed by one or more transaction rows that visually appear independent but are actually continuations.

Known bare continuation transaction codes:

* `TRN`
* `MIS`
* `TRT`
* `GAT`

These continuation lines:

* have no meaningful independent interest-qualified prefix such as `WI`, `RI`, or `OR`
* belong to the preceding logical transaction
* should not become independent output records

## Revenue Merge Rule

Continuation records should be merged into the previous base record.

Current allowed base row final transaction codes:

* `SEV`
* `MIS`

Specifically:

* add the continuation `owner_net_value`
* preserve the original base transaction metadata
* suppress the continuation record from final output

Interest-qualified rows such as `WI TRN` are independent rows and should not be treated as continuations.

## Revenue Owner Net Normalization

Some XTO/Chevron-style bare continuation or deduction rows contain only an owner-level amount whose x-coordinate maps closer to `owner_volume` than `owner_net_value`.

Current parser behavior normalizes `owner_volume` to `owner_net_value` for bare:

* `TRN`
* `MIS`
* `TRT`
* `GAT`
* `DEDUCT`

when `owner_net_value` is otherwise missing.

## Revenue Page Breaks

Highmark revenue properties/products can continue across page breaks before the next `Property:` header. Revenue parsing now builds property blocks across the whole document and skips repeated page header/footer furniture.

This prevents top-of-page detail rows from being orphaned.

## Revenue Product Headings Containing INTEREST

`JOINT INTEREST BILLING` can appear as a product heading on Highmark revenue statements. It must be recognized as a product heading even though it contains the word `INTEREST`.

## JIB: Statement of Account Pages

Highmark JIB PDFs may begin with `Statement of Account` pages listing outstanding invoices. These are not imported as JIB data.

JIB parsing starts at the first Highmark `Operator Invoice - JIB` page with a cost center summary table.

Statement-of-account-only PDFs and non-Highmark JIB samples currently return no parsed invoice and are skipped by JIB ingest.

## JIB: Duplicate Cost Centers in Summary

A Highmark JIB summary can contain multiple rows for the same cost center, for example:

* one AFE-specific row
* one non-AFE row for the same cost center

Validation aggregates summaries by cost center before comparing against detail-line totals.

## JIB: Detail Page Header Repetition

Highmark JIB detail pages repeat header rows such as:

* `Statement`
* `Partner Operator Invoice`
* `Invoice Number ...`
* `Op Accounting Month ...`
* `Cost Center ...`
* column headers

The detail parser skips these rows and preserves pending vendor/detail continuation state across repeated page headers.

## JIB: Vendor Continuation Rows

Highmark JIB detail rows can be followed by vendor metadata lines such as:

```text
JOE R. MAY OILFIELD PIPE & SUPPLY, LTD.~05-OI-693~~~~~~
```

The parser stores:

* `vendor_name`
* `vendor_invoice`

Some vendor/service notes continue as free text without `~`; these are appended to the prior line description.

## JIB: Cost Classes and Account Groups

Highmark detail pages can include cost class headings such as:

* `Capital`
* `Expense`
* `Leasehold`

and account group headings such as:

* `RWO-REMEDIAL WORKOVER`
* `LOE-LEASE OPERATING EXPENSE`
* `Lease Operating Expense`
* `Plug and Abandon`

These are carried onto subsequent detail lines until replaced.

## Guiding Principle

The source layout is authoritative.

When uncertain, preserve deterministic behavior, fail on ambiguous financial rows, and add narrow edge-case handling rather than broad heuristics.
