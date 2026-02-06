from typing import List

from src.core.database.postgres_repository import PostgresRepository
from src.core.utils import get_logger
from src.modules.billing.models.subscription_event import SubscriptionEvent
from src.modules.billing.repositories.interfaces import ISubscriptionEventRepository

logger = get_logger(__name__)


class PostgresSubscriptionEventRepository(PostgresRepository[SubscriptionEvent], ISubscriptionEventRepository):
    model = SubscriptionEvent

    def __init__(self, db):
        super().__init__(db, "subscription_events", SubscriptionEvent)

    def find_by_subscription(self, subscription_id: str) -> List[SubscriptionEvent]:
        return super().find_by_subscription(subscription_id)
