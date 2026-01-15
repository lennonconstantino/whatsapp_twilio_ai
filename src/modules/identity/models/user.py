from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from src.modules.identity.enums.user_role import UserRole
from src.core.utils.custom_ulid import validate_ulid_field, is_valid_ulid

class User(BaseModel):
    """
    User entity with ULID.
    """
    user_id: Optional[str] = None  # Changed from int to str (ULID)
    owner_id: str  # Changed from int to str (ULID FK)
    profile_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER
    phone: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        """Validate ULID format for user_id."""
        return validate_ulid_field(v)
    
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
        return f"User(id={self.user_id}, owner_id={self.owner_id}, role={self.role}, phone={self.phone})"
