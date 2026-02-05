from typing import List, Optional

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.billing.models.plan_version import PlanVersion
from src.modules.billing.repositories.interfaces import IPlanVersionRepository


class SupabasePlanVersionRepository(SupabaseRepository[PlanVersion], IPlanVersionRepository):
    def __init__(self, client):
        super().__init__(client, "plan_versions", PlanVersion)

    def find_by_plan(self, plan_id: str) -> List[PlanVersion]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("plan_id", plan_id)
                .order("version_number", desc=True)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception:
            return []

    def find_active_version(self, plan_id: str) -> Optional[PlanVersion]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("plan_id", plan_id)
                .eq("is_active", True)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception:
            return None
