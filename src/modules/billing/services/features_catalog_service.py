from typing import List, Optional, Dict, Any
from datetime import datetime

from src.modules.billing.models.feature import Feature, FeatureCreate, FeatureUpdate
from src.modules.billing.enums.feature_type import FeatureType
from src.modules.billing.repositories.interfaces import IFeaturesCatalogRepository


class FeaturesCatalogService:
    """
    Manages the global feature catalog.
    """

    def __init__(self, catalog_repository: IFeaturesCatalogRepository):
        self.catalog_repo = catalog_repository

    def create_feature(
        self,
        feature_key: str,
        name: str,
        feature_type: FeatureType,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Feature:
        """
        Create a new feature in the catalog.
        """
        # Validate feature_key format (snake_case, alphanumeric + underscore)
        if not feature_key.replace('_', '').isalnum():
            raise ValueError("feature_key must be snake_case alphanumeric")

        # Check if feature_key already exists
        existing = self.catalog_repo.find_by_key(feature_key)
        if existing:
            raise ValueError(f"Feature with key '{feature_key}' already exists")

        feature_data = {
            "feature_key": feature_key,
            "name": name,
            "feature_type": feature_type.value,
            "description": description,
            "unit": unit,
            "category": category,
            "is_public": True,
            "metadata": metadata or {}
        }

        return self.catalog_repo.create(feature_data)

    def get_feature_by_key(self, feature_key: str) -> Feature:
        """Get feature by its unique key."""
        feature = self.catalog_repo.find_by_key(feature_key)
        if not feature:
            raise ValueError(f"Feature '{feature_key}' not found in catalog")
        return feature

    def get_all_features(
        self,
        category: Optional[str] = None,
        feature_type: Optional[FeatureType] = None,
        include_deprecated: bool = False
    ) -> List[Feature]:
        """
        Get all features, optionally filtered.
        """
        filters = {}

        if category:
            filters["category"] = category

        if feature_type:
            filters["feature_type"] = feature_type.value

        if not include_deprecated:
            filters["is_deprecated"] = False

        return self.catalog_repo.find_by(filters)

    def deprecate_feature(self, feature_key: str, reason: str) -> Feature:
        """Mark a feature as deprecated."""
        feature = self.get_feature_by_key(feature_key)

        metadata = feature.metadata.copy()
        metadata["deprecation_reason"] = reason
        metadata["deprecated_at"] = datetime.utcnow().isoformat()

        updated = self.catalog_repo.update(
            feature.feature_id,
            {
                "is_deprecated": True,
                "metadata": metadata
            }
        )
        return updated
