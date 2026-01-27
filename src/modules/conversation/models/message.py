from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.utils.custom_ulid import is_valid_ulid, validate_ulid_field
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType


class Message(BaseModel):
    """
    Message entity with ULID.
    """

    msg_id: Optional[str] = None  # Changed from int to str (ULID)
    conv_id: str  # Changed to ULID
    owner_id: str  # Added: ULID (denormalized from conversation)
    correlation_id: Optional[str] = None  # Trace ID
    from_number: str
    to_number: str
    body: str
    direction: MessageDirection = MessageDirection.INBOUND
    timestamp: Optional[datetime] = None
    sent_by_ia: bool = False
    message_owner: MessageOwner = MessageOwner.USER
    message_type: MessageType = MessageType.TEXT
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("msg_id")
    @classmethod
    def validate_msg_id(cls, v):
        """Validate ULID format for msg_id."""
        return validate_ulid_field(v)

    @field_validator("conv_id")
    @classmethod
    def validate_conv_id(cls, v):
        """Validate ULID format for conv_id."""
        if not v:
            raise ValueError("conv_id is required")
        if not is_valid_ulid(v):
            raise ValueError(f"Invalid ULID format for conv_id: {v}")
        return v.upper()

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
        return (
            f"Message(id={self.msg_id}, conv_id={self.conv_id}, owner_id={self.owner_id}, "
            f"direction={self.direction}, owner={self.message_owner}, type={self.message_type})"
        )
