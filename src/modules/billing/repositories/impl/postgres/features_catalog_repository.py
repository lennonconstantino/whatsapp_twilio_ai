from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.feature import Feature
from src.modules.billing.repositories.interfaces import IFeaturesCatalogRepository


class PostgresFeaturesCatalogRepository(PostgresRepository[Feature], IFeaturesCatalogRepository):
    model = Feature

    def find_by_key(self, feature_key: str) -> Optional[Feature]:
        stmt = select(self.model).where(self.model.feature_key == feature_key)
        result = self.session.execute(stmt).scalar_one_or_none()
        return result
