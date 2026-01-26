from src.modules.identity.enums.user_role import UserRole

from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from src.core.utils.custom_ulid import  is_valid_ulid

class UserCreateDTO(BaseModel):
    """DTO for creating a user."""
    owner_id: str  # ULID
    profile_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER
    phone: Optional[str] = None
    auth_id: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for owner_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"UserCreateDTO(owner_id={self.owner_id}, role={self.role}, phone={self.phone})"
    