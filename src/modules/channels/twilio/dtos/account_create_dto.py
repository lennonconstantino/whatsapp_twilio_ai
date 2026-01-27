from typing import List

from pydantic import BaseModel, Field, field_validator

from src.core.utils.custom_ulid import is_valid_ulid


class TwilioAccountCreateDTO(BaseModel):
    """DTO for creating a Twilio account."""

    owner_id: str  # ULID
    account_sid: str
    auth_token: str
    phone_numbers: List[str] = Field(default_factory=list)

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f"Invalid ULID format for owner_id: {v}")
        return v.upper()

    def __repr__(self) -> str:
        return f"TwilioAccountCreateDTO(owner_id={self.owner_id}, account_sid={self.account_sid})"
