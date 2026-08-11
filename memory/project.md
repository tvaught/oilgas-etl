# Oil & Gas Revenue and JIB ETL

## Objective

Convert oil and gas accounting PDFs into deterministic, auditable DuckDB data for financial reporting, PDF reconciliation, Excel exports, and browser-based analysis.

Supported formats:

- EnergyLink-style revenue statements.
- Highmark EnergyLink `Operator Invoice - JIB` packages.

## Pipeline

```text
PDF -> extraction/layout -> classifier -> parser -> Pydantic model
    -> validation/repository -> DuckDB -> web/Excel/reporting
```

## Design Principles

- Prefer explicit, parser-specific rules to broad heuristics.
- Treat PDF/source layout as authoritative.
- Preserve source rows/values when needed for auditability.
- Keep JIB cost centers distinct from revenue properties.
- Use strict validation for financial totals and ambiguous rows.
- Keep reporting calculations SQL-first and auditable.

## Revenue Model and Important Rules

```text
RevenueStatement -> RevenueProperty -> RevenueProduct -> RevenueLine
```

Key fields include production/check dates, property/product, volume, unit price, property values, interests, owner deductions, and owner net value.

- `owner_net_value` may be null for a raw source line with no source net field.
- Reporting sums naturally ignore null net values.
- XTO full lines use explicit coordinates: Property Volume at x≈361, Price at x≈412, Value at x≈460.
- XTO bare `MIS`/`TRN` deduction rows use x≈712 for `owner_deductions`, retain their own row, and do not alter the preceding SEV owner-net field.
- Other generic continuation logic remains narrow and only merges rows that actually contain an owner-net continuation value.

Revenue duplicate identity: source-file SHA256.

## JIB Model and Important Rules

```text
JIBInvoice -> JIBCostCenterSummary + JIBLine
```

- Highmark only in Phase 1.
- Skip Statement of Account pages.
- Expenses are positive `invoiced_amount`; credit/reversal source sign is retained.
- Duplicate identity: operator + invoice number.
- Operator is taken from Highmark accounting-month header where available, not the owner/invoice row.
- Canonical name normalizer folds `HIGHMARK ENERGY OPERATING, LLC` into `HIGHMARK ENERGY OPERATING LLC`.

JIB validation checks invoice, summary, and cost-center detail totals.

## Reporting App

Located in `src/oilgas/web/`.

- Flask + Jinja, embedded Bokeh; no Bokeh server, Plotly service, ORM, or SQLAlchemy.
- Direct read-only DuckDB queries in `ReportRepository`.
- Pages: cashflow/overview, cashflow detail, production, prices, revenue audit, JIB audit.
- Cashflow supports monthly/quarterly/annual rollups, cumulative values, period-aware axes, and latest-first tables.
- Property/cost-center comparisons are deliberately unallocated. Filtering a single dimension suppresses unrelated unfiltered rows; selecting both displays both filtered branches.
- Audit source links resolve `source_file.filepath`; ingest on the host that serves PDFs.
- CSV/XLSX export supported.

## Production: `openhollow`

The working deployment is `https://oilgas.openhollow.com`.

```text
Nginx TLS proxy -> Gunicorn (one worker, 127.0.0.1:8000) -> Flask/Bokeh
```

- `travis` is the key-authenticated deployment/admin account.
- `oilgas` is the non-login system service account.
- systemd service is `oilgas.service`.
- Nginx and Certbot manage public HTTP/HTTPS/TLS.
- Linode firewall plus UFW expose SSH, HTTP, HTTPS only.
- `OILGAS_AUTH_REQUIRED=true` enables Google OAuth and approved-email access; do not store production values in Git.
- `ProxyFix` honors Nginx forwarding headers for correct OAuth HTTPS callback generation.
- Production database/PDFs are under `/srv/oilgas/data/`.

See `deploy/README.md` for non-secret deployment procedures.

## Dependency and Deployment Notes

- `uv.lock` is committed for reproducible production installs.
- Production uses `gunicorn` and `authlib`; `requests` is explicitly declared because Authlib Flask integration requires it.
- Production virtualenv must resolve Python from `/srv/oilgas/python`, not a user-private uv installation under `/home/travis`.
- Apply code changes: `git pull --ff-only`, `uv sync --frozen`, permissions update if needed, `systemctl restart oilgas`.

## Testing

Last known complete result: **36 passed**.

Important regression coverage includes:

- revenue statement total persistence;
- XTO price/volume mapping;
- XTO raw MIS/TRN deduction preservation;
- Highmark split-header operator parsing/canonicalization;
- Google-auth configuration and unauthenticated route protection.
