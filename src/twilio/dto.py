
from typing import Optional
from pydantic import Field

class MessageInfo:
    message_input: str = Field(..., alias='MessageInput')
    message_output: str = Field(..., alias='MessageOutput')
    type: str = Field(..., alias='Type')
    path: Optional[str] = Field(..., alias='Path')
