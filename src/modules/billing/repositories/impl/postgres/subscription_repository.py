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

    def find_by_owner(self, owner_id: str) -> Optional[Subscription]:
        try:
            # Usually want active or latest
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE owner_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """).format(table=sql.Identifier(self.table_name))

            result = self._execute_query(query, (owner_id,), fetch_one=True)
            
            if result:
                return self.model_class(**result)
            return None
        except Exception as e:
            logger.error("find_by_owner_failed", owner_id=owner_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find subscription for owner {owner_id}", original_error=e)

    def find_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        try:
            # JSONB query for Postgres: metadata @> '{"stripe_subscription_id": "..."}'
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE metadata @> %s::jsonb
                LIMIT 1
            """).format(table=sql.Identifier(self.table_name))
            
            import json
            param = json.dumps({"stripe_subscription_id": stripe_subscription_id})
            
            result = self._execute_query(query, (param,), fetch_one=True)
            
            if result:
                return self.model_class(**result)
            return None
        except Exception as e:
            logger.error("find_by_stripe_subscription_id_failed", stripe_subscription_id=stripe_subscription_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find subscription by stripe id {stripe_subscription_id}", original_error=e)

    def find_pending_cancellations(self) -> List[Subscription]:
        try:
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE status = %s
            """).format(table=sql.Identifier(self.table_name))
            
            results = self._execute_query(query, (SubscriptionStatus.PENDING_CANCELLATION,), fetch_all=True)
            
            return [self.model_class(**row) for row in results]
        except Exception as e:
            logger.error("find_pending_cancellations_failed", error=str(e))
            raise BillingRepositoryError("Failed to find pending cancellations", original_error=e)

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
