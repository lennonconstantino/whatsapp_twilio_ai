from typing import Optional

from sqlalchemy import select

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.repositories.interfaces import IPlanFeatureRepository


class PostgresPlanFeatureRepository(PostgresRepository[PlanFeature], IPlanFeatureRepository):
    model = PlanFeature

    def find_by_plan_and_feature(self, plan_id: str, feature_id: str) -> Optional[PlanFeature]:
        stmt = select(self.model).where(
            self.model.plan_id == plan_id,
            self.model.feature_id == feature_id
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result
