from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    Person, PersonCreate, PersonUpdate
)
from src.modules.ai.engines.lchain.feature.relationships.repositories.person_repository import PersonRepository

class PostgresPersonRepository(PostgresRepository[Person], PersonRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "person", Person)

    def create_from_schema(self, person: PersonCreate) -> Optional[Person]:
        return self.create(person.model_dump())

    def update_from_schema(
        self, person_id: int, person: PersonUpdate
    ) -> Optional[Person]:
        data = person.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(person_id)
        return self.update(person_id, data)

    def search_by_name_or_tags(self, name: Optional[str] = None, tags: Optional[str] = None) -> List[Person]:
        query = "SELECT * FROM person WHERE 1=1"
        params = []
        
        if name:
            query += " AND (first_name ILIKE %s OR last_name ILIKE %s)"
            params.extend([f"%{name}%", f"%{name}%"])
            
        if tags:
            query += " AND tags ILIKE %s"
            params.append(f"%{tags}%")
            
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
