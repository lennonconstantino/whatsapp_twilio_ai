from typing import Optional

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.billing.models.plan_feature import PlanFeature
from src.modules.billing.repositories.interfaces import IPlanFeatureRepository


class SupabasePlanFeatureRepository(SupabaseRepository[PlanFeature], IPlanFeatureRepository):
    def __init__(self, client):
        super().__init__(client, "plan_features", PlanFeature)

    def find_by_plan_and_feature(self, plan_id: str, feature_id: str) -> Optional[PlanFeature]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("plan_id", plan_id)
                .eq("feature_id", feature_id)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception:
            return None
