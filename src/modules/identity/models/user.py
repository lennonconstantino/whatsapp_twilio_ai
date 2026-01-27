from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.core.utils.custom_ulid import is_valid_ulid, validate_ulid_field
from src.modules.identity.enums.user_role import UserRole
from src.modules.identity.models.owner import Owner


class UserBase(BaseModel):
    profile_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    owner_id: str
    external_auth_id: Optional[str] = None


class UserSync(BaseModel):
    """Model sync user after external auth"""

    external_auth_id: str = Field(
        ..., description="Sub or ID from external auth provider"
    )
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_name: Optional[str] = None


class UserUpdate(BaseModel):
    profile_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    active: Optional[bool] = None


class User(UserBase):
    """
    User entity with ULID.
    """

    user_id: Optional[str] = None  # (ULID)
    owner_id: str  # (ULID FK)
    auth_id: Optional[str] = (
        None  # External auth ID (e.g., sub from JWT or external auth ID)
    )
    active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """Validate ULID format for user_id."""
        return validate_ulid_field(v)

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not v:
            raise ValueError("owner_id is required")
        if not is_valid_ulid(v):
            raise ValueError(f"Invalid ULID format for owner_id: {v}")
        return v.upper()

    def __repr__(self) -> str:
        return f"User(id={self.user_id}, owner_id={self.owner_id}, role={self.role}, phone={self.phone}, email={self.email})"

    def __hash__(self) -> int:
        return hash((self.user_id, self.owner_id, self.role, self.phone, self.email))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return False
        return (
            self.user_id == other.user_id
            and self.owner_id == other.owner_id
            and self.role == other.role
            and self.phone == other.phone
            and self.email == other.email
        )


class UserWithOwner(User):
    """User com informações do Owner"""

    owner: Owner

    def __repr__(self) -> str:
        return f"UserWithOwner(id={self.user_id}, owner_id={self.owner_id}, role={self.role}, phone={self.phone}, owner={self.owner})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserWithOwner):
            return False
        return (
            self.user_id == other.user_id
            and self.owner_id == other.owner_id
            and self.role == other.role
            and self.phone == other.phone
            and self.owner == other.owner
        )

    def __hash__(self) -> int:
        return hash((self.user_id, self.owner_id, self.role, self.phone, self.owner))
