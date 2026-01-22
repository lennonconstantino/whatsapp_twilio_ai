"""
Identity Service module.
"""
from typing import Optional, Tuple, Dict, Any
from src.core.utils import get_logger
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.user_service import UserService
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User, UserRole

logger = get_logger(__name__)

class IdentityService:
    """
    High-level service for identity management.
    Orchestrates operations involving both Owners and Users.
    """

    def __init__(self, owner_service: OwnerService, user_service: UserService):
        """
        Initialize IdentityService.
        
        Args:
            owner_service: OwnerService instance
            user_service: UserService instance
        """
        self.owner_service = owner_service
        self.user_service = user_service

    def register_organization(
        self, 
        owner_data: OwnerCreateDTO, 
        admin_user_data: UserCreateDTO
    ) -> Tuple[Optional[Owner], Optional[User]]:
        """
        Register a new organization (Owner) and its initial Admin User.
        
        Args:
            owner_data: Data for creating the Owner
            admin_user_data: Data for creating the initial Admin User
            
        Returns:
            Tuple containing (Owner, User)
            
        Raises:
            ValueError: If validation fails
            Exception: If creation fails
        """
        logger.info(f"Registering new organization: {owner_data.name}")
        
        # 1. Create Owner
        owner = self.owner_service.create_owner(owner_data)
        if not owner:
            logger.error("Failed to create owner")
            raise Exception("Failed to create owner")
            
        # 2. Create Admin User linked to Owner
        logger.info(f"Creating admin user for owner {owner.owner_id}")
        
        # Override owner_id to match the created owner
        user_dict = admin_user_data.model_dump()
        user_dict['owner_id'] = owner.owner_id
        user_dict['role'] = UserRole.ADMIN
        
        # Re-validate with DTO
        final_user_dto = UserCreateDTO(**user_dict)
        
        try:
            user = self.user_service.create_user(final_user_dto)
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            # Note: Transaction rollback would be handled here in a transactional system
            raise e
            
        return owner, user

    def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full context for a user (User + Owner info).
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user and owner details, or None
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return None
            
        owner = self.owner_service.get_owner_by_id(user.owner_id)
        
        return {
            "user": user,
            "owner": owner
        }
