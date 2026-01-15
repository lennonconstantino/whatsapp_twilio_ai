from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from src.core.utils.custom_ulid import validate_ulid_field


class Owner(BaseModel):
    """
    Owner (tenant) entity with ULID.
    """
    owner_id: Optional[str] = None  # Changed from int to str (ULID)
    name: str
    email: str
    created_at: Optional[datetime] = None
    active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        return validate_ulid_field(v)

    def __repr__(self) -> str:
        return f"Owner(id={self.owner_id}, name={self.name}, email={self.email})"
    