from typing import List, Optional
from datetime import datetime, timedelta

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.utils import get_logger
from src.modules.billing.models.subscription import Subscription
from src.modules.billing.repositories.interfaces import ISubscriptionRepository
from src.modules.billing.enums.subscription_status import SubscriptionStatus
from src.modules.billing.exceptions import BillingRepositoryError

logger = get_logger(__name__)


class PostgresSubscriptionRepository(PostgresRepository[Subscription], ISubscriptionRepository):
    model = Subscription

    def __init__(self, db):
        super().__init__(db, "subscriptions", Subscription)

    def find_by_owner(self, owner_id: str) -> Optional[Subscription]:
        return super().find_by_owner(owner_id)

    def find_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        return super().find_by_stripe_subscription_id(stripe_subscription_id)

    def find_pending_cancellations(self) -> List[Subscription]:
        return super().find_pending_cancellations()

    def find_expiring_trials(self, days_before: int) -> List[Subscription]:
        try:
            target_date = datetime.utcnow() + timedelta(days=days_before)
            
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE status = %s AND trial_end <= %s
            """).format(table=sql.Identifier(self.table_name))
            
            results = self._execute_query(query, (SubscriptionStatus.TRIALING, target_date), fetch_all=True)
            
            return [self.model_class(**row) for row in results]
        except Exception as e:
            logger.error("find_expiring_trials_failed", days_before=days_before, error=str(e))
            raise BillingRepositoryError("Failed to find expiring trials", original_error=e)
