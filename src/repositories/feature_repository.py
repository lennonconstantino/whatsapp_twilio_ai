"""
Feature repository for database operations.
"""
from typing import Optional, List
from supabase import Client

from .base import BaseRepository
from ..models import Feature
from ..utils import get_logger

logger = get_logger(__name__)


class FeatureRepository(BaseRepository[Feature]):
    """Repository for Feature entity operations."""
    
    def __init__(self, client: Client):
        """Initialize feature repository."""
        super().__init__(client, "features", Feature)
    
    def find_by_owner(self, owner_id: int, limit: int = 100) -> List[Feature]:
        """
        Find features by owner ID.
        
        Args:
            owner_id: Owner ID
            limit: Maximum number of features to return
            
        Returns:
            List of Feature instances
        """
        return self.find_by({"owner_id": owner_id}, limit=limit)
    
    def find_enabled_by_owner(self, owner_id: int, limit: int = 100) -> List[Feature]:
        """
        Find enabled features by owner ID.
        
        Args:
            owner_id: Owner ID
            limit: Maximum number of features to return
            
        Returns:
            List of enabled Feature instances
        """
        return self.find_by(
            {"owner_id": owner_id, "enabled": True},
            limit=limit
        )
    
    def find_by_name(self, owner_id: int, name: str) -> Optional[Feature]:
        """
        Find feature by owner and name.
        
        Args:
            owner_id: Owner ID
            name: Feature name
            
        Returns:
            Feature instance or None
        """
        features = self.find_by({"owner_id": owner_id, "name": name}, limit=1)
        return features[0] if features else None
    
    def enable_feature(self, feature_id: int) -> Optional[Feature]:
        """
        Enable a feature.
        
        Args:
            feature_id: Feature ID
            
        Returns:
            Updated Feature instance or None
        """
        return self.update(feature_id, {"enabled": True}, id_column="feature_id")
    
    def disable_feature(self, feature_id: int) -> Optional[Feature]:
        """
        Disable a feature.
        
        Args:
            feature_id: Feature ID
            
        Returns:
            Updated Feature instance or None
        """
        return self.update(feature_id, {"enabled": False}, id_column="feature_id")
    
    def update_config(
        self,
        feature_id: int,
        config: dict
    ) -> Optional[Feature]:
        """
        Update feature configuration.
        
        Args:
            feature_id: Feature ID
            config: New configuration
            
        Returns:
            Updated Feature instance or None
        """
        return self.update(
            feature_id,
            {"config_json": config},
            id_column="feature_id"
        )
