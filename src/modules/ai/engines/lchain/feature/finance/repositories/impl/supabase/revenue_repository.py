from datetime import datetime
from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Revenue,
    RevenueCreate,
    RevenueUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.revenue_repository import (
    RevenueRepository,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.utils import (
    prepare_data_for_db,
)

logger = get_logger(__name__)


class SupabaseRevenueRepository(SupabaseRepository[Revenue], RevenueRepository):
    """Repository for Revenue operations via Supabase."""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="revenue",
            model_class=Revenue,
            validates_ulid=False,  # Uses BIGSERIAL (int)
        )

    def create_from_schema(self, revenue: RevenueCreate) -> Optional[Revenue]:
        """
        Create revenue from Pydantic schema.
        Automatically converts datetime to ISO string.
        """
        data = prepare_data_for_db(revenue.model_dump())
        return self.create(data)

    def update_from_schema(
        self, revenue_id: int, revenue: RevenueUpdate
    ) -> Optional[Revenue]:
        """
        Update revenue from Pydantic schema.
        Only provided fields are updated.
        """
        data = prepare_data_for_db(revenue.model_dump(exclude_unset=True))
        if not data:  # If no data to update
            return self.find_by_id(revenue_id)
        return self.update(revenue_id, data)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Revenue]:
        """Find revenues in a date range."""
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .gte("date", start_date.isoformat())
                .lte("date", end_date.isoformat())
                .order("date", desc=True)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(
                f"Error finding revenues by date range",
                error=str(e),
                start_date=start_date,
                end_date=end_date,
            )
            raise

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total revenue in a period."""
        revenues = self.get_by_date_range(start_date, end_date)
        return sum(r.gross_amount for r in revenues)
