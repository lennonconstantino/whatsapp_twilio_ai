from typing import List, Optional
from datetime import datetime, timedelta
from src.core.database.supabase_repository import SupabaseRepository
from src.core.database.interface import IDatabaseSession
from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.feature.relationships.models.models import Reminder, ReminderCreate
from src.modules.ai.engines.lchain.feature.relationships.repositories.reminder_repository import ReminderRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.utils import prepare_data_for_db

logger = get_logger(__name__)

class SupabaseReminderRepository(SupabaseRepository[Reminder], ReminderRepository):
    """Supabase implementation of ReminderRepository"""

    def __init__(self, client: IDatabaseSession):
        super().__init__(
            client=client,
            table_name="reminder",
            model_class=Reminder,
            validates_ulid=False,
        )

    def create_from_schema(self, reminder: ReminderCreate) -> Optional[Reminder]:
        """Cria reminder a partir do schema Pydantic"""
        data = prepare_data_for_db(reminder.model_dump())
        return self.create(data)

    def get_upcoming(self, days: int = 7) -> List[Reminder]:
        """Busca lembretes para os próximos dias"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .gte("due_date", start_date.isoformat())
                .lte("due_date", end_date.isoformat())
                .eq("status", "open")
                .order("due_date", desc=False)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(f"Error getting upcoming reminders", error=str(e))
            raise
