from datetime import datetime
from typing import List, Optional

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Revenue,
    RevenueCreate,
    RevenueUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.revenue_repository import (
    RevenueRepository,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.interfaces import (
    IRevenueRepository,
)


class PostgresRevenueRepository(PostgresRepository[Revenue], RevenueRepository):
    """Repository for Revenue operations via Postgres."""

    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "revenue", Revenue)

    def create_from_schema(self, revenue: RevenueCreate) -> Optional[Revenue]:
        """Create revenue from Pydantic schema."""
        data = revenue.model_dump()
        return self.create(data)

    def update_from_schema(
        self, revenue_id: int, revenue: RevenueUpdate
    ) -> Optional[Revenue]:
        """Update revenue from Pydantic schema."""
        data = revenue.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(revenue_id)
        return self.update(revenue_id, data)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Revenue]:
        """Find revenues in a date range."""
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
        """Calculate total revenue in a period."""
        query = sql.SQL(
            "SELECT SUM(gross_amount) as total FROM {} WHERE date >= %s AND date <= %s"
        ).format(sql.Identifier(self.table_name))
        
        result = self._execute_query(
            query, 
            (start_date, end_date), 
            fetch_one=True
        )
        
        return float(result["total"] or 0.0)
