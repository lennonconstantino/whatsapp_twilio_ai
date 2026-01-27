from typing import Any, Dict, Optional

from pydantic import BaseModel


class AgentContext(BaseModel):
    correlation_id: str
    owner_id: str
    feature: Optional[str] = None  # Feature Name associated with the agent execution
    msg_id: Optional[str] = None  # Message ID (ULID) associated with the input
    user_input: str
    channel: str
    user: Optional[Dict[str, Any]] = None  # User information
    memory: Optional[list] = None  # List of previous messages
    additional_context: Optional[str] = (
        None  # Additional context to be used by the agent
    )
