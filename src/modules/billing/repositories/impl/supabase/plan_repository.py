from typing import List, Optional

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.billing.models.plan import Plan
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.repositories.interfaces import IPlanRepository


class SupabasePlanRepository(SupabaseRepository[Plan], IPlanRepository):
    def __init__(self, client):
        super().__init__(client, "plans", Plan)

    def get_features(self, plan_id: str) -> List[PlanFeature]:
        try:
            # Join plan_features table
            result = (
                self.client.table("plan_features")
                .select("*")
                .eq("plan_id", plan_id)
                .execute()
            )
            return [PlanFeature(**item) for item in result.data]
        except Exception:
            return []

    def find_by_name(self, name: str) -> Optional[Plan]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("name", name)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception:
            return None
    
    def find_public_plans(self) -> List[Plan]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("is_public", True)
                .eq("active", True)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception:
            return []
