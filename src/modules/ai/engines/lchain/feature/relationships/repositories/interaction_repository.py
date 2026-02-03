from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.ai.engines.lchain.feature.relationships.models.models import Interaction, InteractionCreate

class InteractionRepository(ABC):
    """Interface for Interaction Repository."""

    @abstractmethod
    def create_from_schema(self, interaction: InteractionCreate) -> Optional[Interaction]:
        """Create interaction from Pydantic schema."""
        pass
    
    @abstractmethod
    def search(self, person_id: Optional[int] = None, channel: Optional[str] = None, type_: Optional[str] = None) -> List[Interaction]:
        """Search interactions with filters."""
        pass
