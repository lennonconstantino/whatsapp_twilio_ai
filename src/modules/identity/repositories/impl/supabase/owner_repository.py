"""
Owner repository for database operations.
"""

from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.identity.models.owner import Owner
from src.modules.identity.repositories.interfaces import IOwnerRepository

logger = get_logger(__name__)


class SupabaseOwnerRepository(SupabaseRepository[Owner], IOwnerRepository):
    """Repository for Owner entity operations."""

    def __init__(self, client: Client):
        """Initialize owner repository."""
        super().__init__(
            client, "owners", Owner, validates_ulid=True
        )  # ✅ Enable ULID validation

    def create_owner(self, name: str, email: str) -> Optional[Owner]:
        """
        Create a new owner.

        Args:
            name: Owner name
            email: Owner email

        Returns:
            Created Owner instance or None
        """
        data = {"name": name, "email": email, "active": True}
        return self.create(data)

    def find_by_email(self, email: str) -> Optional[Owner]:
        """
        Find owner by email.

        Args:
            email: Email to search for

        Returns:
            Owner instance or None
        """
        owners = self.find_by({"email": email}, limit=1)
        return owners[0] if owners else None

    def find_active_owners(self, limit: int = 100) -> List[Owner]:
        """
        Find all active owners.

        Args:
            limit: Maximum number of owners to return

        Returns:
            List of active Owner instances
        """
        return self.find_by({"active": True}, limit=limit)

    def deactivate_owner(self, owner_id: str) -> Optional[Owner]:
        """
        Deactivate an owner.

        Args:
            owner_id: ID of the owner to deactivate

        Returns:
            Updated Owner instance or None
        """
        return self.update(owner_id, {"active": False}, id_column="owner_id")

    def activate_owner(self, owner_id: str) -> Optional[Owner]:
        """
        Activate an owner.

        Args:
            owner_id: ID of the owner to activate

        Returns:
            Updated Owner instance or None
        """
        return self.update(owner_id, {"active": True}, id_column="owner_id")
