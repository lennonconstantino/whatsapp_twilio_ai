"""
Updated domain models with ULID support.

This file shows how to update the domain.py models to support ULID primary keys.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

from src.core.utils.custom_ulid import is_valid_ulid

class Feature(BaseModel):
    """
    Feature entity.
    Note: Keeping feature_id as int for non-sensitive internal use.
    Can be migrated to ULID later if needed.
    """
    feature_id: Optional[int] = None  # Keeping as int
    owner_id: str  # Changed to ULID
    name: str
    description: Optional[str] = None
    enabled: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not v:
            raise ValueError('owner_id is required')
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for owner_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"Feature(id={self.feature_id}, owner_id={self.owner_id}, name={self.name}, enabled={self.enabled})"

