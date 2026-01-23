"""
User Service module.
"""
from typing import List, Optional
from src.core.utils import get_logger
from src.modules.identity.repositories.user_repository import UserRepository
from src.modules.identity.models.user import User, UserRole
from src.modules.identity.dtos.user_dto import UserCreateDTO

logger = get_logger(__name__)

class UserService:
    """Service for managing users."""

    def __init__(self, repository: UserRepository):
        """
        Initialize UserService.
        
        Args:
            repository: UserRepository instance
        """
        self.repository = repository

    def create_user(self, data: UserCreateDTO) -> Optional[User]:
        """
        Create a new user.
        
        Args:
            data: User creation data DTO
            
        Returns:
            Created User or None
            
        Raises:
            ValueError: If user with same phone already exists
        """
        logger.info(f"Creating user for owner {data.owner_id}")
        
        if data.phone:
            existing = self.repository.find_by_phone(data.phone)
            if existing:
                logger.warning(f"User with phone '{data.phone}' already exists")
                raise ValueError(f"User with phone '{data.phone}' already exists.")
        
        user = self.repository.create(data.model_dump())
        if user:
            logger.info(f"User created with ID: {user.user_id}")
        return user

    def get_users_by_owner(self, owner_id: str) -> List[User]:
        """
        Get all users for an owner.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            List of Users
        """
        return self.repository.find_by_owner(owner_id)
    
    def get_active_users_by_owner(self, owner_id: str) -> List[User]:
        """
        Get active users for an owner.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            List of active Users
        """
        return self.repository.find_active_by_owner(owner_id)

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """
        Find user by phone number.
        
        Args:
            phone: Phone number
            
        Returns:
            User instance or None
        """
        return self.repository.find_by_phone(phone)
        
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID (ULID)
            
        Returns:
            User instance or None
        """
        return self.repository.get_by_id(user_id)
    
    def get_users_by_role(self, owner_id: str, role: UserRole) -> List[User]:
        """
        Get users by role within an owner.
        
        Args:
            owner_id: Owner ID
            role: User role
            
        Returns:
            List of Users with the specified role
        """
        return self.repository.find_by_role(owner_id, role)

    def deactivate_user(self, user_id: str) -> Optional[User]:
        """
        Deactivate a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated User or None
        """
        logger.info(f"Deactivating user {user_id}")
        return self.repository.deactivate_user(user_id)
        
    def activate_user(self, user_id: str) -> Optional[User]:
        """
        Activate a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated User or None
        """
        logger.info(f"Activating user {user_id}")
        return self.repository.activate_user(user_id)
