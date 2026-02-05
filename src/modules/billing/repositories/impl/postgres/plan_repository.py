from typing import List, Optional

from sqlalchemy import select

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.plan import Plan
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.repositories.interfaces import IPlanRepository


class PostgresPlanRepository(PostgresRepository[Plan], IPlanRepository):
    model = Plan

    def get_features(self, plan_id: str) -> List[PlanFeature]:
        stmt = select(PlanFeature).where(PlanFeature.plan_id == plan_id)
        result = self.session.execute(stmt).scalars().all()
        return list(result)

    def find_by_name(self, name: str) -> Optional[Plan]:
        # Usually internal name or slug
        stmt = select(self.model).where(self.model.name == name)
        result = self.session.execute(stmt).scalar_one_or_none()
        return result
