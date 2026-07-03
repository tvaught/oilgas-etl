from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path.cwd()

    database: Path = Path("data/oilgas.duckdb")

    schema_sql: Path = Path("sql/schema.sql")

    raw_data: Path = Path("data/raw")

    archive: Path = Path("data/archive")

    parser_version: str = "0.1.0"


settings = Settings()
