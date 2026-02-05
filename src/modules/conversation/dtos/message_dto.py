"""
Updated domain models with ULID support.

This file shows how to update the domain.py models to support ULID primary keys.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.utils.custom_ulid import is_valid_ulid
from src.modules.conversation.enums import (MessageDirection, MessageOwner,
                                            MessageType)


class MessageCreateDTO(BaseModel):
    """DTO for creating a message."""

    conv_id: str  # ULID
    owner_id: str  # ULID
    correlation_id: Optional[str] = None  # Trace ID
    from_number: str
    to_number: str
    body: str
    direction: MessageDirection = MessageDirection.INBOUND
    message_owner: MessageOwner = MessageOwner.USER
    message_type: MessageType = MessageType.TEXT
    sent_by_ia: bool = False
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("conv_id")
    @classmethod
    def validate_conv_id(cls, v):
        """Validate ULID format for conv_id."""
        if not is_valid_ulid(v):
            raise ValueError(f"Invalid ULID format for conv_id: {v}")
        return v.upper()

    @field_validator("owner_id")
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f"Invalid ULID format for owner_id: {v}")
        return v.upper()

    def __repr__(self) -> str:
        return (
            f"MessageCreateDTO(conv_id={self.conv_id}, owner_id={self.owner_id}, "
            f"direction={self.direction}, owner={self.message_owner}, type={self.message_type})"
        )
