from typing import List, Optional

from sqlalchemy import select

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.repositories.interfaces import IPlanVersionRepository


class PostgresPlanVersionRepository(PostgresRepository[PlanVersion], IPlanVersionRepository):
    model = PlanVersion

    def find_by_plan(self, plan_id: str) -> List[PlanVersion]:
        stmt = select(self.model).where(self.model.plan_id == plan_id)
        result = self.session.execute(stmt).scalars().all()
        return list(result)

    def find_active_version(self, plan_id: str) -> Optional[PlanVersion]:
        stmt = select(self.model).where(
            self.model.plan_id == plan_id,
            self.model.is_active == True
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result
