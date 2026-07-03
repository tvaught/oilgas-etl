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

## Roadmap

- [ ] Database schema
- [ ] Revenue parser
- [ ] JIB summary parser
- [ ] Detailed JIB parser
- [ ] Categorization engine
- [ ] SQL views
- [ ] Excel integration
