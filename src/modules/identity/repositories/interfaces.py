from typing import Any, Dict, List, Optional, Protocol

from src.core.database.interface import IRepository
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User, UserRole


class IOwnerRepository(IRepository[Owner], Protocol):
    """Interface for Owner repository."""

    def create_owner(self, name: str, email: str) -> Optional[Owner]:
        """Create a new owner."""
        ...

    def find_by_email(self, email: str) -> Optional[Owner]:
        """Find owner by email."""
        ...

    def find_active_owners(self, limit: int = 100) -> List[Owner]:
        """Find all active owners."""
        ...

    def deactivate_owner(self, owner_id: str) -> Optional[Owner]:
        """Deactivate an owner."""
        ...

    def activate_owner(self, owner_id: str) -> Optional[Owner]:
        """Activate an owner."""
        ...

    def register_organization_atomic(
        self,
        owner_name: str,
        owner_email: str,
        user_auth_id: str,
        user_email: str,
        user_first_name: str,
        user_last_name: str,
        user_phone: str,
    ) -> Dict[str, str]:
        """Register owner and admin user atomically via RPC."""
        ...


class IUserRepository(IRepository[User], Protocol):
    """Interface for User repository."""

    def find_by_owner(self, owner_id: str, limit: int = 100) -> List[User]:
        """Find users by owner ID."""
        ...

    def find_by_phone(self, phone: str) -> Optional[User]:
        """Find user by phone number."""
        ...

    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        ...

    def find_by_auth_id(self, auth_id: str) -> Optional[User]:
        """Find user by auth ID."""
        ...

    def find_active_by_owner(self, owner_id: str, limit: int = 100) -> List[User]:
        """Find active users by owner ID."""
        ...

    def find_by_role(
        self, owner_id: str, role: UserRole, limit: int = 100
    ) -> List[User]:
        """Find users by owner and role."""
        ...

    def deactivate_user(self, user_id: str) -> Optional[User]:
        """Deactivate a user."""
        ...

    def activate_user(self, user_id: str) -> Optional[User]:
        """Activate a user."""
        ...
