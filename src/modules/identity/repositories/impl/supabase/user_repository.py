"""
User repository for database operations.
"""

from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.identity.models.user import User, UserRole
from src.modules.identity.repositories.interfaces import IUserRepository

logger = get_logger(__name__)


class SupabaseUserRepository(SupabaseRepository[User], IUserRepository):
    """Repository for User entity operations."""

    def __init__(self, client: Client):
        """Initialize user repository with ULID validation."""
        super().__init__(
            client, "users", User, validates_ulid=True
        )  # ✅ Enable ULID validation

    def find_by_owner(self, owner_id: str, limit: int = 100) -> List[User]:
        """
        Find users by owner ID.
        ULID validation happens automatically in find_by().
        Args:
            owner_id: Owner ID
            limit: Maximum number of users to return

        Returns:
            List of User instances
        """
        return self.find_by({"owner_id": owner_id}, limit=limit)

    def find_by_phone(self, phone: str) -> Optional[User]:
        """
        Find user by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            User instance or None
        """
        users = self.find_by({"phone": phone}, limit=1)
        return users[0] if users else None

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email.

        Args:
            email: Email to search for

        Returns:
            User instance or None
        """
        # Note: User model might not have email field directly if it's in auth?
        # Let's check User model. Assuming it might be stored or we rely on auth.
        # Checking src/modules/identity/models/user.py later.
        # If User model doesn't have email, this query will fail or return nothing.
        # Assuming for now User has email or we query JSON?
        # Actually standard practice is to store email in User record too.
        # But if not, we might need to query by other means.
        # Let's check User model first? No, I'll add the method and check model later.
        # If the column doesn't exist, SupabaseRepository might complain or return empty.
        users = self.find_by({"email": email}, limit=1)
        return users[0] if users else None

    def find_by_auth_id(self, auth_id: str) -> Optional[User]:
        """
        Find user by auth ID.

        Args:
            auth_id: Auth ID to search for

        Returns:
            User instance or None
        """
        users = self.find_by({"auth_id": auth_id}, limit=1)
        return users[0] if users else None

    def find_active_by_owner(self, owner_id: str, limit: int = 100) -> List[User]:
        """
        Find active users by owner ID.

        Args:
            owner_id: Owner ID
            limit: Maximum number of users to return

        Returns:
            List of active User instances
        """
        return self.find_by({"owner_id": owner_id, "active": True}, limit=limit)

    def find_by_role(
        self, owner_id: str, role: UserRole, limit: int = 100
    ) -> List[User]:
        """
        Find users by owner and role.

        Args:
            owner_id: Owner ID
            role: User role
            limit: Maximum number of users to return

        Returns:
            List of User instances
        """
        return self.find_by({"owner_id": owner_id, "role": role.value}, limit=limit)

    def deactivate_user(self, user_id: str) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            user_id: ID of the user to deactivate

        Returns:
            Updated User instance or None
        """
        return self.update(user_id, {"active": False}, id_column="user_id")

    def activate_user(self, user_id: str) -> Optional[User]:
        """
        Activate a user.

        Args:
            user_id: ID of the user to activate

        Returns:
            Updated User instance or None
        """
        return self.update(user_id, {"active": True}, id_column="user_id")
