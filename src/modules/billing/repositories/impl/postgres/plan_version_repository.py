from typing import List, Optional

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.utils import get_logger
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.repositories.interfaces import IPlanVersionRepository

logger = get_logger(__name__)


class PostgresPlanVersionRepository(PostgresRepository[PlanVersion], IPlanVersionRepository):
    model = PlanVersion

    def __init__(self, db):
        super().__init__(db, "plan_versions", PlanVersion)

    def find_by_plan(self, plan_id: str) -> List[PlanVersion]:
        return self.find_by({"plan_id": plan_id})

    def find_active_version(self, plan_id: str) -> Optional[PlanVersion]:
        results = self.find_by({"plan_id": plan_id, "is_active": True}, limit=1)
        return results[0] if results else None
