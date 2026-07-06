from __future__ import annotations

from pathlib import Path

import duckdb

from oilgas.config import settings


class Database:
    def __init__(
        self,
        path: Path | None = None,
    ):

        self.path = path or settings.database

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = duckdb.connect(
            str(self.path),
        )

    # ----------------------------------------------------------

    def initialize(self) -> None:

        sql_dir = Path(__file__).resolve().parents[2] / "sql"

        #
        # Execute numbered schema files first
        #
        for script in sorted(sql_dir.glob("[0-9][0-9][0-9]_*.sql")):
            self.connection.execute(
                script.read_text(),
            )

        #
        # Views last (optional)
        #
        views = sql_dir / "views.sql"

        if views.exists():
            self.connection.execute(
                views.read_text(),
            )

    # ----------------------------------------------------------

    def close(self) -> None:

        self.connection.close()

    # ----------------------------------------------------------

    def execute(
        self,
        sql: str,
        params=None,
    ):

        if params is None:
            return self.connection.execute(sql)

        return self.connection.execute(
            sql,
            params,
        )

    # ----------------------------------------------------------

    def dataframe(
        self,
        sql: str,
    ):

        return self.connection.execute(sql).fetchdf()

    # ----------------------------------------------------------

    def scalar(
        self,
        sql: str,
    ):

        return self.connection.execute(sql).fetchone()[0]

    # ----------------------------------------------------------

    def __enter__(self):

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):

        self.close()
