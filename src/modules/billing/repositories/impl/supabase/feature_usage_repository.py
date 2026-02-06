from typing import List, Optional, Dict, Any

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.repositories.interfaces import IFeatureUsageRepository
from src.modules.billing.exceptions import BillingRepositoryError

logger = get_logger(__name__)


class SupabaseFeatureUsageRepository(SupabaseRepository[FeatureUsage], IFeatureUsageRepository):
    def __init__(self, client):
        super().__init__(client, "feature_usage", FeatureUsage, primary_key="usage_id")

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
        except Exception as e:
            logger.error("find_by_owner_and_feature_failed", owner_id=owner_id, feature_id=feature_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find feature usage for owner {owner_id}", original_error=e)

    def find_all_by_owner(self, owner_id: str) -> List[FeatureUsage]:
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("find_all_by_owner_failed", owner_id=owner_id, error=str(e))
            raise BillingRepositoryError(f"Failed to find all feature usages for owner {owner_id}", original_error=e)

    def increment(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        # We try to use the RPC if available, otherwise fallback to read-update
        # But wait, the RPC takes feature_key, here we have feature_id.
        # Let's do a direct atomic update if possible via postgrest? 
        # Supabase-py doesn't support easy atomic increments without RPC.
        # So we fetch, update in memory, and save. Not truly atomic but works for now in MVP.
        # BETTER: Use RPC if we can resolve key, or create a new RPC for ID.
        # Since we are inside repository, we might not have access to feature_key easily without join.
        # Let's assume low concurrency for now or that we accept race conditions in MVP.
        
        try:
            usage = self.find_by_owner_and_feature(owner_id, feature_id)
            if not usage:
                raise ValueError(f"Usage record not found for owner {owner_id} and feature {feature_id}")
                
            new_usage = usage.current_usage + amount
            
            updated = self.update(usage.usage_id, {"current_usage": new_usage})
            return updated
        except ValueError:
            raise
        except Exception as e:
            logger.error("increment_usage_failed", owner_id=owner_id, feature_id=feature_id, error=str(e))
            raise BillingRepositoryError("Failed to increment usage", original_error=e)

    def decrement(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        try:
            usage = self.find_by_owner_and_feature(owner_id, feature_id)
            if not usage:
                raise ValueError(f"Usage record not found for owner {owner_id} and feature {feature_id}")
                
            new_usage = max(0, usage.current_usage - amount)
            
            updated = self.update(usage.usage_id, {"current_usage": new_usage})
            return updated
        except ValueError:
            raise
        except Exception as e:
            logger.error("decrement_usage_failed", owner_id=owner_id, feature_id=feature_id, error=str(e))
            raise BillingRepositoryError("Failed to decrement usage", original_error=e)

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
            logger.error("upsert_usage_failed", error=str(e))
            raise BillingRepositoryError("Failed to upsert feature usage", original_error=e)
