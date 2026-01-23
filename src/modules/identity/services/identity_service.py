"""
Identity Service module.
"""
from typing import Optional, Tuple, Dict, Any, List

from src.core.utils import get_logger
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.user_service import UserService
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.dtos.feature_dto import FeatureCreateDTO
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User, UserRole

logger = get_logger(__name__)

class IdentityService:
    """
    High-level service for identity management.
    Orchestrates operations involving both Owners and Users.
    """

    def __init__(self, owner_service: OwnerService, user_service: UserService, feature_service: FeatureService):
        """
        Initialize IdentityService.
        
        Args:
            owner_service: OwnerService instance
            user_service: UserService instance
            feature_service: FeatureService instance
        """
        self.owner_service = owner_service
        self.user_service = user_service
        self.feature_service = feature_service

    def register_organization(
        self, 
        owner_data: OwnerCreateDTO, 
        admin_user_data: UserCreateDTO,
        initial_features: Optional[List[str]] = None
    ) -> Tuple[Optional[Owner], Optional[User]]:
        """
        Register a new organization (Owner) and its initial Admin User.
        
        Args:
            owner_data: Data for creating the Owner
            admin_user_data: Data for creating the initial Admin User
            initial_features: Optional list of feature names to enable for the organization
            
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
            # Rollback: Delete the orphan owner
            if owner and owner.owner_id:
                logger.warning(f"Rolling back owner creation for {owner.owner_id} due to user creation failure")
                try:
                    self.owner_service.delete_owner(owner.owner_id)
                    logger.info(f"Successfully rolled back owner {owner.owner_id}")
                except Exception as rollback_error:
                    logger.critical(f"CRITICAL: Failed to rollback owner {owner.owner_id}: {rollback_error}")
            raise e
            
        # 3. Create initial features if provided
        if initial_features:
            logger.info(f"Creating {len(initial_features)} initial features for owner {owner.owner_id}")
            for feature_name in initial_features:
                try:
                    feature_dto = FeatureCreateDTO(
                        owner_id=owner.owner_id,
                        name=feature_name,
                        enabled=True,
                        description=f"Initial feature: {feature_name}"
                    )
                    self.feature_service.create_feature(feature_dto)
                except Exception as e:
                    logger.error(f"Failed to create feature {feature_name}: {e}")
                    # Continue creating other features
            
        return owner, user

    def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full context for a user (User + Owner info + Features).
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user, owner and features details, or None
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return None
            
        owner = self.owner_service.get_owner_by_id(user.owner_id)
        features = self.feature_service.get_enabled_features(owner.owner_id)
        
        return {
            "user": user,
            "owner": owner,
            "features": features
        }

    def check_feature_access(self, user_id: str, feature_name: str) -> bool:
        """
        Check if a user has access to a specific feature.
        
        Args:
            user_id: User ID
            feature_name: Name of the feature to check
            
        Returns:
            True if the user exists and the feature is enabled for their organization, False otherwise
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return False
            
        feature = self.feature_service.get_feature_by_name(user.owner_id, feature_name)
        return feature is not None and feature.enabled

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """
        Find user by phone number.
        
        Args:
            phone: Phone number
            
        Returns:
            User instance or None
        """
        return self.user_service.get_user_by_phone(phone)

    def get_feature_by_name(self, owner_id: str, name: str) -> Optional[Any]:
        """
        Get a specific feature by name and owner.
        
        Args:
            owner_id: Owner ID
            name: Feature name
            
        Returns:
            Feature instance or None
        """
        return self.feature_service.get_feature_by_name(owner_id, name)
    
    def validate_feature_path(self, path: str) -> Dict[str, Any]:
        """
        Validate a feature path.
        
        Args:
            path: Feature path to validate
            
        Returns:
            dict with validation results for feature path
        """
        return self.feature_service.validate_feature_path(path)
