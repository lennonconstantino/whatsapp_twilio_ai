from datetime import datetime
from typing import List, Optional

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


class PostgresRevenueRepository(PostgresRepository[Revenue], RevenueRepository):
    """Repository for Revenue operations via Postgres."""

    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "revenue", Revenue)

    def create_from_schema(self, revenue: RevenueCreate) -> Optional[Revenue]:
        """Create revenue from Pydantic schema."""
        data = revenue.model_dump()
        # TODO: Handle datetime serialization if needed for Postgres (psycopg2 usually handles it)
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
        raise NotImplementedError("Postgres implementation not yet available")

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total revenue in a period."""
        raise NotImplementedError("Postgres implementation not yet available")
