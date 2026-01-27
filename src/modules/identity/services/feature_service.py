"""
Feature Service module.
"""

from typing import Any, Dict, List, Optional

from src.core.utils import get_logger
from src.modules.identity.dtos.feature_dto import FeatureCreateDTO
from src.modules.identity.helpers.validates import PathValidator
from src.modules.identity.models.feature import Feature
from src.modules.identity.repositories.interfaces import IFeatureRepository

logger = get_logger(__name__)


class FeatureService:
    """Service for managing features."""

    def __init__(self, repository: IFeatureRepository):
        """
        Initialize FeatureService.

        Args:
            repository: FeatureRepository instance
        """
        self.repository = repository

    def create_feature(self, data: FeatureCreateDTO) -> Optional[Feature]:
        """
        Create a new feature.

        Args:
            data: Feature creation data DTO

        Returns:
            Created Feature or None

        Raises:
            ValueError: If feature with same name already exists for owner
        """
        logger.info(f"Creating feature '{data.name}' for owner {data.owner_id}")

        existing = self.repository.find_by_name(data.owner_id, data.name)
        if existing:
            logger.warning(
                f"Feature '{data.name}' already exists for owner {data.owner_id}"
            )
            raise ValueError(f"Feature '{data.name}' already exists for this owner.")

        feature = self.repository.create(data.model_dump())
        logger.info(f"Feature created with ID: {feature.feature_id}")
        return feature

    def get_features_by_owner(self, owner_id: str) -> List[Feature]:
        """
        Get all features for an owner.

        Args:
            owner_id: Owner ID

        Returns:
            List of Features
        """
        return self.repository.find_by_owner(owner_id)

    def get_enabled_features(self, owner_id: str) -> List[Feature]:
        """
        Get only enabled features for an owner.

        Args:
            owner_id: Owner ID

        Returns:
            List of enabled Features
        """
        return self.repository.find_enabled_by_owner(owner_id)

    def get_feature_by_name(self, owner_id: str, name: str) -> Optional[Feature]:
        """
        Get a specific feature by name and owner.

        Args:
            owner_id: Owner ID
            name: Feature name

        Returns:
            Feature instance or None
        """
        return self.repository.find_by_name(owner_id, name)

    def toggle_feature(self, feature_id: int, enabled: bool) -> Optional[Feature]:
        """
        Enable or disable a feature.

        Args:
            feature_id: Feature ID
            enabled: True to enable, False to disable

        Returns:
            Updated Feature or None
        """
        logger.info(f"Setting feature {feature_id} enabled status to {enabled}")
        if enabled:
            return self.repository.enable_feature(feature_id)
        return self.repository.disable_feature(feature_id)

    def update_configuration(
        self, feature_id: int, config: Dict[str, Any]
    ) -> Optional[Feature]:
        """
        Update feature configuration.

        Args:
            feature_id: Feature ID
            config: New configuration dictionary

        Returns:
            Updated Feature or None
        """
        logger.info(f"Updating configuration for feature {feature_id}")
        return self.repository.update_config(feature_id, config)

    def validate_feature_path(self, path: str) -> Dict[str, any]:
        """
        Validate a feature path.

        Args:
            path: Feature path to validate

        Returns:
            dict with validation results for feature path
        """
        return PathValidator.validate_and_check_next_directory(path)
