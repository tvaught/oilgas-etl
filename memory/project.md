# Oil & Gas Revenue Statement ETL

## Objective

Build a robust ETL pipeline that converts PDF oil and gas revenue statements into normalized structured data suitable for storage in DuckDB and downstream analytics.

The parser should tolerate significant variation in statement layout while producing consistent records.

## High-Level Pipeline

```text
PDF
  ↓
Document extraction / OCR
  ↓
Token stream
  ↓
Statement parser
  ↓
Normalized transaction records
  ↓
Validation
  ↓
DuckDB
```

## Core Design Principles

* Parsing should be deterministic.
* Parsing rules should be explicit rather than heuristic whenever possible.
* Intermediate parsed structures should be inspectable for debugging.
* Preserve original source values whenever practical.
* Normalize only after the parser has correctly identified semantic fields.

## Normalized Transaction Fields

Typical parsed records contain fields similar to:

* line_type
* interest_type
* revenue_type
* production_period
* volume
* unit_price
* property_net_value
* owner_interest
* distribution_interest
* owner_volume
* owner_net_value
* tax_deduct_code (when applicable)

## Parser Philosophy

The parser should identify the semantic meaning of each line before attempting to merge or normalize records.

Continuation records are part of the previous logical transaction, not independent transactions.

Future parser improvements should extend existing rules rather than replacing working behavior.
