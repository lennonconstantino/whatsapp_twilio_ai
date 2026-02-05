from typing import List, Optional, Dict, Any
from sqlalchemy import select, update

from src.core.database.postgres_repository import PostgresRepository
from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.repositories.interfaces import IFeatureUsageRepository


class PostgresFeatureUsageRepository(PostgresRepository[FeatureUsage], IFeatureUsageRepository):
    model = FeatureUsage

    def find_by_owner_and_feature(self, owner_id: str, feature_id: str) -> Optional[FeatureUsage]:
        stmt = select(self.model).where(
            self.model.owner_id == owner_id,
            self.model.feature_id == feature_id
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return result

    def find_all_by_owner(self, owner_id: str) -> List[FeatureUsage]:
        stmt = select(self.model).where(self.model.owner_id == owner_id)
        result = self.session.execute(stmt).scalars().all()
        return list(result)

    def increment(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        # Using atomic update
        stmt = (
            update(self.model)
            .where(
                self.model.owner_id == owner_id,
                self.model.feature_id == feature_id
            )
            .values(current_usage=self.model.current_usage + amount)
            .returning(self.model)
        )
        result = self.session.execute(stmt).scalar_one()
        self.session.commit()
        return result

    def decrement(self, owner_id: str, feature_id: str, amount: int) -> FeatureUsage:
        # Using atomic update
        stmt = (
            update(self.model)
            .where(
                self.model.owner_id == owner_id,
                self.model.feature_id == feature_id
            )
            .values(current_usage=self.model.current_usage - amount)
            .returning(self.model)
        )
        result = self.session.execute(stmt).scalar_one()
        self.session.commit()
        return result

    def upsert(self, data: Dict[str, Any]) -> FeatureUsage:
        # Handle upsert logic
        # For simplicity, check if exists then update or create
        # Ideal: use ON CONFLICT DO UPDATE
        existing = self.find_by_owner_and_feature(data["owner_id"], data["feature_id"])
        if existing:
            return self.update(existing.usage_id, data, id_column="usage_id")
        return self.create(data)
