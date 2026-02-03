from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.identity.models.user import User, UserRole


class PostgresUserRepository(PostgresRepository[User]):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "users", User)

    def find_by_id(self, id_value, id_column: str = "user_id") -> Optional[User]:
        return super().find_by_id(id_value, id_column=id_column)

    def find_by_owner(self, owner_id: str, limit: int = 100) -> List[User]:
        return self.find_by({"owner_id": owner_id}, limit=limit)

    def find_by_phone(self, phone: str) -> Optional[User]:
        users = self.find_by({"phone": phone}, limit=1)
        return users[0] if users else None

    def find_by_email(self, email: str) -> Optional[User]:
        users = self.find_by({"email": email}, limit=1)
        return users[0] if users else None

    def find_by_auth_id(self, auth_id: str) -> Optional[User]:
        users = self.find_by({"auth_id": auth_id}, limit=1)
        return users[0] if users else None

    def find_active_by_owner(self, owner_id: str, limit: int = 100) -> List[User]:
        return self.find_by({"owner_id": owner_id, "active": True}, limit=limit)

    def find_by_role(
        self, owner_id: str, role: UserRole, limit: int = 100
    ) -> List[User]:
        role_value = role.value if hasattr(role, "value") else role
        return self.find_by({"owner_id": owner_id, "role": role_value}, limit=limit)

    def deactivate_user(self, user_id: str) -> Optional[User]:
        return self.update(user_id, {"active": False}, id_column="user_id")

    def activate_user(self, user_id: str) -> Optional[User]:
        return self.update(user_id, {"active": True}, id_column="user_id")

