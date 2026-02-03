from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.ai.engines.lchain.feature.relationships.models.models import Reminder, ReminderCreate

class ReminderRepository(ABC):
    """Interface for Reminder Repository."""

    @abstractmethod
    def create_from_schema(self, reminder: ReminderCreate) -> Optional[Reminder]:
        """Create reminder from Pydantic schema."""
        pass

    @abstractmethod
    def get_upcoming(self, days: int = 7) -> List[Reminder]:
        """Get upcoming reminders for the next N days."""
        pass
