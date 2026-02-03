from typing import List, Optional
from src.core.database.supabase_repository import SupabaseRepository
from src.core.database.interface import IDatabaseSession
from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.feature.relationships.models.models import Person, PersonCreate, PersonUpdate
from src.modules.ai.engines.lchain.feature.relationships.repositories.person_repository import PersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.utils import prepare_data_for_db

logger = get_logger(__name__)

class SupabasePersonRepository(SupabaseRepository[Person], PersonRepository):
    """Supabase implementation of PersonRepository"""

    def __init__(self, client: IDatabaseSession):
        super().__init__(
            client=client,
            table_name="person",
            model_class=Person,
            validates_ulid=False,
        )

    def create_from_schema(self, person: PersonCreate) -> Optional[Person]:
        """Cria person a partir do schema Pydantic"""
        data = prepare_data_for_db(person.model_dump())
        return self.create(data)

    def update_from_schema(
        self, person_id: int, person: PersonUpdate
    ) -> Optional[Person]:
        """Atualiza person a partir do schema Pydantic"""
        data = prepare_data_for_db(person.model_dump(exclude_unset=True))
        if not data:
            return self.find_by_id(person_id)
        return self.update(person_id, data)

    def search_by_name_or_tags(self, name: Optional[str] = None, tags: Optional[str] = None) -> List[Person]:
        """Busca pessoas por nome ou tags"""
        try:
            query = self.client.table(self.table_name).select("*")
            
            if name:
                query = query.or_(f"first_name.ilike.%{name}%,last_name.ilike.%{name}%")
            
            if tags:
                query = query.ilike("tags", f"%{tags}%")
                
            result = query.execute()
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(
                f"Error searching people",
                error=str(e),
                name=name,
                tags=tags
            )
            raise
