from datetime import datetime
from typing import Optional

from psycopg2 import sql

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

    def cancel_subscription(self, subscription_id: str, owner_id: str) -> Optional[Subscription]:
        update_data = {
            "status": SubscriptionStatus.CANCELED.value,
            "canceled_at": datetime.utcnow().isoformat(),
        }
        
        # Custom SQL update to check owner_id
        set_clauses = [
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in update_data.keys()
        ]
        
        query = sql.SQL("UPDATE {} SET {} WHERE {} = %s AND {} = %s RETURNING *").format(
            sql.Identifier(self.table_name),
            sql.SQL(", ").join(set_clauses),
            sql.Identifier("subscription_id"),
            sql.Identifier("owner_id")
        )
        
        # Params: values + subscription_id + owner_id
        params = tuple(update_data.values()) + (subscription_id, owner_id)
        
        result = self._execute_query(query, params, fetch_one=True, commit=True)
        
        if result:
            return self.model_class(**result)
        return None

