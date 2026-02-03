from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Revenue,
    RevenueCreate,
    RevenueUpdate,
)


class RevenueRepository(ABC):
    """
    Abstract Base Class for Revenue Repository.
    Defines the contract for Revenue data access.
    """

    @abstractmethod
    def create_from_schema(self, revenue: RevenueCreate) -> Optional[Revenue]:
        """Create revenue from Pydantic schema."""
        pass

    @abstractmethod
    def update_from_schema(
        self, revenue_id: int, revenue: RevenueUpdate
    ) -> Optional[Revenue]:
        """Update revenue from Pydantic schema."""
        pass

    @abstractmethod
    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Revenue]:
        """Find revenues in a date range."""
        pass

    @abstractmethod
    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total revenue in a period."""
        pass
