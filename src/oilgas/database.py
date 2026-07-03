from __future__ import annotations

from pathlib import Path

import duckdb

from oilgas.config import settings


class Database:

    def __init__(self):

        self.path = settings.database

        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = duckdb.connect(str(self.path))

    def initialize(self):

        sql = settings.schema_sql.read_text()

        self.conn.execute(sql)

    def close(self):

        self.conn.close()

    def execute(self, sql: str, params=None):

        if params:

            return self.conn.execute(sql, params)

        return self.conn.execute(sql)

    def dataframe(self, sql: str):

        return self.conn.execute(sql).fetchdf()

    def scalar(self, sql: str):

        return self.conn.execute(sql).fetchone()[0]
