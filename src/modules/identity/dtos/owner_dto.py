from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OwnerCreateDTO(BaseModel):
    """DTO for creating an owner."""

    name: str
    email: str

    def __repr__(self) -> str:
        return f"OwnerCreateDTO(name={self.name}, email={self.email})"


class OwnerUpdateDTO(BaseModel):
    """DTO for updating an owner."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    active: Optional[bool] = None

    def __repr__(self) -> str:
        return f"OwnerUpdateDTO(name={self.name}, email={self.email}, active={self.active})"
