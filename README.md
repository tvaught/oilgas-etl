# Oil & Gas ETL

A Python ETL pipeline for importing EnergyLink revenue statements and JIB statements into DuckDB.

## Goals

- Parse EnergyLink revenue PDFs
- Parse EnergyLink JIB PDFs
- Normalize data into DuckDB
- Eliminate duplicate imports
- Produce monthly working-interest cashflow
- Feed Excel dashboards through Power Query

---

## Features

- DuckDB backend
- Incremental imports
- SHA256 duplicate detection
- Revenue statement parser
- JIB summary parser
- Detailed JIB parser
- SQL reporting views
- Excel-friendly schema

---

## Project Layout

```
oilgas-etl/

data/
    raw/
    archive/
    oilgas.duckdb

src/oilgas/

tests/

sql/

config/
```

---

## Installation

Using uv:

```bash
uv sync
```

Run:

```bash
oilgas init
```

Import PDFs

```bash
oilgas import data/raw/highmark
```

Generate reports

```bash
oilgas report monthly
```

---

## Local Reporting App

Start the read-only browser app after initializing and ingesting the database:

```bash
uv run oilgas app
```

Then open <http://127.0.0.1:5000>. Use `--database <path>` or `--port <port>` when needed.

The initial MVP includes:

- revenue, JIB expense, and net-cashflow reporting;
- monthly cashflow roll-ups with independent revenue-property and JIB-cost-center drilldown;
- production and price history charts with URL-shareable filters;
- revenue/JIB detail audit tables with source-PDF links;
- CSV and Excel exports of each report.

The app is read-only and binds to localhost by default. It has **no authentication**; do not expose it to an untrusted network. Source-PDF links require the paths stored in `source_file.filepath` to be available on the machine running the app.

## Roadmap

- [ ] Database schema
- [ ] Revenue parser
- [ ] JIB summary parser
- [ ] Detailed JIB parser
- [ ] Categorization engine
- [ ] SQL views
- [ ] Excel integration
