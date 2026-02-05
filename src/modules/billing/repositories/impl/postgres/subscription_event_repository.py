from typing import List

from sqlalchemy import select

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.subscription_event import SubscriptionEvent
from src.modules.billing.repositories.interfaces import ISubscriptionEventRepository


class PostgresSubscriptionEventRepository(PostgresRepository[SubscriptionEvent], ISubscriptionEventRepository):
    model = SubscriptionEvent

    def find_by_subscription(self, subscription_id: str) -> List[SubscriptionEvent]:
        stmt = select(self.model).where(self.model.subscription_id == subscription_id).order_by(self.model.created_at.desc())
        result = self.session.execute(stmt).scalars().all()
        return list(result)
