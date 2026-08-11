# Current Project Status

## Snapshot

`oilgas-etl` is a Python/DuckDB ETL and reporting application for EnergyLink revenue statements and Highmark JIB invoices.

Core CLI:

```bash
uv run oilgas init
uv run oilgas ingest <path>
uv run oilgas jib ingest <path>
uv run pytest
```

Last known suite result: **36 passed**.

## Implemented ETL

### Revenue

- Normalized statement/property/product/line storage in DuckDB.
- SHA256 source-file duplicate detection.
- Page-break-aware property/product parsing.
- `JOINT INTEREST BILLING` accepted as a revenue product heading.
- XTO-specific fixed-column mapping correctly stores source Property `Volume`, `Price`, and `Value`.
- XTO bare `MIS`/`TRN`/`TRT`/`GAT` rows in the owner-deduction coordinate layout are preserved as raw lines with `owner_deductions`; `owner_net_value` is null and they are not merged into `WI SEV`.
- Generic continuation handling remains for layouts where the bare row actually carries an owner-net amount.
- `RevenueLine.owner_net_value` is nullable to preserve source rows with no source net field; revenue totals ignore null net values.

### Highmark JIB

- Parses Highmark EnergyLink `Operator Invoice - JIB` packages.
- Skips Statement of Account pages; parses summary/detail cost-center data.
- Stores expenses positive; credits/reversals retain source sign.
- Duplicate detection: `operator_id + invoice_number`.
- Correctly extracts operator from the accounting-month header row when invoice-number row contains owner address data.
- Canonical operator name: `HIGHMARK ENERGY OPERATING LLC`; comma variant normalizes to this value.
- Finley/Chevron JIB formats are still unsupported.

## Reporting App

Local command:

```bash
uv run oilgas app
```

Implemented pages:

- Overview/Cashflow
- Cashflow detail and audit/PDF drill-through
- Production history
- Price history
- Revenue audit
- JIB audit

Capabilities:

- URL-only filters; no hidden session filter state.
- Month/year range selectors from available reporting months.
- Operator, property, product, and cost-center-name filters.
- Cashflow is unallocated: revenue properties and JIB cost centers stay separate.
  - property-only filter: revenue rows only;
  - cost-center-only filter: JIB rows only;
  - both selected: both filtered row sets.
- Monthly, quarterly, and annual cashflow rollups.
- Cumulative chart mode is period-aware.
- Quarterly/annual cashflow charts use the same period labels as their tables.
- Charts include their filtered date span in their titles.
- Tables sort newest date/period first; charts remain chronological.
- Numeric cells are right-aligned/local-formatted; null/NaN displays as `--`.
- CSV/XLSX exports; source PDF links in audit/drill-through views.

## Working Production Deployment

Public authenticated site:

```text
https://oilgas.openhollow.com
```

Host/service names:

```text
Linode: openhollow
Application hostname: oilgas.openhollow.com
```

Architecture:

```text
Internet -> Linode Firewall + UFW -> Nginx :80/:443
         -> Gunicorn 127.0.0.1:8000 -> Flask/Bokeh -> DuckDB/PDFs
```

Server layout:

```text
/srv/oilgas/app/             Git checkout
/srv/oilgas/data/oilgas.duckdb
/srv/oilgas/data/raw/        source PDFs
/srv/oilgas/backups/
/etc/oilgas.env              root:oilgas, mode 640; secrets only
```

Service accounts:

- `travis`: SSH/deployment/admin user with key-based access and sudo.
- `oilgas`: non-login service account running Gunicorn.

Production app configuration is read from `/etc/oilgas.env`:

```text
OILGAS_AUTH_REQUIRED=true
OILGAS_DATABASE=/srv/oilgas/data/oilgas.duckdb
OILGAS_SECRET_KEY=secret
GOOGLE_CLIENT_ID=secret
GOOGLE_CLIENT_SECRET=secret
OILGAS_ALLOWED_EMAILS=approved addresses
```

Never commit or copy the environment file, credentials, session secret, or approved addresses into project docs/memory.

Authentication:

- Google OAuth via Authlib.
- Verified Google email must be in `OILGAS_ALLOWED_EMAILS`.
- Authentication protects reports, exports, audit routes, and source PDFs.
- OAuth callback URI:

```text
https://oilgas.openhollow.com/auth/google/callback
```

Deployment assets:

```text
deploy/oilgas.service
deploy/oilgas.openhollow.com.nginx
deploy/oilgas.env.example
deploy/README.md
```

- systemd service: `oilgas.service`.
- Nginx + Certbot issue/renew TLS.
- Cloud firewall and UFW permit only SSH, HTTP, and HTTPS; Gunicorn port 8000 stays loopback-only.

## Operational Notes

- `uv.lock` is now tracked and must be committed with dependency changes.
- On `openhollow`, rebuild the venv against the shared Python location under `/srv/oilgas/python`; do not use a venv whose interpreter lives under `/home/travis/.local` because the `oilgas` service user cannot execute it.
- For application updates: pull code, run `uv sync --frozen`, ensure app files are group-readable by `oilgas`, restart `oilgas` service.
- For data refreshes, sync raw PDFs to `/srv/oilgas/data/raw/` and ingest on `openhollow` so `source_file.filepath` points to server-valid paths.
- Existing databases require rebuild/reimport after parser/schema corrections; no formal migrations exist yet.

## Next Work

1. Back up DuckDB and raw PDFs off-host; document/automate restore.
2. Create a controlled data-refresh procedure or admin workflow.
3. Add printable/PDF evidence packages and Bokeh PNG/SVG export.
4. Add prudent-operator, trailing-12-month deficit analysis.
5. Add separate parsers for Chevron/Finley JIB formats.
6. Consider formal schema migrations.
