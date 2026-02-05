from typing import Optional

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.billing.models.feature import Feature
from src.modules.billing.repositories.interfaces import IFeaturesCatalogRepository


class SupabaseFeaturesCatalogRepository(SupabaseRepository[Feature], IFeaturesCatalogRepository):
    def __init__(self, client):
        super().__init__(client, "features_catalog", Feature, primary_key="feature_id")

    def find_by_key(self, feature_key: str) -> Optional[Feature]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("feature_key", feature_key)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception:
            return None
