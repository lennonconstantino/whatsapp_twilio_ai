"""
PostgreSQL implementation of the Repository Pattern using asyncpg.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
import re

from src.core.utils import get_logger
from src.core.database.postgres_async_session import AsyncPostgresDatabase
from psycopg2 import sql

logger = get_logger(__name__)

T = TypeVar("T")  # Pydantic Model


class PostgresAsyncRepository(Generic[T]):
    """
    PostgreSQL implementation of IRepository using asyncpg.
    """

    def __init__(self, db: AsyncPostgresDatabase, table_name: str, model_class: Type[T]):
        self.db = db
        self.table_name = table_name
        self.model_class = model_class

        # Handle schema qualification
        if "." in table_name:
            schema, table = table_name.split(".", 1)
            self.table_identifier = sql.Identifier(schema, table)
        else:
            self.table_identifier = sql.Identifier(table_name)

    def _convert_query_to_asyncpg(self, query: sql.Composable) -> str:
        """
        Convert psycopg2 sql object to string and replace %s with $1, $2, etc.
        """
        # We use a dummy context to get the string; standard SQL usually works.
        # If specific quoting is needed, this might be slightly off without a real conn,
        # but for identifiers it's usually fine in standard Postgres.
        query_str = query.as_string(None)
        
        # Replace %s with $1, $2, ...
        # We need to be careful if %s appears in literals, but with parametrized queries
        # literals should be handled by params.
        
        parts = query_str.split('%s')
        if len(parts) == 1:
            return query_str
        
        new_query = []
        for i, part in enumerate(parts[:-1]):
            new_query.append(part)
            new_query.append(f"${i+1}")
        new_query.append(parts[-1])
        
        return "".join(new_query)

    async def _execute_query(
        self,
        query: sql.Composable,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Any:
        """Helper to execute queries with asyncpg."""
        async with self.db.connection() as conn:
            try:
                sql_str = self._convert_query_to_asyncpg(query)
                args = params or ()

                # Debug logging
                # logger.debug(f"Executing Async SQL: {sql_str} | Params: {args}")

                if fetch_one:
                    row = await conn.fetchrow(sql_str, *args)
                    return dict(row) if row else None
                
                if fetch_all:
                    rows = await conn.fetch(sql_str, *args)
                    return [dict(row) for row in rows]

                # Execute only (INSERT/UPDATE/DELETE)
                result = await conn.execute(sql_str, *args)
                # result is usually "INSERT 0 1" or "UPDATE 1"
                # We can parse it if needed, but usually we return rowcount equivalent or rely on RETURNING
                
                # Extract row count from result string (e.g., "UPDATE 5" -> 5)
                parts = result.split(" ")
                if len(parts) > 0 and parts[-1].isdigit():
                    return int(parts[-1])
                return 1 # Default success

            except Exception as e:
                logger.error(
                    f"Error executing async query on {self.table_name}", error=str(e)
                )
                raise

    async def create(self, data: Dict[str, Any]) -> Optional[T]:
        columns = data.keys()
        values = data.values()

        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
            self.table_identifier,
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )

        result = await self._execute_query(
            query, tuple(values), fetch_one=True
        )

        if result:
            return self.model_class(**result)
        return None

    async def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[T]:
        query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
            self.table_identifier, sql.Identifier(id_column)
        )

        result = await self._execute_query(query, (id_value,), fetch_one=True)

        if result:
            return self.model_class(**result)
        return None

    async def update(
        self,
        id_value: Union[int, str],
        data: Dict[str, Any],
        id_column: str = "id",
        current_version: Optional[int] = None,
    ) -> Optional[T]:
        if not data:
            return await self.find_by_id(id_value, id_column)

        where_clause = sql.SQL("{} = %s").format(sql.Identifier(id_column))
        
        params_list = list(data.values())
        params_list.append(id_value)

        if current_version is not None:
            if "version" not in data:
                data = {**data, "version": current_version + 1}
                # Update params list with new version value if we added it
                # Wait, data.values() order matters.
                # Let's reconstruct params carefully.
                params_list = list(data.values()) # Re-grab values including version
                params_list.append(id_value)
            
            where_clause = where_clause + sql.SQL(" AND version = %s")
            params_list.append(current_version)

        set_clauses = [
            sql.SQL("{} = %s").format(sql.Identifier(k))
            for k in data.keys()
        ]

        query = sql.SQL("UPDATE {} SET {} WHERE ").format(
            self.table_identifier,
            sql.SQL(", ").join(set_clauses),
        ) + where_clause + sql.SQL(" RETURNING *")

        result = await self._execute_query(query, tuple(params_list), fetch_one=True)

        if result:
            return self.model_class(**result)
        return None

    async def delete(self, id_value: Union[int, str], id_column: str = "id") -> bool:
        query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
            self.table_identifier, sql.Identifier(id_column)
        )

        rowcount = await self._execute_query(query, (id_value,))
        return rowcount > 0

    async def find_by(self, filters: Dict[str, Any], limit: int = 100) -> List[T]:
        conditions = []
        values = []

        for k, v in filters.items():
            conditions.append(
                sql.SQL("{} = %s").format(sql.Identifier(k))
            )
            values.append(v)

        where_clause = (
            sql.SQL(" WHERE {}").format(sql.SQL(" AND ").join(conditions))
            if conditions
            else sql.SQL("")
        )
        limit_clause = sql.SQL(" LIMIT %s")

        query = (
            sql.SQL("SELECT * FROM {}").format(self.table_identifier)
            + where_clause
            + limit_clause
        )

        params = tuple(values) + (limit,)

        results = await self._execute_query(query, params, fetch_all=True)

        return [self.model_class(**row) for row in results]

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        conditions = []
        values = []

        if filters:
            for k, v in filters.items():
                conditions.append(
                    sql.SQL("{} = %s").format(sql.Identifier(k))
                )
                values.append(v)

        where_clause = (
            sql.SQL(" WHERE {}").format(sql.SQL(" AND ").join(conditions))
            if conditions
            else sql.SQL("")
        )

        query = (
            sql.SQL("SELECT COUNT(*) as count FROM {}").format(
                self.table_identifier
            )
            + where_clause
        )

        result = await self._execute_query(query, tuple(values), fetch_one=True)
        return result["count"] if result else 0
