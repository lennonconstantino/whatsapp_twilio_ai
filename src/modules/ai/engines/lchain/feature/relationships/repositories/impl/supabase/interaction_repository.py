from typing import List, Optional
from src.core.database.supabase_repository import SupabaseRepository
from src.core.database.interface import IDatabaseSession
from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.feature.relationships.models.models import Interaction, InteractionCreate
from src.modules.ai.engines.lchain.feature.relationships.repositories.interaction_repository import InteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.utils import prepare_data_for_db

logger = get_logger(__name__)

class SupabaseInteractionRepository(SupabaseRepository[Interaction], InteractionRepository):
    """Supabase implementation of InteractionRepository"""

    def __init__(self, client: IDatabaseSession):
        super().__init__(
            client=client,
            table_name="interaction",
            model_class=Interaction,
            validates_ulid=False,
        )

    def create_from_schema(self, interaction: InteractionCreate) -> Optional[Interaction]:
        """Cria interaction a partir do schema Pydantic"""
        data = prepare_data_for_db(interaction.model_dump())
        return self.create(data)
    
    def search(self, person_id: Optional[int] = None, channel: Optional[str] = None, type_: Optional[str] = None) -> List[Interaction]:
        """Busca interações com filtros"""
        try:
            query = self.client.table(self.table_name).select("*")
            
            if person_id is not None:
                query = query.eq("person_id", person_id)
            if channel:
                query = query.eq("channel", channel)
            if type_:
                query = query.eq("type", type_)
                
            query = query.order("date", desc=True)
            result = query.execute()
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(f"Error searching interactions", error=str(e))
            raise
