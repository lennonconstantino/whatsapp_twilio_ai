"""
Subscription repository for database operations.
"""
from datetime import datetime
from typing import Optional, List
from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.identity.models.subscription import Subscription
from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.core.utils import get_logger

logger = get_logger(__name__)


class SubscriptionRepository(SupabaseRepository[Subscription]):
    """Repository for Subscription entity operations."""
    
    def __init__(self, client: Client):
        """Initialize subscription repository."""
        super().__init__(client, "subscriptions", Subscription, validates_ulid=True)
    
    def find_active_by_owner(self, owner_id: str) -> Optional[Subscription]:
        """
        Find active subscription for an owner.
        
        Args:
            owner_id: ID of the owner
            
        Returns:
            Active Subscription instance or None
        """
        # Search for active subscriptions
        subs = self.find_by({"owner_id": owner_id, "status": SubscriptionStatus.ACTIVE.value}, limit=1)
        if subs:
            return subs[0]
            
        # Also check for trial
        subs = self.find_by({"owner_id": owner_id, "status": SubscriptionStatus.TRIAL.value}, limit=1)
        if subs:
            return subs[0]
            
        return None

    def cancel_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: ID of the subscription
            
        Returns:
            Updated Subscription instance or None
        """
        update_data = {
            "status": SubscriptionStatus.CANCELED.value,
            "canceled_at": datetime.utcnow().isoformat()
        }
        return self.update(subscription_id, update_data, id_column="subscription_id")
