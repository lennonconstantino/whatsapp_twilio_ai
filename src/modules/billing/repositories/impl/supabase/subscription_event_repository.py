from typing import List

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.billing.models.subscription_event import SubscriptionEvent
from src.modules.billing.repositories.interfaces import ISubscriptionEventRepository


class SupabaseSubscriptionEventRepository(SupabaseRepository[SubscriptionEvent], ISubscriptionEventRepository):
    def __init__(self, client):
        super().__init__(client, "subscription_events", SubscriptionEvent, primary_key="event_id")

    def find_by_subscription(self, subscription_id: str) -> List[SubscriptionEvent]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("subscription_id", subscription_id)
                .order("created_at", desc=True)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception:
            return []
