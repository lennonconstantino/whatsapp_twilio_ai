from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    Interaction, InteractionCreate
)
from src.modules.ai.engines.lchain.feature.relationships.repositories.interaction_repository import InteractionRepository

class PostgresInteractionRepository(PostgresRepository[Interaction], InteractionRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "interaction", Interaction)

    def create_from_schema(self, interaction: InteractionCreate) -> Optional[Interaction]:
        return self.create(interaction.model_dump())
    
    def search(self, person_id: Optional[int] = None, channel: Optional[str] = None, type_: Optional[str] = None) -> List[Interaction]:
        query = "SELECT * FROM interaction WHERE 1=1"
        params = []
        
        if person_id is not None:
            query += " AND person_id = %s"
            params.append(person_id)
        if channel:
            query += " AND channel = %s"
            params.append(channel)
        if type_:
            query += " AND type = %s"
            params.append(type_)
            
        query += " ORDER BY date DESC"
        
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                if not rows:
                    return []
                cols = [d[0] for d in cur.description]
                return [self.model_class(**dict(zip(cols, r))) for r in rows]
            finally:
                cur.close()
