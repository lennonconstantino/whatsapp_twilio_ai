"""
Identity Service module.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.utils import get_logger
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.services.user_service import UserService

# Billing Imports
from src.modules.billing.services.subscription_service import SubscriptionService as BillingSubscriptionService
from src.modules.billing.services.feature_usage_service import FeatureUsageService as BillingFeatureService
from src.modules.billing.services.plan_service import PlanService as BillingPlanService
from src.modules.billing.enums.subscription_status import SubscriptionStatus as BillingSubscriptionStatus

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
        billing_subscription_service: BillingSubscriptionService,
        billing_feature_service: BillingFeatureService,
        billing_plan_service: BillingPlanService,
    ):
        """
        Initialize IdentityService.

        Args:
            owner_service: OwnerService instance
            user_service: UserService instance
            billing_subscription_service: Billing SubscriptionService instance
            billing_feature_service: Billing FeatureUsageService instance
            billing_plan_service: Billing PlanService instance
        """
        self.owner_service = owner_service
        self.user_service = user_service
        self.billing_subscription_service = billing_subscription_service
        self.billing_feature_service = billing_feature_service
        self.billing_plan_service = billing_plan_service

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
             raise Exception("Failed to fetch created organization details")

        # 3. Create initial features if provided
        if initial_features:
            # TODO: Implement override creation via Billing Module
            logger.warning(
                f"Initial features {initial_features} requested for owner {owner.owner_id} but not yet supported in new Billing flow."
            )

        # 4. Create default subscription (Free Tier)
        try:
            # Find Free plan by name using Billing Repo
            free_plan = self.billing_plan_service.plan_repo.find_by_name("free")
            if free_plan:
                logger.info(f"Subscribing owner {owner.owner_id} to Free plan")

                self.billing_subscription_service.create_subscription(
                    owner_id=owner.owner_id,
                    plan_id=free_plan.plan_id,
                    trial_days=None, # Free plan usually has no trial or is infinite
                    payment_method_id=None,
                    metadata={"source": "registration"}
                )
            else:
                logger.warning("Free plan not found in Billing. Skipping default subscription.")
        except Exception as e:
            logger.error(f"Failed to create default subscription: {e}")
            # We don't rollback here as the user and owner are already created.
            # The user can subscribe later.

        return owner, user

    def get_consolidated_features(self, owner_id: str) -> Dict[str, Any]:
        """
        Get consolidated features usage summary from Billing.

        Args:
            owner_id: Owner ID

        Returns:
            Dictionary: {feature_name: config_value_or_usage_info}
        """
        features = {}
        try:
            summary = self.billing_feature_service.get_usage_summary(owner_id)
            for key, usage in summary.items():
                features[key] = {
                    "limit": usage.quota_limit,
                    "usage": usage.current_usage,
                    "active": usage.is_active
                }
        except Exception as e:
            logger.error(f"Error fetching feature summary for owner {owner_id}: {e}")

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
            # Check for active subscription via Billing Repository
            subscription = self.billing_subscription_service.subscription_repo.find_by_owner(owner_id)
            
            if not subscription:
                logger.warning(
                    f"Access denied for owner {owner_id}: No subscription found."
                )
                return False
                
            # Check status
            valid_statuses = [
                BillingSubscriptionStatus.ACTIVE,
                BillingSubscriptionStatus.TRIALING,
                BillingSubscriptionStatus.PAST_DUE # Maybe allow grace period
            ]
            
            if subscription.status not in valid_statuses:
                 logger.warning(
                    f"Access denied for owner {owner_id}: Subscription status is {subscription.status}."
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
            feature_name: Name of the feature (key) to check

        Returns:
            True if the user exists and the feature is enabled/within quota, False otherwise
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return False

        try:
            result = self.billing_feature_service.check_feature_access(
                owner_id=user.owner_id,
                feature_key=feature_name
            )
            return result.allowed
        except Exception as e:
            logger.error(f"Error checking feature access for {feature_name}: {e}")
            return False

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
