from typing import List, Optional
from datetime import datetime, timedelta

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    Reminder, ReminderCreate
)
from src.modules.ai.engines.lchain.feature.relationships.repositories.reminder_repository import ReminderRepository

class PostgresReminderRepository(PostgresRepository[Reminder], ReminderRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "reminder", Reminder)

    def create_from_schema(self, reminder: ReminderCreate) -> Optional[Reminder]:
        return self.create(reminder.model_dump())

    def get_upcoming(self, days: int = 7) -> List[Reminder]:
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        query = """
            SELECT * FROM reminder 
            WHERE due_date >= %s 
            AND due_date <= %s 
            AND status = 'open' 
            ORDER BY due_date ASC
        """
        
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(query, (start_date, end_date))
                rows = cur.fetchall()
                if not rows:
                    return []
                cols = [d[0] for d in cur.description]
                return [self.model_class(**dict(zip(cols, r))) for r in rows]
            finally:
                cur.close()
