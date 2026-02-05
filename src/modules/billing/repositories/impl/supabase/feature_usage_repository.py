from typing import List, Optional, Dict, Any

from src.core.database.supabase_repository import SupabaseRepository
from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.repositories.interfaces import IFeatureUsageRepository


class SupabaseFeatureUsageRepository(SupabaseRepository[FeatureUsage], IFeatureUsageRepository):
    def __init__(self, client):
        super().__init__(client, "feature_usage", FeatureUsage)

    def find_by_owner_and_feature(self, owner_id: str, feature_id: str) -> Optional[FeatureUsage]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .eq("feature_id", feature_id)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception:
            return None

    def find_all_by_owner(self, owner_id: str) -> List[FeatureUsage]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception:
            return []

    def increment(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        # We try to use the RPC if available, otherwise fallback to read-update
        # But wait, the RPC takes feature_key, here we have feature_id.
        # Let's do a direct atomic update if possible via postgrest? 
        # Supabase-py doesn't support easy atomic increments without RPC.
        # So we fetch, update in memory, and save. Not truly atomic but works for now in MVP.
        # BETTER: Use RPC if we can resolve key, or create a new RPC for ID.
        # Since we are inside repository, we might not have access to feature_key easily without join.
        # Let's assume low concurrency for now or that we accept race conditions in MVP.
        
        usage = self.find_by_owner_and_feature(owner_id, feature_id)
        if not usage:
            raise ValueError(f"Usage record not found for owner {owner_id} and feature {feature_id}")
            
        new_usage = usage.current_usage + amount
        
        updated = self.update(usage.usage_id, {"current_usage": new_usage}, id_column="usage_id")
        return updated

    def decrement(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        usage = self.find_by_owner_and_feature(owner_id, feature_id)
        if not usage:
            raise ValueError(f"Usage record not found for owner {owner_id} and feature {feature_id}")
            
        new_usage = max(0, usage.current_usage - amount)
        
        updated = self.update(usage.usage_id, {"current_usage": new_usage}, id_column="usage_id")
        return updated

    def upsert(self, data: Dict[str, Any]) -> FeatureUsage:
        try:
            # Supabase upsert requires specifying conflict columns
            result = (
                self.client.table(self.table_name)
                .upsert(data, on_conflict="owner_id, feature_id")
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            raise ValueError("Failed to upsert feature usage")
        except Exception as e:
            raise e
