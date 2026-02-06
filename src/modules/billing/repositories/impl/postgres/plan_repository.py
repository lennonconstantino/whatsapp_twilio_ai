from typing import List, Optional

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.utils import get_logger
from src.modules.billing.models.plan import Plan
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.repositories.interfaces import IPlanRepository

logger = get_logger(__name__)


class PostgresPlanRepository(PostgresRepository[Plan], IPlanRepository):
    model = Plan

    def __init__(self, db):
        super().__init__(db, "plans", Plan)

    def get_features(self, plan_id: str) -> List[PlanFeature]:
        return super().get_features(plan_id)
    
    def find_by_name(self, name: str) -> Optional[Plan]:
        results = self.find_by({"name": name}, limit=1)
        return results[0] if results else None

    def find_public_plans(self) -> List[Plan]:
        try:
            query = sql.SQL("""
                SELECT * FROM {table}
                WHERE is_public = true AND active = true
            """).format(table=sql.Identifier(self.table_name))
            
            results = self._execute_query(query, fetch_all=True)
            
            return [self.model_class(**row) for row in results]
        except Exception as e:
            logger.error("find_public_plans_failed", error=str(e))
            return []
