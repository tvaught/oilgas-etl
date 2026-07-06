from __future__ import annotations

import duckdb


class Database:
    def __init__(
        self,
        path: str,
    ):
        self.connection = duckdb.connect(path)

    @property
    def db(self):

        return self.connection
