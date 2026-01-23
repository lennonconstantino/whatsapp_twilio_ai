"""
Twilio Result Models.
"""
from typing import Optional
from pydantic import BaseModel, Field

class TwilioMessageResult(BaseModel):
    """
    Result object for Twilio message sending operations.
    Replaces generic dictionaries for better type safety.
    """
    sid: str
    status: str
    to: str
    from_number: str = Field(..., alias="from")
    body: str
    direction: str
    num_media: int = 0
    error_code: Optional[int] = None
    error_message: Optional[str] = None

    model_config = {
        "populate_by_name": True
    }
