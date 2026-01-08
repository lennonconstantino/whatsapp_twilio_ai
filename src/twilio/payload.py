from pydantic import BaseModel, Field, field_validator
from typing import Optional
import json

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

    client_receive: Optional[bool] = Field(None, alias='ClientReceive')
    
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
