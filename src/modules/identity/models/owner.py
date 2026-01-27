from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.core.utils.custom_ulid import validate_ulid_field


class OwnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    active: Optional[bool] = None


class Owner(OwnerBase):
    """
    Owner (tenant) entity with ULID.

    """

    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        return validate_ulid_field(v)

    def __repr__(self) -> str:
        return f"Owner(id={self.owner_id}, name={self.name}, email={self.email})"

    def __hash__(self) -> int:
        return hash((self.owner_id, self.name, self.email, self.active))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Owner):
            return False
        return (
            self.owner_id == other.owner_id
            and self.name == other.name
            and self.email == other.email
            and self.active == other.active
        )
