"""
Identity Service module.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.utils import get_logger
from src.modules.identity.dtos.feature_dto import FeatureCreateDTO
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.subscription import SubscriptionCreate
from src.modules.identity.models.user import User, UserRole
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.plan_service import PlanService
from src.modules.identity.services.subscription_service import \
    SubscriptionService
from src.modules.identity.services.user_service import UserService

logger = get_logger(__name__)


class IdentityService:
    """
    High-level service for identity management.
    Orchestrates operations involving both Owners and Users.
    """

    def __init__(
        self,
        owner_service: OwnerService,
        user_service: UserService,
        feature_service: FeatureService,
        subscription_service: SubscriptionService,
        plan_service: PlanService,
    ):
        """
        Initialize IdentityService.

        Args:
            owner_service: OwnerService instance
            user_service: UserService instance
            feature_service: FeatureService instance
            subscription_service: SubscriptionService instance
            plan_service: PlanService instance
        """
        self.owner_service = owner_service
        self.user_service = user_service
        self.feature_service = feature_service
        self.subscription_service = subscription_service
        self.plan_service = plan_service

    def register_organization(
        self,
        owner_data: OwnerCreateDTO,
        admin_user_data: UserCreateDTO,
        initial_features: Optional[List[str]] = None,
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

        # 1. & 2. Create Owner and Admin User Atomically via RPC
        logger.info(f"Registering new organization atomically: {owner_data.name}")

        try:
            result = self.owner_service.register_organization_atomic(
                owner_name=owner_data.name,
                owner_email=owner_data.email,
                user_auth_id=admin_user_data.auth_id,
                user_email=admin_user_data.email,
                user_first_name=admin_user_data.first_name,
                user_last_name=admin_user_data.last_name,
                user_phone=admin_user_data.phone
            )
        except Exception as e:
            logger.error(f"Atomic registration failed: {e}")
            raise e

        # Fetch created entities
        owner_id = result.get('owner_id')
        user_id = result.get('user_id')
        
        owner = self.owner_service.get_owner_by_id(owner_id)
        user = self.user_service.get_user_by_id(user_id)
        
        if not owner or not user:
             logger.error("Atomic registration succeeded but failed to fetch created entities")
             # This is a rare edge case, but we should handle it or raise
             raise Exception("Failed to fetch created organization details")

        # 3. Create initial features if provided
        if initial_features:
            logger.info(
                f"Creating {len(initial_features)} initial features for owner {owner.owner_id}"
            )
            for feature_name in initial_features:
                try:
                    feature_dto = FeatureCreateDTO(
                        owner_id=owner.owner_id,
                        name=feature_name,
                        enabled=True,
                        description=f"Initial feature: {feature_name}",
                    )
                    self.feature_service.create_feature(feature_dto)
                except Exception as e:
                    logger.error(f"Failed to create feature {feature_name}: {e}")
                    # Continue creating other features

        # 4. Create default subscription (Free Tier)
        try:
            free_plan = self.plan_service.plan_repository.find_by_name("free")
            if free_plan:
                logger.info(f"Subscribing owner {owner.owner_id} to Free plan")

                sub_create = SubscriptionCreate(
                    owner_id=owner.owner_id,
                    plan_id=free_plan.plan_id,
                    status=SubscriptionStatus.ACTIVE,
                )
                self.subscription_service.create_subscription(sub_create)
            else:
                logger.warning("Free plan not found. Skipping default subscription.")
        except Exception as e:
            logger.error(f"Failed to create default subscription: {e}")
            # We don't rollback here as the user and owner are already created.
            # The user can subscribe later.

        return owner, user

    def get_consolidated_features(self, owner_id: str) -> Dict[str, Any]:
        """
        Get consolidated features (Plan Features + Owner Overrides).

        Args:
            owner_id: Owner ID

        Returns:
            Dictionary: {feature_name: config_value}
        """
        features = {}

        # 1. Get Plan Features via Subscription
        try:
            subscription = self.subscription_service.get_active_subscription(owner_id)
            if subscription and subscription.plan_id:
                plan_features = self.plan_service.get_plan_features(
                    subscription.plan_id
                )
                for pf in plan_features:
                    features[pf.feature_name] = pf.feature_value
        except Exception as e:
            logger.error(f"Error fetching plan features for owner {owner_id}: {e}")

        # 2. Get Owner Overrides
        try:
            overrides = self.feature_service.get_enabled_features(owner_id)
            for feature in overrides:
                # Overwrite or merge? Usually overwrite for specific owner config.
                features[feature.name] = feature.config_json
        except Exception as e:
            logger.error(f"Error fetching feature overrides for owner {owner_id}: {e}")

        return features

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

        # Use consolidated features
        features = self.get_consolidated_features(owner.owner_id)

        return {"user": user, "owner": owner, "features": features}

    def validate_owner_access(self, owner_id: str) -> bool:
        """
        Check if the owner has a valid subscription to access the service.

        Args:
            owner_id: The Owner ID

        Returns:
            bool: True if access is allowed, False otherwise.
        """
        # Bypass check in development if configured
        if (
            settings.api.environment == "development"
            and settings.api.bypass_subscription_check
        ):
            logger.warning(
                f"Bypassing subscription check for owner {owner_id} (DEV MODE)"
            )
            return True

        try:
            subscription = self.subscription_service.get_active_subscription(owner_id)
            if not subscription:
                logger.warning(
                    f"Access denied for owner {owner_id}: No active subscription found."
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating access for owner {owner_id}: {e}")
            return False

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

    def update_user_profile_name(self, user_id: str, profile_name: str) -> Optional[User]:
        cleaned = (profile_name or "").strip()
        if not cleaned:
            return None
        return self.user_service.update_user(user_id, {"profile_name": cleaned})

    def clear_user_profile_name(self, user_id: str) -> Optional[User]:
        return self.user_service.update_user(user_id, {"profile_name": None})

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

    def get_active_feature(self, owner_id: str) -> Optional[Any]:
        """
        Get the active feature for an owner based on configuration.

        Args:
            owner_id: Owner ID

        Returns:
            Active Feature instance or None
        """
        return self.feature_service.get_active_feature(owner_id)

    def validate_feature_path(self, path: str) -> Dict[str, Any]:
        """
        Validate a feature path.

        Args:
            path: Feature path to validate

        Returns:
            dict with validation results for feature path
        """
        return self.feature_service.validate_feature_path(path)
