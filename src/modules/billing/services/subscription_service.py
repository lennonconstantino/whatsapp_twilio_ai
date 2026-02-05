from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from src.modules.billing.models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate
from src.modules.billing.enums.subscription_status import SubscriptionStatus
from src.modules.billing.services.plan_service import PlanService
from src.modules.billing.services.feature_usage_service import FeatureUsageService
from src.modules.billing.repositories.interfaces import (
    ISubscriptionRepository,
    ISubscriptionEventRepository
)


class SubscriptionService:
    """
    Manages tenant subscriptions with proper lifecycle.
    """

    def __init__(
        self,
        subscription_repo: ISubscriptionRepository,
        plan_service: PlanService,
        feature_usage_service: FeatureUsageService,
        event_repo: ISubscriptionEventRepository,
        logger=None
    ):
        self.subscription_repo = subscription_repo
        self.plan_service = plan_service
        self.feature_usage_service = feature_usage_service
        self.event_repo = event_repo
        self.logger = logger

    def create_subscription(
        self,
        owner_id: str,
        plan_id: str,
        trial_days: Optional[int] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Subscription:
        """
        Create subscription and initialize feature usage.
        """
        # 1. Validate plan
        plan = self.plan_service.get_plan(plan_id)
        if not plan or not plan.active:
            raise ValueError(f"Plan {plan_id} not found or inactive")

        # 2. Create subscription
        now = datetime.now(timezone.utc)
        
        subscription_data = {
            "owner_id": owner_id,
            "plan_id": plan_id,
            "status": SubscriptionStatus.TRIALING if trial_days else SubscriptionStatus.ACTIVE,
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),  # TODO: based on plan
            "metadata": metadata or {}
        }

        if trial_days:
            subscription_data["trial_start"] = now
            subscription_data["trial_end"] = now + timedelta(days=trial_days)

        subscription = self.subscription_repo.create(subscription_data)

        # 3. Get plan features
        plan_features = self.plan_service.get_plan_features(plan_id)

        # 4. Initialize feature usage
        self.feature_usage_service.initialize_features_for_tenant(
            owner_id=owner_id,
            plan_features=plan_features
        )

        # 5. Log event
        self._log_event(
            subscription_id=subscription.subscription_id,
            event_type="created",
            to_plan_id=plan_id,
            to_status=subscription.status.value,
            triggered_by="system",
            metadata={
                "trial_days": trial_days,
                "payment_method_id": payment_method_id
            }
        )

        if self.logger:
            self.logger.info(
                f"Subscription created: subscription_id={subscription.subscription_id}, "
                f"owner={owner_id}, plan={plan_id}"
            )

        return subscription

    def upgrade_subscription(
        self,
        subscription_id: str,
        new_plan_id: str,
        triggered_by: str
    ) -> Subscription:
        """
        Upgrade to higher plan (immediate).
        """
        # Get current subscription
        subscription = self.subscription_repo.find_by_id(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        old_plan_id = subscription.plan_id

        # Validate new plan
        new_plan = self.plan_service.get_plan(new_plan_id)
        if not new_plan:
            raise ValueError(f"Plan {new_plan_id} not found")

        # Update subscription
        updated_subscription = self.subscription_repo.update(
            subscription_id,
            {
                "plan_id": new_plan_id,
                "updated_at": datetime.now(timezone.utc)
            }
        )

        # Get new plan features
        new_plan_features = self.plan_service.get_plan_features(new_plan_id)

        # Update feature usage quotas
        self.feature_usage_service.initialize_features_for_tenant(
            owner_id=subscription.owner_id,
            plan_features=new_plan_features
        )

        # Log event
        self._log_event(
            subscription_id=subscription_id,
            event_type="upgraded",
            from_plan_id=old_plan_id,
            to_plan_id=new_plan_id,
            triggered_by=triggered_by
        )

        return updated_subscription

    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False,
        reason: Optional[str] = None,
        triggered_by: str = "user"
    ) -> Subscription:
        """
        Cancel subscription.
        """
        subscription = self.subscription_repo.find_by_id(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        now = datetime.now(timezone.utc)

        if immediately:
            # Cancel immediately
            updated_subscription = self.subscription_repo.update(
                subscription_id,
                {
                    "status": SubscriptionStatus.CANCELED,
                    "canceled_at": now,
                    "cancellation_reason": reason
                }
            )
            event_type = "canceled"
        else:
            # Schedule cancellation at period end
            updated_subscription = self.subscription_repo.update(
                subscription_id,
                {
                    "status": SubscriptionStatus.PENDING_CANCELLATION,
                    "cancel_at": subscription.current_period_end,
                    "cancellation_reason": reason
                }
            )
            event_type = "cancellation_scheduled"

        # Log event
        self._log_event(
            subscription_id=subscription_id,
            event_type=event_type,
            from_status=subscription.status.value,
            to_status=updated_subscription.status.value,
            triggered_by=triggered_by,
            reason=reason,
            metadata={"immediately": immediately}
        )

        return updated_subscription

    def _log_event(
        self,
        subscription_id: str,
        event_type: str,
        from_plan_id: Optional[str] = None,
        to_plan_id: Optional[str] = None,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        triggered_by: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a subscription event."""
        event_data = {
            "subscription_id": subscription_id,
            "event_type": event_type,
            "from_plan_id": from_plan_id,
            "to_plan_id": to_plan_id,
            "from_status": from_status,
            "to_status": to_status,
            "triggered_by": triggered_by,
            "reason": reason,
            "metadata": metadata or {}
        }

        return self.event_repo.create(event_data)
