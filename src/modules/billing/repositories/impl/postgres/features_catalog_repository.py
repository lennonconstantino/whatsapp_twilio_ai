from typing import List, Optional, Dict, Any

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.feature import Feature
from src.modules.billing.repositories.interfaces import IFeaturesCatalogRepository


class PostgresFeaturesCatalogRepository(PostgresRepository[Feature], IFeaturesCatalogRepository):
    # Note: PostgresRepository uses model_class passed in __init__, or derived from Generic[T] if inspected,
    # but the current implementation requires explicitly passing it to super().__init__ which happens in DI container?
    # No, DI container calls __init__.
    # PostgresRepository.__init__ takes (db, table_name, model_class).
    # But providers.Factory(PostgresFeaturesCatalogRepository, db=...) only passes db.
    # So PostgresFeaturesCatalogRepository MUST define __init__ to pass the other args.
    
    def __init__(self, db):
        super().__init__(db, "features_catalog", Feature)

    def find_by_key(self, feature_key: str) -> Optional[Feature]:
        # Explicitly ignore 'id' column assumption from base class if any
        # But base find_by doesn't use ID.
        # Wait, the error is likely in how find_by is being called or if there's a default ID query somewhere?
        # The error log says: SELECT * FROM "features_catalog" WHERE "id" = '...'
        # This implies find_by_id was called or something similar.
        # Looking at the trace, it seems `resolve_agent_feature` calls `check_feature_access` which calls `get_feature_by_key` -> `find_by_key`.
        # `find_by_key` calls `self.find_by({"feature_key": feature_key})`.
        # PostgresRepository.find_by uses keys from filters.
        # So where is "id" coming from?
        
        # Ah, maybe something else is calling find_by_id?
        # The error log: "Error resolving agent feature for owner ... column "id" does not exist"
        # "LINE 1: SELECT * FROM "features_catalog" WHERE "id" = 'KFDWNRGK1017Q..."
        
        # Let's check `FeatureUsageService.check_feature_access` logic again.
        # It calls `catalog_service.get_feature_by_key` -> `catalog_repo.find_by_key`.
        # And `usage_repo.find_by_owner_and_feature(owner_id, feature.feature_id)`.
        
        # Wait, `feature_id` is the PK of features_catalog.
        # Is there any chance that `find_by_key` implementation in `PostgresFeaturesCatalogRepository` is somehow correct?
        # `results = self.find_by({"feature_key": feature_key}, limit=1)`
        # This generates `SELECT * FROM features_catalog WHERE feature_key = %s`.
        # This matches the code.
        
        # BUT, if `check_feature_access` calls `usage_repo.find_by_owner_and_feature`, that's on `feature_usage` table.
        # The error says `SELECT * FROM "features_catalog"`.
        
        # Let's look closer at the log:
        # `src.modules.channels.twilio.services.webhook.ai_processor ERROR Error resolving agent feature ...`
        # `LINE 1: SELECT * FROM "features_catalog" WHERE "id" = ...`
        
        # Who is querying `features_catalog` with `id`?
        # Maybe `FeatureUsage` has a relationship?
        # Or maybe the code is trying to find the feature by ID somewhere?
        
        # If I look at `PostgresRepository.find_by_id`:
        # `def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[T]:`
        # Default `id_column` is "id".
        
        # Is it possible that `TwilioWebhookAIProcessor` is calling `catalog_repo.find_by_id` somewhere?
        # Or `check_feature_access` is doing something else?
        
        # Let's search for usages of `find_by_id` on `features_catalog`.
        
        #results = self.find_by({"feature_key": feature_key}, limit=1)
        results = super().find_by({"feature_key": feature_key}, limit=1)
        return results[0] if results else None
