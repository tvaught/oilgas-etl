# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- Install dependencies: `uv sync`

### Running the Application
The main CLI is defined as `oilgas`. Use `uv run oilgas <command>` to execute.
- Initialize database: `uv run oilgas init`
- Ingest PDFs (Revenue/JIB): `uv run oilgas ingest <path>`
- Ingest JIB specifically: `uv run oilgas jib ingest <path>`
- Parse PDF to JSON: `uv run oilgas parse <pdf>` or `uv run oilgas jib parse <pdf>`

### Testing and Quality
- Run all tests: `uv run pytest`
- Run a specific test file: `uv run pytest tests/test_file.py`
- Lint code: `uv run ruff check .`
- Fix lint errors: `uv run ruff check . --fix`
- Type check: `uv run mypy .`

### Debugging PDF Extraction
The CLI provides several utilities for inspecting PDF layouts and extraction logic:
- `inspect <pdf>`: Basic page/text info.
- `classify <pdf>`: Identify document type.
- `head <pdf>`: Print first N lines of page 1.
- `words <pdf> --page <N>`: Dump words with coordinates.
- `rows <pdf> --page <N>`: Dump layout rows.
- `draw <pdf>`: Output a PDF (`layout.pdf`) with bounding boxes around extracted words.
- `header <pdf>`, `properties <pdf>`, `products <pdf>`, `lines <pdf>`: Test specific extraction stages.

## Architecture Overview

The project is an ETL pipeline that converts EnergyLink revenue and JIB (Joint Interest Billing) PDFs into a DuckDB database for financial reporting.

### High-Level Flow
`PDF File` $\rightarrow$ `PDFExtractor` $\rightarrow$ `Layout Analysis` $\rightarrow$ `DocumentClassifier` $\rightarrow$ `Specific Parser` $\rightarrow$ `Pydantic Model` $\rightarrow$ `Repository` $\rightarrow$ `DuckDB`

### Key Components
- **CLI (`src/oilgas/cli.py`)**: Built with Typer; provides the user interface for ingestion and debugging.
- **Extraction Engine**:
    - `PDFExtractor`: Uses `pymupdf` and `pdfplumber` to extract raw text and coordinates.
    - `Layout`: Groups words into logical rows based on Y-coordinates and handles spatial queries (e.g., "words right of phrase").
    - `DocumentClassifier`: Heuristically determines if a file is a Revenue statement or JIB invoice.
- **Parsers (`src/oilgas/parsers/`)**: Logic for transforming layout blocks into structured data (e.g., `RevenueParser`, `JIBParser`).
- **Persistence (`src/oilgas/repositories/`)**: Manages DuckDB insertions and implements duplicate detection using SHA256 hashes of the source files.
- **Database (`src/oilgas/database.py`)**: Handles connection management to the local `.duckdb` file.

### Project Structure
- `src/oilgas/`: Source code.
- `tests/`: Pytest suite for parsers and repositories.
- `sql/`: SQL definitions for reporting views used by downstream tools (e.g., Excel Power Query).
- `data/`: Local storage for raw PDFs, archived files, and the DuckDB database file (`oilgas.duckdb`).
- `config/`: Application configuration.
