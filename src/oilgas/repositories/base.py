from __future__ import annotations

import duckdb


class Repository:
    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
    ):
        self.connection = connection

    def execute(
        self,
        sql: str,
        params: tuple = (),
    ):

        return self.connection.execute(sql, params)

    def executemany(
        self,
        sql: str,
        rows: list[tuple],
    ):

        return self.connection.executemany(sql, rows)

    def transaction(self):

        return self.connection
