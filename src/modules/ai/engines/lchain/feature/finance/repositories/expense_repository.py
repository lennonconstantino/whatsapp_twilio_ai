from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Expense,
    ExpenseCreate,
    ExpenseUpdate,
)


class ExpenseRepository(ABC):
    """
    Abstract Base Class for Expense Repository.
    Defines the contract for Expense data access.
    """

    @abstractmethod
    def create_from_schema(self, expense: ExpenseCreate) -> Optional[Expense]:
        """Create expense from Pydantic schema."""
        pass

    @abstractmethod
    def update_from_schema(
        self, expense_id: int, expense: ExpenseUpdate
    ) -> Optional[Expense]:
        """Update expense from Pydantic schema."""
        pass

    @abstractmethod
    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Expense]:
        """Find expenses in a date range."""
        pass

    @abstractmethod
    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total expense in a period."""
        pass
