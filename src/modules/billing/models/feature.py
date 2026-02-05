from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field

from src.modules.billing.enums.feature_type import FeatureType


class FeatureBase(BaseModel):
    feature_key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    feature_type: FeatureType = FeatureType.BOOLEAN
    unit: Optional[str] = None
    category: Optional[str] = None
    is_public: bool = True
    is_deprecated: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeatureCreate(FeatureBase):
    pass


class FeatureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    feature_type: Optional[FeatureType] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    is_public: Optional[bool] = None
    is_deprecated: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class Feature(FeatureBase):
    """
    Feature Catalog entity.
    """
    feature_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        return f"Feature(id={self.feature_id}, key={self.feature_key}, name={self.name}, type={self.feature_type})"
