from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.utils.custom_ulid import is_valid_ulid, validate_ulid_field
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus


class Conversation(BaseModel):
    """
    Conversation entity with ULID.
    """

    conv_id: Optional[str] = None  # Changed from int to str (ULID)
    owner_id: str  # Changed to ULID
    user_id: Optional[str] = None  # Changed to ULID
    from_number: str
    to_number: str
    status: ConversationStatus = ConversationStatus.PENDING
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    channel: Optional[str] = "whatsapp"
    phone_number: Optional[str] = None
    agent_id: Optional[str] = None
    handoff_at: Optional[datetime] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1  # Optimistic Locking

    model_config = ConfigDict(from_attributes=True, use_enum_values=True, extra="ignore")

    @field_validator("conv_id")
    @classmethod
    def validate_conv_id(cls, v):
        """Validate ULID format for conv_id."""
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

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """Validate ULID format for user_id."""
        return validate_ulid_field(v)

    def is_active(self) -> bool:
        """Check if conversation is active."""
        status = ConversationStatus(self.status)
        return status.is_active()

    def is_paused(self) -> bool:
        """Check if conversation is paused."""
        status = ConversationStatus(self.status)
        return status.is_paused()

    def is_closed(self) -> bool:
        """Check if conversation is closed."""
        status = ConversationStatus(self.status)
        return status.is_closed()

    def can_receive_messages(self) -> bool:
        """Check if conversation can receive messages."""
        status = ConversationStatus(self.status)
        return status.can_receive_messages()

    def is_expired(self) -> bool:
        """Check if conversation has expired."""
        if self.is_closed():
            return False

        if not self.expires_at:
            return False
        from datetime import timezone

        now_utc = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now_utc > exp

    def is_idle(self, minutes: int) -> bool:
        """Check if conversation is idle."""
        if self.is_closed():
            return False

        # Use updated_at or fallback to started_at
        last_activity = self.updated_at or self.started_at
        if not last_activity:
            return False

        from datetime import timedelta, timezone

        now_utc = datetime.now(timezone.utc)
        threshold = now_utc - timedelta(minutes=minutes)

        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        return last_activity < threshold

    def close_conversation(
        self, reason: ConversationStatus, closing_message: Optional[str] = None
    ):
        """Close the conversation with a specific reason."""
        from datetime import timezone

        self.status = reason
        self.ended_at = datetime.now(timezone.utc)
        # TODO: Add logic to update conversation context with closing message
        # if closing_message:
        #     self.closed_by_message = closing_message

    def __repr__(self) -> str:
        return (
            f"Conversation(id={self.conv_id}, owner_id={self.owner_id}, "
            f"from={self.from_number}, to={self.to_number}, status={self.status})"
        )
