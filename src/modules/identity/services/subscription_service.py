"""
Subscription service for managing owner subscriptions.
"""

from typing import Optional

from src.core.utils import get_logger
from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.subscription import (Subscription,
                                                      SubscriptionCreate,
                                                      SubscriptionUpdate)
from src.modules.identity.repositories.interfaces import (IPlanRepository,
                                                          ISubscriptionRepository)

logger = get_logger(__name__)


class SubscriptionService:
    """Service for managing subscriptions."""

    def __init__(
        self,
        subscription_repository: ISubscriptionRepository,
        plan_repository: IPlanRepository,
    ):
        self.subscription_repository = subscription_repository
        self.plan_repository = plan_repository

    def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> Optional[Subscription]:
        """
        Create a new subscription (subscribe owner to plan).

        Args:
            subscription_data: Subscription creation data

        Returns:
            Created Subscription instance or None
        """
        logger.info(
            f"Creating subscription for owner: {subscription_data.owner_id} to plan: {subscription_data.plan_id}"
        )

        # Verify plan exists
        plan = self.plan_repository.find_by_id(
            subscription_data.plan_id, id_column="plan_id"
        )
        if not plan:
            raise ValueError(f"Plan not found: {subscription_data.plan_id}")

        # Check if owner already has active subscription
        active_sub = self.subscription_repository.find_active_by_owner(
            subscription_data.owner_id
        )
        if active_sub:
            # Logic to handle existing subscription (e.g., cancel old one, or upgrade)
            # We cancel the old one first to enforce "one active subscription" rule.
            logger.info(
                f"Owner {subscription_data.owner_id} already has an active subscription: {active_sub.subscription_id}. Cancelling it."
            )
            self.cancel_subscription(active_sub.subscription_id, active_sub.owner_id)

        data = subscription_data.model_dump()
        # Default status is TRIAL from model, or we can set based on plan logic
        return self.subscription_repository.create(data)

    def cancel_subscription(self, subscription_id: str, owner_id: str) -> Optional[Subscription]:
        """
        Cancel a subscription.

        Args:
            subscription_id: ID of the subscription
            owner_id: ID of the owner

        Returns:
            Updated Subscription instance or None
        """
        logger.info(f"Canceling subscription: {subscription_id} for owner {owner_id}")
        return self.subscription_repository.cancel_subscription(subscription_id, owner_id)

    def get_active_subscription(self, owner_id: str) -> Optional[Subscription]:
        """
        Get active subscription for owner.

        Args:
            owner_id: ID of the owner

        Returns:
            Active Subscription instance or None
        """
        return self.subscription_repository.find_active_by_owner(owner_id)
