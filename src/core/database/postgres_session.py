from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg2.extensions import register_adapter
from psycopg2.extras import Json
from psycopg2.pool import ThreadedConnectionPool


class PostgresDatabase:
    def __init__(self, *, dsn: str, minconn: int = 1, maxconn: int = 10):
        # Register adapters for JSON serialization
        register_adapter(dict, Json)
        
        self._pool = ThreadedConnectionPool(minconn=minconn, maxconn=maxconn, dsn=dsn)

    @contextmanager
    def connection(self) -> Iterator:
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        self._pool.closeall()
