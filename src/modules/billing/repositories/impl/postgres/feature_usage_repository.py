from typing import List, Optional, Dict, Any

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.utils import get_logger
from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.repositories.interfaces import IFeatureUsageRepository
from src.modules.billing.exceptions import BillingRepositoryError

logger = get_logger(__name__)


class PostgresFeatureUsageRepository(PostgresRepository[FeatureUsage], IFeatureUsageRepository):
    model = FeatureUsage

    def __init__(self, db):
        super().__init__(db, "feature_usage", FeatureUsage)

    def find_by_owner_and_feature(self, owner_id: str, feature_id: str) -> Optional[FeatureUsage]:        
        results = self.find_by({"owner_id": owner_id, "feature_id": feature_id}, limit=1)
        return results[0] if results else None

    def find_all_by_owner(self, owner_id: str) -> List[FeatureUsage]:
        return self.find_by({"owner_id": owner_id})

    def increment(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        query = sql.SQL("""
            UPDATE {table}
            SET current_usage = current_usage + %s,
                updated_at = NOW()
            WHERE owner_id = %s AND feature_id = %s
            RETURNING *
        """).format(table=self.table_identifier)
        
        result = self._execute_query(query, (amount, owner_id, feature_id), fetch_one=True, commit=True)
        if result:
            return self.model_class(**result)
        raise BillingRepositoryError(f"Usage record not found for owner {owner_id} and feature {feature_id}")

    def decrement(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        query = sql.SQL("""
            UPDATE {table}
            SET current_usage = GREATEST(0, current_usage - %s),
                updated_at = NOW()
            WHERE owner_id = %s AND feature_id = %s
            RETURNING *
        """).format(table=self.table_identifier)
        
        result = self._execute_query(query, (amount, owner_id, feature_id), fetch_one=True, commit=True)
        if result:
            return self.model_class(**result)
        raise BillingRepositoryError(f"Usage record not found for owner {owner_id} and feature {feature_id}")

    def upsert(self, data: Dict[str, Any]) -> FeatureUsage:
        columns = list(data.keys())
        values = list(data.values())
        
        update_columns = [col for col in columns if col not in ('owner_id', 'feature_id', 'usage_id', 'created_at')]
        
        if update_columns:
            set_clause = sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(k), sql.Identifier(k))
                for k in update_columns
            )
            conflict_action = sql.SQL("DO UPDATE SET {}").format(set_clause)
        else:
            conflict_action = sql.SQL("DO NOTHING")

        query = sql.SQL("""
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
            ON CONFLICT (owner_id, feature_id)
            {conflict_action}
            RETURNING *
        """).format(
            table=self.table_identifier,
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            placeholders=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
            conflict_action=conflict_action
        )
        
        result = self._execute_query(query, tuple(values), fetch_one=True, commit=True)
        
        if not result and not update_columns:
            # If DO NOTHING and row exists, we need to fetch it
            return self.find_by_owner_and_feature(data['owner_id'], data['feature_id'])
            
        return self.model_class(**result)
