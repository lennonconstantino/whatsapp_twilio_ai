"""
PostgreSQL implementation of the Repository Pattern using raw SQL (psycopg2).
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from src.core.database.interface import IRepository
from src.core.utils import get_logger

logger = get_logger(__name__)

T = TypeVar("T")  # Pydantic Model


class PostgresRepository(Generic[T]):
    """
    PostgreSQL implementation of IRepository using raw SQL (psycopg2).

    This class generates and executes raw SQL queries, mapping results directly
    to Pydantic models without an ORM overhead.
    """

    def __init__(self, connection, table_name: str, model_class: Type[T]):
        """
        Initialize Postgres Raw repository.

        Args:
            connection: psycopg2 connection object
            table_name: Name of the database table
            model_class: Pydantic model class (for return types)
        """
        self.connection = connection
        self.table_name = table_name
        self.model_class = model_class

    def _execute_query(
        self,
        query: sql.Composable,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
    ) -> Any:
        """Helper to execute queries with cursor management."""
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(query, params)

            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()

            self.connection.commit()
            return cursor.rowcount

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error executing query on {self.table_name}", error=str(e))
            raise
        finally:
            cursor.close()

    def create(self, data: Dict[str, Any]) -> Optional[T]:
        """
        Create a new record using raw INSERT.
        """
        columns = data.keys()
        values = data.values()

        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
            sql.Identifier(self.table_name),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )

        result = self._execute_query(query, tuple(values), fetch_one=True)

        if result:
            self.connection.commit()
            return self.model_class(**result)
        return None

    def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[T]:
        """
        Find a record by ID using raw SELECT.
        """
        query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
            sql.Identifier(self.table_name), sql.Identifier(id_column)
        )

        result = self._execute_query(query, (id_value,), fetch_one=True)

        if result:
            return self.model_class(**result)
        return None

    def update(
        self, id_value: Union[int, str], data: Dict[str, Any], id_column: str = "id"
    ) -> Optional[T]:
        """
        Update a record using raw UPDATE.
        """
        if not data:
            return self.find_by_id(id_value, id_column)

        set_clauses = [
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in data.keys()
        ]

        query = sql.SQL("UPDATE {} SET {} WHERE {} = %s RETURNING *").format(
            sql.Identifier(self.table_name),
            sql.SQL(", ").join(set_clauses),
            sql.Identifier(id_column),
        )

        # Params: values for SET + id_value for WHERE
        params = tuple(data.values()) + (id_value,)

        result = self._execute_query(query, params, fetch_one=True)

        if result:
            self.connection.commit()
            return self.model_class(**result)
        return None

    def delete(self, id_value: Union[int, str], id_column: str = "id") -> bool:
        """
        Delete a record using raw DELETE.
        """
        query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
            sql.Identifier(self.table_name), sql.Identifier(id_column)
        )

        rowcount = self._execute_query(query, (id_value,))
        return rowcount > 0

    def find_by(self, filters: Dict[str, Any], limit: int = 100) -> List[T]:
        """
        Find records by equality filters using raw SELECT.
        """
        conditions = []
        values = []

        for k, v in filters.items():
            conditions.append(
                sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            )
            values.append(v)

        where_clause = (
            sql.SQL(" WHERE {}").format(sql.SQL(" AND ").join(conditions))
            if conditions
            else sql.SQL("")
        )
        limit_clause = sql.SQL(" LIMIT %s")

        query = (
            sql.SQL("SELECT * FROM {}").format(sql.Identifier(self.table_name))
            + where_clause
            + limit_clause
        )

        # Params: filter values + limit
        params = tuple(values) + (limit,)

        results = self._execute_query(query, params, fetch_all=True)

        return [self.model_class(**row) for row in results]

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records using raw SELECT COUNT(*).
        """
        conditions = []
        values = []

        if filters:
            for k, v in filters.items():
                conditions.append(
                    sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
                )
                values.append(v)

        where_clause = (
            sql.SQL(" WHERE {}").format(sql.SQL(" AND ").join(conditions))
            if conditions
            else sql.SQL("")
        )

        query = (
            sql.SQL("SELECT COUNT(*) as count FROM {}").format(
                sql.Identifier(self.table_name)
            )
            + where_clause
        )

        result = self._execute_query(query, tuple(values), fetch_one=True)
        return result["count"] if result else 0

    def query_dynamic(
        self, select_columns: List[str] = None, filters: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute dynamic query with raw SQL.
        """
        # Select columns
        if select_columns:
            select_clause = sql.SQL(", ").join(map(sql.Identifier, select_columns))
        else:
            select_clause = sql.SQL("*")

        query = sql.SQL("SELECT {} FROM {}").format(
            select_clause, sql.Identifier(self.table_name)
        )

        params = []
        if filters:
            conditions = []
            for f in filters:
                col = f.get("column")
                val = f.get("value")
                op = f.get("operator", "eq")

                # Basic safety check for column names
                # Ideally, validate against a schema or allow-list

                if op == "eq":
                    conditions.append(
                        sql.SQL("{} = {}").format(
                            sql.Identifier(col), sql.Placeholder()
                        )
                    )
                elif op == "gt":
                    conditions.append(
                        sql.SQL("{} > {}").format(
                            sql.Identifier(col), sql.Placeholder()
                        )
                    )
                elif op == "lt":
                    conditions.append(
                        sql.SQL("{} < {}").format(
                            sql.Identifier(col), sql.Placeholder()
                        )
                    )

                params.append(val)

            if conditions:
                query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)

        results = self._execute_query(query, tuple(params), fetch_all=True)

        # Return dicts directly as requested by interface
        return [dict(row) for row in results]
