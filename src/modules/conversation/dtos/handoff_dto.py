from typing import Optional
from pydantic import BaseModel

class HandoffRequestDTO(BaseModel):
    """Request model for initiating handoff."""
    reason: Optional[str] = "user_request"

class HandoffAssignDTO(BaseModel):
    """Request model for assigning an agent."""
    agent_id: str

class HandoffReleaseDTO(BaseModel):
    """Request model for releasing control back to bot."""
    reason: Optional[str] = "agent_release"
