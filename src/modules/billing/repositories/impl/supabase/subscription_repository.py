from typing import List, Optional
from datetime import datetime, timedelta

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.billing.models.subscription import Subscription
from src.modules.billing.repositories.interfaces import ISubscriptionRepository
from src.modules.billing.exceptions import BillingRepositoryError

logger = get_logger(__name__)


class SupabaseSubscriptionRepository(SupabaseRepository[Subscription], ISubscriptionRepository):
    def __init__(self, client):
        super().__init__(client, "subscriptions", Subscription, primary_key="subscription_id")

    def find_by_owner(self, owner_id: str) -> Optional[Subscription]:
        try:
            # We want the most recent or active subscription
            # Assuming one active subscription per owner for now, or finding the latest
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("find_by_owner_failed", owner_id=owner_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find subscription for owner {owner_id}", original_error=e)

    def find_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        try:
            # Check if metadata contains the stripe_subscription_id
            # PostgREST operator for jsonb containment is @> (cs in supabase-py)
            result = (
                self.client.table(self.table_name)
                .select("*")
                .contains("metadata", {"stripe_subscription_id": stripe_subscription_id})
                .limit(1)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("find_by_stripe_subscription_id_failed", stripe_subscription_id=stripe_subscription_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find subscription by stripe id {stripe_subscription_id}", original_error=e)

    def find_pending_cancellations(self) -> List[Subscription]:
        try:
            now = datetime.utcnow().isoformat()
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", "pending_cancellation")
                .lte("cancel_at", now)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("find_pending_cancellations_failed", error=str(e))
            raise BillingRepositoryError("Failed to find pending cancellations", original_error=e)

    def find_expiring_trials(self, days_before: int) -> List[Subscription]:
        try:
            target_date = (datetime.utcnow() + timedelta(days=days_before)).date().isoformat()
            # This query is tricky in simple PostgREST if we want exact day match
            # We'll fetch trialing status and filter by date range roughly
            
            start_date = datetime.utcnow().isoformat()
            end_date = (datetime.utcnow() + timedelta(days=days_before + 1)).isoformat()
            
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", "trialing")
                .gte("trial_end", start_date)
                .lte("trial_end", end_date)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("find_expiring_trials_failed", days_before=days_before, error=str(e))
            raise BillingRepositoryError("Failed to find expiring trials", original_error=e)
