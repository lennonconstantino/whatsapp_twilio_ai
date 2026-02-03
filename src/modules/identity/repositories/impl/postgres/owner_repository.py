from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.identity.models.owner import Owner


class PostgresOwnerRepository(PostgresRepository[Owner]):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "owners", Owner)

    def find_by_id(self, id_value, id_column: str = "owner_id") -> Optional[Owner]:
        return super().find_by_id(id_value, id_column=id_column)

    def create_owner(self, name: str, email: str) -> Optional[Owner]:
        data = {"name": name, "email": email, "active": True}
        return self.create(data)

    def find_by_email(self, email: str) -> Optional[Owner]:
        owners = self.find_by({"email": email}, limit=1)
        return owners[0] if owners else None

    def find_active_owners(self, limit: int = 100) -> List[Owner]:
        return self.find_by({"active": True}, limit=limit)

    def deactivate_owner(self, owner_id: str) -> Optional[Owner]:
        return self.update(owner_id, {"active": False}, id_column="owner_id")

    def activate_owner(self, owner_id: str) -> Optional[Owner]:
        return self.update(owner_id, {"active": True}, id_column="owner_id")

