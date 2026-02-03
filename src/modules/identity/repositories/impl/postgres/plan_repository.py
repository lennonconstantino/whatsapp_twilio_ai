from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.identity.models.plan import Plan
from src.modules.identity.models.plan_feature import PlanFeature
from src.modules.identity.repositories.interfaces import IPlanRepository


class PostgresPlanRepository(PostgresRepository[Plan], IPlanRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "plans", Plan)
        self._plan_feature_repo = PostgresRepository(db, "plan_features", PlanFeature)

    def find_public_plans(self, limit: int = 100) -> List[Plan]:
        return self.find_by({"is_public": True, "active": True}, limit=limit)

    def find_by_name(self, name: str) -> Optional[Plan]:
        plans = self.find_by({"name": name}, limit=1)
        return plans[0] if plans else None

    def get_features(self, plan_id: str) -> List[PlanFeature]:
        return self._plan_feature_repo.find_by({"plan_id": plan_id}, limit=200)

