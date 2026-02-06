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
        results = super().find_by({"feature_key": feature_key}, limit=1)
        return results[0] if results else None
