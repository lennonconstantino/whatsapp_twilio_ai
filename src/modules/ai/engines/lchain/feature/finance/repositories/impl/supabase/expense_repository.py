from datetime import datetime
from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Expense,
    ExpenseCreate,
    ExpenseUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.expense_repository import (
    ExpenseRepository,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.utils import (
    prepare_data_for_db,
)

logger = get_logger(__name__)


class SupabaseExpenseRepository(SupabaseRepository[Expense], ExpenseRepository):
    """Repository for Expense operations via Supabase."""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="expense",
            model_class=Expense,
            validates_ulid=False,
        )

    def create_from_schema(self, expense: ExpenseCreate) -> Optional[Expense]:
        """Create expense from Pydantic schema"""
        data = prepare_data_for_db(expense.model_dump())
        return self.create(data)

    def update_from_schema(
        self, expense_id: int, expense: ExpenseUpdate
    ) -> Optional[Expense]:
        """Update expense from Pydantic schema"""
        data = prepare_data_for_db(expense.model_dump(exclude_unset=True))
        if not data:
            return self.find_by_id(expense_id)
        return self.update(expense_id, data)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Expense]:
        """Find expenses in a date range"""
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
                f"Error finding expenses by date range",
                error=str(e),
                start_date=start_date,
                end_date=end_date,
            )
            raise

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total expense in a period"""
        expenses = self.get_by_date_range(start_date, end_date)
        return sum(e.gross_amount for e in expenses)
