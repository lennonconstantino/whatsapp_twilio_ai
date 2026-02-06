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

    def find_by_owner_and_feature(self, owner_id: str, feature_id: str) -> Optional[FeatureUsage]:
        try:
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE owner_id = %s AND feature_id = %s
                LIMIT 1
            """).format(table=sql.Identifier(self.table_name))
            
            result = self._execute_query(query, (owner_id, feature_id), fetch_one=True)
            
            if result:
                return self.model_class(**result)
            return None
        except Exception as e:
            logger.error("find_by_owner_and_feature_failed", owner_id=owner_id, feature_id=feature_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find feature usage for owner {owner_id}", original_error=e)

    def find_all_by_owner(self, owner_id: str) -> List[FeatureUsage]:
        try:
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE owner_id = %s
            """).format(table=sql.Identifier(self.table_name))
            
            results = self._execute_query(query, (owner_id,), fetch_all=True)
            
            return [self.model_class(**row) for row in results]
        except Exception as e:
            logger.error("find_all_by_owner_failed", owner_id=owner_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find all feature usages for owner {owner_id}", original_error=e)

    def increment(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        try:
            # Using atomic update
            query = sql.SQL("""
                UPDATE {table}
                SET current_usage = current_usage + %s
                WHERE owner_id = %s AND feature_id = %s
                RETURNING *
            """).format(table=sql.Identifier(self.table_name))
            
            result = self._execute_query(query, (amount, owner_id, feature_id), fetch_one=True, commit=True)
            
            if result:
                return self.model_class(**result)
            raise ValueError(f"Feature usage not found for owner {owner_id} and feature {feature_id}")
        except ValueError:
            raise
        except Exception as e:
            logger.error("increment_usage_failed", owner_id=owner_id, feature_id=feature_id, error=str(e))
            raise BillingRepositoryError("Failed to increment usage", original_error=e)

    def decrement(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        try:
            # Using atomic update
            query = sql.SQL("""
                UPDATE {table}
                SET current_usage = current_usage - %s
                WHERE owner_id = %s AND feature_id = %s
                RETURNING *
            """).format(table=sql.Identifier(self.table_name))
            
            result = self._execute_query(query, (amount, owner_id, feature_id), fetch_one=True, commit=True)
            
            if result:
                return self.model_class(**result)
            raise ValueError(f"Feature usage not found for owner {owner_id} and feature {feature_id}")
        except ValueError:
            raise
        except Exception as e:
            logger.error("decrement_usage_failed", owner_id=owner_id, feature_id=feature_id, error=str(e))
            raise BillingRepositoryError("Failed to decrement usage", original_error=e)

    def upsert(self, data: Dict[str, Any]) -> FeatureUsage:
        try:
            # Raw SQL upsert using ON CONFLICT (requires unique constraint on owner_id, feature_id)
            # Assuming table has UNIQUE(owner_id, feature_id)
            
            columns = list(data.keys())
            values = list(data.values())
            
            # Construct the INSERT part
            insert_query = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values})").format(
                table=sql.Identifier(self.table_name),
                fields=sql.SQL(", ").join(map(sql.Identifier, columns)),
                values=sql.SQL(", ").join(sql.Placeholder() * len(columns))
            )
            
            # Construct the ON CONFLICT part
            # DO UPDATE SET col1=EXCLUDED.col1, ...
            update_assignments = [
                sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(col))
                for col in columns if col not in ["usage_id", "created_at"] # Don't update ID or created_at
            ]
            
            upsert_query = insert_query + sql.SQL("""
                ON CONFLICT (owner_id, feature_id) 
                DO UPDATE SET {assignments}
                RETURNING *
            """).format(assignments=sql.SQL(", ").join(update_assignments))
            
            result = self._execute_query(upsert_query, tuple(values), fetch_one=True, commit=True)
            
            if result:
                return self.model_class(**result)
            raise BillingRepositoryError("Failed to upsert feature usage")
            
        except Exception as e:
            logger.error("upsert_usage_failed", error=str(e))
            raise BillingRepositoryError("Failed to upsert feature usage", original_error=e)
