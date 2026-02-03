from datetime import datetime
from typing import List, Optional

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Expense,
    ExpenseCreate,
    ExpenseUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.interfaces import (
    IExpenseRepository,
)


class PostgresExpenseRepository(PostgresRepository[Expense], IExpenseRepository):
    """Repository for Expense operations via Postgres."""

    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "expense", Expense)

    def create_from_schema(self, expense: ExpenseCreate) -> Optional[Expense]:
        """Create expense from Pydantic schema."""
        data = expense.model_dump()
        return self.create(data)

    def update_from_schema(
        self, expense_id: int, expense: ExpenseUpdate
    ) -> Optional[Expense]:
        """Update expense from Pydantic schema."""
        data = expense.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(expense_id)
        return self.update(expense_id, data)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Expense]:
        """Find expenses in a date range."""
        query = sql.SQL(
            "SELECT * FROM {} WHERE date >= %s AND date <= %s ORDER BY date DESC"
        ).format(sql.Identifier(self.table_name))
        
        results = self._execute_query(
            query, 
            (start_date, end_date), 
            fetch_all=True
        )
        
        return [self.model_class(**item) for item in results]

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total expense in a period."""
        query = sql.SQL(
            "SELECT SUM(amount) as total FROM {} WHERE date >= %s AND date <= %s"
        ).format(sql.Identifier(self.table_name))
        
        result = self._execute_query(
            query, 
            (start_date, end_date), 
            fetch_one=True
        )
        
        return float(result["total"] or 0.0)
