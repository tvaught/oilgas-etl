# Known Parsing and Deployment Edge Cases

## Revenue: XTO Source Rows

### Price / Volume Positions

XTO’s Property columns differ from the original generic map:

```text
x≈361 -> property_volume
x≈412 -> unit_price
x≈460 -> property_gross_value
```

Do not swap Volume and Price. Example January 2025 XTO oil rows have volumes such as `29.93` BBL and price `72.67`.

### Bare MIS/TRN Deduction Rows

For XTO fixed-layout bare `MIS`, `TRN`, `TRT`, or `GAT` rows, e.g.:

```text
Jun 22 MIS 0.14852000 0.00 3.68
Jun 22 TRN 0.14852000 0.00 (12.45)
```

- source x≈516 is property deductions;
- source x≈712 is owner deductions;
- there is no source owner-net value;
- preserve each raw row;
- leave `owner_net_value` null;
- do not merge it into the preceding SEV row.

Example for XTO `2022_07_29` / property `D668792-261`:

```text
WI SEV  owner_deductions=-17.95  owner_net_value=375.42
MIS     owner_deductions=  3.68  owner_net_value=null
TRN     owner_deductions=-12.45  owner_net_value=null
```

This reconciles owner deductions to `-26.72` while preserving the PDF Property Total owner net of `375.42`.

### Generic Continuations

Bare `TRN`, `MIS`, `TRT`, and `GAT` should only merge into a previous `SEV`/`MIS` row when the parsed record genuinely carries an owner-net continuation amount. Interest-qualified rows such as `WI TRN` remain independent.

### Page Breaks / Headings

- Property/product blocks can span page breaks before another property header.
- `JOINT INTEREST BILLING` is a valid product heading despite containing `INTEREST`.

## JIB: Highmark Headers

Highmark invoice packages can separate operator and owner data across rows:

```text
16556 HIGHMARK ENERGY OPERATING LLC Op Accounting Month June 2025
WHITE HAT EXPLORATION LTD PO BOX ... Invoice Number ...
```

Use the accounting-month row for the operator. Do not parse the White Hat owner/address row as the operator.

Normalize the comma variation:

```text
HIGHMARK ENERGY OPERATING, LLC -> HIGHMARK ENERGY OPERATING LLC
```

## JIB: Existing Parsing Rules

- Skip Statement of Account pages.
- Aggregate duplicate summary cost centers before total comparison.
- Repeated detail headers must not reset continuation state for the same cost center.
- `~` vendor lines populate vendor name/invoice.
- Plain free-text vendor/service lines append to preceding description.
- Cost class/account-group headings apply to following lines until changed.
- Finley/Chevron JIB samples remain unsupported; add separate parser logic.

## Reporting Rules

### Property / Cost Center

Revenue properties and JIB cost centers are separate source concepts. The app does not auto-match or allocate expenses.

- property-only filter -> only matching revenue rows;
- cost-center-only filter -> only matching JIB rows;
- both filters -> both selected record sets.

### Source PDFs

Audit links use absolute `source_file.filepath`. For a hosted deployment, ingest PDFs on the hosted server after syncing the raw archive; otherwise links point to unavailable paths.

## Production: `openhollow`

- Gunicorn must bind only to `127.0.0.1:8000`; do not expose port 8000 via firewall.
- Nginx is the public HTTP/HTTPS proxy.
- Google OAuth redirect URI is `https://oilgas.openhollow.com/auth/google/callback`.
- `OILGAS_AUTH_REQUIRED=true` intentionally prevents service startup if any required secret or email allowlist is absent.
- Gunicorn 26 attempts to create `/srv/oilgas/.gunicorn`; that directory must be owned by `oilgas`.
- A venv created with Python under `/home/travis/.local/share/uv` fails for the `oilgas` service user. Install/use shared Python under `/srv/oilgas/python` and make it group-readable/executable.

## General Rule

When uncertain, preserve deterministic behavior, retain auditable source semantics, fail clearly for ambiguous financial data, and add narrowly scoped regression tests.
