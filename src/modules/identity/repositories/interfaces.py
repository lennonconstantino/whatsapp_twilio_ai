from typing import Any, Dict, List, Optional, Protocol

from src.core.database.interface import IRepository
from src.modules.identity.models.feature import Feature
from src.modules.identity.models.owner import Owner
from src.modules.identity.models.plan import Plan
from src.modules.identity.models.plan_feature import PlanFeature
from src.modules.identity.models.subscription import Subscription
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


class IPlanRepository(IRepository[Plan], Protocol):
    """Interface for Plan repository."""

    def find_public_plans(self, limit: int = 100) -> List[Plan]:
        """Find all public and active plans."""
        ...

    def find_by_name(self, name: str) -> Optional[Plan]:
        """Find plan by unique name."""
        ...

    def get_features(self, plan_id: str) -> List[PlanFeature]:
        """Get features for a plan."""
        ...

    def add_feature(
        self, plan_id: str, name: str, value: Dict[str, Any]
    ) -> Optional[PlanFeature]:
        """Add a feature to a plan."""
        ...


class ISubscriptionRepository(IRepository[Subscription], Protocol):
    """Interface for Subscription repository."""

    def find_active_by_owner(self, owner_id: str) -> Optional[Subscription]:
        """Find active subscription for an owner."""
        ...

    def cancel_subscription(self, subscription_id: str, owner_id: str) -> Optional[Subscription]:
        """Cancel a subscription."""
        ...


class IFeatureRepository(IRepository[Feature], Protocol):
    """Interface for Feature repository."""

    def find_by_owner(self, owner_id: str, limit: int = 100) -> List[Feature]:
        """Find features by owner ID."""
        ...

    def find_enabled_by_owner(self, owner_id: str, limit: int = 100) -> List[Feature]:
        """Find enabled features by owner ID."""
        ...

    def find_by_name(self, owner_id: str, name: str) -> Optional[Feature]:
        """Find feature by owner and name."""
        ...

    def enable_feature(self, feature_id: int) -> Optional[Feature]:
        """Enable a feature."""
        ...

    def disable_feature(self, feature_id: int) -> Optional[Feature]:
        """Disable a feature."""
        ...

    def update_config(self, feature_id: int, config: dict) -> Optional[Feature]:
        """Update feature configuration."""
        ...
