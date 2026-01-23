
from datetime import datetime
import json
from typing import Optional,  List
from pydantic import BaseModel, Field, ConfigDict, field_validator


from src.core.utils.custom_ulid import is_valid_ulid

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
