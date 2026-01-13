"""
Updated domain models with ULID support.

This file shows how to update the domain.py models to support ULID primary keys.
"""
from datetime import datetime
import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, field_validator

from .enums import (
    ConversationStatus,
    MessageOwner,
    MessageType,
    MessageDirection,
    UserRole
)
from src.utils.custom_ulid import validate_ulid_field, is_valid_ulid


class Owner(BaseModel):
    """
    Owner (tenant) entity with ULID.
    """
    owner_id: Optional[str] = None  # Changed from int to str (ULID)
    name: str
    email: str
    created_at: Optional[datetime] = None
    active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        return validate_ulid_field(v)

    def __repr__(self) -> str:
        return f"Owner(id={self.owner_id}, name={self.name}, email={self.email})"


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


class Feature(BaseModel):
    """
    Feature entity.
    Note: Keeping feature_id as int for non-sensitive internal use.
    Can be migrated to ULID later if needed.
    """
    feature_id: Optional[int] = None  # Keeping as int
    owner_id: str  # Changed to ULID
    name: str
    description: Optional[str] = None
    enabled: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

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
        return f"Feature(id={self.feature_id}, owner_id={self.owner_id}, name={self.name}, enabled={self.enabled})"


class TwilioAccount(BaseModel):
    """
    Twilio Account entity.
    Note: Keeping tw_account_id as int for non-sensitive internal use.
    """
    tw_account_id: Optional[int] = None  # Keeping as int
    owner_id: str  # Changed to ULID
    account_sid: str
    auth_token: str
    phone_numbers: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

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
        return f"TwilioAccount(id={self.tw_account_id}, owner_id={self.owner_id}, account_sid={self.account_sid})"


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
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    @field_validator('conv_id')
    @classmethod
    def validate_conv_id(cls, v):
        """Validate ULID format for conv_id."""
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
    
    @field_validator('user_id')
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
        if not self.expires_at:
            return False
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now_utc > exp

    def __repr__(self) -> str:
        return (
            f"Conversation(id={self.conv_id}, owner_id={self.owner_id}, "
            f"from={self.from_number}, to={self.to_number}, status={self.status})"
        )
    
    def close_conversation(self, reason: ConversationStatus, closing_message: Optional[str] = None):
        """Close the conversation with a specific reason."""
        from datetime import timezone
        self.status = reason
        self.ended_at = datetime.now(timezone.utc)
        # TODO: Add logic to update conversation context with closing message
        # if closing_message:
        #     self.closed_by_message = closing_message            


class Message(BaseModel):
    """
    Message entity with ULID.
    """
    msg_id: Optional[str] = None  # Changed from int to str (ULID)
    conv_id: str  # Changed to ULID
    owner_id: str  # Added: ULID (denormalized from conversation)
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

    @field_validator('msg_id')
    @classmethod
    def validate_msg_id(cls, v):
        """Validate ULID format for msg_id."""
        return validate_ulid_field(v)
    
    @field_validator('conv_id')
    @classmethod
    def validate_conv_id(cls, v):
        """Validate ULID format for conv_id."""
        if not v:
            raise ValueError('conv_id is required')
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for conv_id: {v}')
        return v.upper()

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
        return (
            f"Message(id={self.msg_id}, conv_id={self.conv_id}, owner_id={self.owner_id}, "
            f"direction={self.direction}, owner={self.message_owner}, type={self.message_type})"
        )


class AIResult(BaseModel):
    """
    AI Result entity with ULID.
    """
    ai_result_id: Optional[str] = None  # Changed from int to str (ULID)
    msg_id: str  # Changed to ULID
    feature_id: int  # Keeping as int
    result_json: Dict[str, Any]
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator('ai_result_id')
    @classmethod
    def validate_ai_result_id(cls, v):
        """Validate ULID format for ai_result_id."""
        return validate_ulid_field(v)
    
    @field_validator('msg_id')
    @classmethod
    def validate_msg_id(cls, v):
        """Validate ULID format for msg_id."""
        if not v:
            raise ValueError('msg_id is required')
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for msg_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"AIResult(id={self.ai_result_id}, msg_id={self.msg_id}, feature_id={self.feature_id})"


# ============================================================================
# DTOs (Data Transfer Objects) - Updated for ULID
# ============================================================================

class ConversationCreateDTO(BaseModel):
    """DTO for creating a conversation."""
    owner_id: str  # ULID
    from_number: str
    to_number: str
    user_id: Optional[str] = None  # ULID
    channel: str = "whatsapp"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('owner_id', 'user_id')
    @classmethod
    def validate_ulids(cls, v, info):
        """Validate ULID format."""
        if v is None and info.field_name == 'user_id':
            return None
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for {info.field_name}: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return (
            f"ConversationCreateDTO(owner_id={self.owner_id}, from={self.from_number}, "
            f"to={self.to_number}, channel={self.channel})"
        )


class MessageCreateDTO(BaseModel):
    """DTO for creating a message."""
    conv_id: str  # ULID
    owner_id: str  # ULID
    from_number: str
    to_number: str
    body: str
    direction: MessageDirection = MessageDirection.INBOUND
    message_owner: MessageOwner = MessageOwner.USER
    message_type: MessageType = MessageType.TEXT
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(use_enum_values=True)

    @field_validator('conv_id')
    @classmethod
    def validate_conv_id(cls, v):
        """Validate ULID format for conv_id."""
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for conv_id: {v}')
        return v.upper()

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for owner_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return (
            f"MessageCreateDTO(conv_id={self.conv_id}, owner_id={self.owner_id}, "
            f"direction={self.direction}, owner={self.message_owner}, type={self.message_type})"
        )


class OwnerCreateDTO(BaseModel):
    """DTO for creating an owner."""
    name: str
    email: str

    def __repr__(self) -> str:
        return f"OwnerCreateDTO(name={self.name}, email={self.email})"


class UserCreateDTO(BaseModel):
    """DTO for creating a user."""
    owner_id: str  # ULID
    profile_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER
    phone: Optional[str] = None
    
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


class FeatureCreateDTO(BaseModel):
    """DTO for creating a feature."""
    owner_id: str  # ULID
    name: str
    description: Optional[str] = None
    enabled: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for owner_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"FeatureCreateDTO(owner_id={self.owner_id}, name={self.name}, enabled={self.enabled})"


class TwilioAccountCreateDTO(BaseModel):
    """DTO for creating a Twilio account."""
    owner_id: str  # ULID
    account_sid: str
    auth_token: str
    phone_numbers: List[str] = Field(default_factory=list)

    @field_validator('owner_id')
    @classmethod
    def validate_owner_id(cls, v):
        """Validate ULID format for owner_id."""
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for owner_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"TwilioAccountCreateDTO(owner_id={self.owner_id}, account_sid={self.account_sid})"


# Additional utility classes

class TwilioWebhookResponseDTO(BaseModel):
    """Response model for Twilio webhook."""
    success: bool
    message: str
    conv_id: Optional[str] = None  # ULID
    msg_id: Optional[str] = None  # ULID

    @field_validator('conv_id', 'msg_id')
    @classmethod
    def validate_ids(cls, v):
        """Validate ULID format for IDs."""
        return validate_ulid_field(v)

    def __repr__(self) -> str:
        return f"TwilioWebhookResponseDTO(success={self.success}, conv_id={self.conv_id}, msg_id={self.msg_id})"
    
class TwilioWhatsAppPayload(BaseModel):
    
    message_sid: str = Field(..., alias='MessageSid')
    account_sid: str = Field(..., alias='AccountSid') # Owner
    
    body: str = Field(..., alias='Body')
    message_type: Optional[str] = Field(default="text", alias="MessageType")
    
    from_number: str = Field(..., alias='From')
    wa_id: Optional[str] = Field(default=None, alias="WaId")
    profile_name: str = Field(default="Unknown", alias="ProfileName")
    
    to_number: str = Field(..., alias='To')
    
    num_media: int = Field(..., alias='NumMedia')
    num_segments: int = Field(..., alias='NumSegments')
    
    sms_status: str = Field(..., alias='SmsStatus')
    api_version: str = Field(..., alias='ApiVersion')
    channel_metadata: Optional[dict] = Field(None, alias='ChannelMetadata')

    media_url: Optional[str] = Field(None, alias='MediaUrl0') # Getting the URL of the file
    media_content_type: Optional[str] = Field(None, alias='MediaContentType0')  # Getting the extension for the file

    date_created: Optional[str] = Field(None, alias='DateCreated')

    to_country: Optional[str] = Field(None,alias='ToCountry')
    to_state: Optional[str] = Field(None,alias='ToState')
    to_city: Optional[str] = Field(None,alias='ToCity')
    from_city: Optional[str] = Field(None,alias='FromCity')
    from_zip: Optional[str] = Field(None,alias='FromZip')
    to_zip: Optional[str] = Field(None,alias='ToZip')
    from_country: Optional[str] = Field(None,alias='FromCountry')

    local_sender: Optional[bool] = Field(None, alias='LocalSender')
    
    # Validador para converter string JSON em dict
    @field_validator('channel_metadata', mode='before')
    @classmethod
    def parse_channel_metadata(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v
    
    # Validador para converter strings numéricas em int
    @field_validator('num_media', 'num_segments', mode='before')
    @classmethod
    def convert_to_int(cls, v):
        if isinstance(v, str):
            return int(v)
        return v
    
    class Config:
        populate_by_name = True

    def __repr__(self) -> str:
        return (
            f"TwilioWhatsAppPayload(message_sid={self.message_sid}, "
            f"from={self.from_number}, to={self.to_number}, type={self.message_type})"
        )
