from typing import Optional
import asyncpg
from contextlib import asynccontextmanager

class AsyncPostgresDatabase:
    def __init__(self, *, dsn: str, minconn: int = 1, maxconn: int = 10):
        self.dsn = dsn
        self.minconn = minconn
        self.maxconn = maxconn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize the connection pool."""
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=self.minconn,
                max_size=self.maxconn,
                server_settings={
                    "search_path": "app,extensions,public"
                }
            )

    async def disconnect(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def connection(self):
        """Acquire a connection from the pool."""
        if not self._pool:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            yield conn
