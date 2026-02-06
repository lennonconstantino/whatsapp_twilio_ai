from typing import Optional

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.utils import get_logger
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.repositories.interfaces import IPlanFeatureRepository

logger = get_logger(__name__)


class PostgresPlanFeatureRepository(PostgresRepository[PlanFeature], IPlanFeatureRepository):
    model = PlanFeature
    
    def __init__(self, db):
        super().__init__(db, "plan_features", PlanFeature)

    def find_by_plan_and_feature(self, plan_id: str, feature_id: str) -> Optional[PlanFeature]:
        results = self.find_by({"plan_id": plan_id, "feature_id": feature_id}, limit=1)
        return results[0] if results else None
