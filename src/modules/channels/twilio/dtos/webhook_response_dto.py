from pydantic import BaseModel, field_validator

from src.core.utils.custom_ulid import validate_ulid_field


class TwilioWebhookResponseDTO(BaseModel):
    """Response model for Twilio webhook."""

    success: bool
    message: str
    conv_id: str | None = None  # ULID
    msg_id: str | None = None  # ULID

    @field_validator("conv_id", "msg_id")
    @classmethod
    def validate_ids(cls, v):
        """Validate ULID format for IDs."""
        return validate_ulid_field(v)

    def __repr__(self) -> str:
        return f"TwilioWebhookResponseDTO(success={self.success}, conv_id={self.conv_id}, msg_id={self.msg_id})"
