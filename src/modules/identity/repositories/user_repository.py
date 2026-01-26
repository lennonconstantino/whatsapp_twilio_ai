"""
User repository for database operations.
"""
from typing import Optional, List
from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.identity.models.user import User, UserRole
from src.core.utils import get_logger

logger = get_logger(__name__)


class UserRepository(SupabaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self, client: Client):
        """Initialize user repository with ULID validation."""
        super().__init__(client, "users", User, validates_ulid=True)  # ✅ Enable ULID validation
    
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
        self,
        owner_id: str,
        role: UserRole,
        limit: int = 100
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
        return self.find_by(
            {"owner_id": owner_id, "role": role.value},
            limit=limit
        )
    
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
