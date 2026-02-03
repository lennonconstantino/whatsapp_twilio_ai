from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.ai.engines.lchain.feature.relationships.models.models import Person, PersonCreate, PersonUpdate

class PersonRepository(ABC):
    """Interface for Person Repository."""

    @abstractmethod
    def create_from_schema(self, person: PersonCreate) -> Optional[Person]:
        """Create person from Pydantic schema."""
        pass

    @abstractmethod
    def update_from_schema(self, person_id: int, person: PersonUpdate) -> Optional[Person]:
        """Update person from Pydantic schema."""
        pass

    @abstractmethod
    def search_by_name_or_tags(self, name: Optional[str] = None, tags: Optional[str] = None) -> List[Person]:
        """Search people by name or tags."""
        pass
