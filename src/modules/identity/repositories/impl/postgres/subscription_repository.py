from datetime import datetime
from typing import Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.subscription import Subscription
from src.modules.identity.repositories.interfaces import ISubscriptionRepository


class PostgresSubscriptionRepository(
    PostgresRepository[Subscription], ISubscriptionRepository
):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "subscriptions", Subscription)

    def find_active_by_owner(self, owner_id: str) -> Optional[Subscription]:
        subs = self.find_by(
            {"owner_id": owner_id, "status": SubscriptionStatus.ACTIVE.value},
            limit=1,
        )
        if subs:
            return subs[0]

        subs = self.find_by(
            {"owner_id": owner_id, "status": SubscriptionStatus.TRIAL.value},
            limit=1,
        )
        return subs[0] if subs else None

    def cancel_subscription(self, subscription_id: str) -> Optional[Subscription]:
        update_data = {
            "status": SubscriptionStatus.CANCELED.value,
            "canceled_at": datetime.utcnow().isoformat(),
        }
        return self.update(subscription_id, update_data, id_column="subscription_id")

