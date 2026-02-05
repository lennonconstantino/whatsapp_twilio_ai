from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy import select

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.subscription import Subscription
from src.modules.billing.repositories.interfaces import ISubscriptionRepository
from src.modules.billing.enums.subscription_status import SubscriptionStatus


class PostgresSubscriptionRepository(PostgresRepository[Subscription], ISubscriptionRepository):
    model = Subscription

    def find_by_owner(self, owner_id: str) -> Optional[Subscription]:
        # Usually want active or latest
        stmt = select(self.model).where(self.model.owner_id == owner_id).order_by(self.model.created_at.desc())
        result = self.session.execute(stmt).scalars().first()
        return result

    def find_pending_cancellations(self) -> List[Subscription]:
        stmt = select(self.model).where(self.model.status == SubscriptionStatus.PENDING_CANCELLATION)
        result = self.session.execute(stmt).scalars().all()
        return list(result)

    def find_expiring_trials(self, days_before: int) -> List[Subscription]:
        target_date = datetime.utcnow() + timedelta(days=days_before)
        stmt = select(self.model).where(
            self.model.status == SubscriptionStatus.TRIALING,
            self.model.trial_end <= target_date
        )
        result = self.session.execute(stmt).scalars().all()
        return list(result)
