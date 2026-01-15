
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field,  field_validator

from src.core.utils.custom_ulid import is_valid_ulid

class FeatureCreateDTO(BaseModel):
    """DTO for creating a feature."""
    owner_id: str  # ULID
    name: str
    description: Optional[str] = None
    enabled: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for owner_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"FeatureCreateDTO(owner_id={self.owner_id}, name={self.name}, enabled={self.enabled})"
