from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.identity.models.feature import Feature


class PostgresFeatureRepository(PostgresRepository[Feature]):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "features", Feature)

    def find_by_owner(self, owner_id: str, limit: int = 100) -> List[Feature]:
        return self.find_by({"owner_id": owner_id}, limit=limit)

    def find_enabled_by_owner(self, owner_id: str, limit: int = 100) -> List[Feature]:
        return self.find_by({"owner_id": owner_id, "enabled": True}, limit=limit)

    def find_by_name(self, owner_id: str, name: str) -> Optional[Feature]:
        features = self.find_by({"owner_id": owner_id, "name": name}, limit=1)
        return features[0] if features else None

    def enable_feature(self, feature_id: int) -> Optional[Feature]:
        return self.update(feature_id, {"enabled": True}, id_column="feature_id")

    def disable_feature(self, feature_id: int) -> Optional[Feature]:
        return self.update(feature_id, {"enabled": False}, id_column="feature_id")

    def update_config(self, feature_id: int, config: dict) -> Optional[Feature]:
        return self.update(feature_id, {"config_json": config}, id_column="feature_id")

