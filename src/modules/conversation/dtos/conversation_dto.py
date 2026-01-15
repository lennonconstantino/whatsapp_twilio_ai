"""
Updated domain models with ULID support.

This file shows how to update the domain.py models to support ULID primary keys.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from src.core.utils.custom_ulid import is_valid_ulid

class ConversationCreateDTO(BaseModel):
    """DTO for creating a conversation."""
    owner_id: str  # ULID
    from_number: str
    to_number: str
    user_id: Optional[str] = None  # ULID
    channel: str = "whatsapp"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('owner_id', 'user_id')
    @classmethod
    def validate_ulids(cls, v, info):
        """Validate ULID format."""
        if v is None and info.field_name == 'user_id':
            return None
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for {info.field_name}: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return (
            f"ConversationCreateDTO(owner_id={self.owner_id}, from={self.from_number}, "
            f"to={self.to_number}, channel={self.channel})"
        )
