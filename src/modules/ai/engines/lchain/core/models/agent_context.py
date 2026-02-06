from typing import Any, Dict, Optional

from pydantic import BaseModel


class AgentContext(BaseModel):
    correlation_id: str
    owner_id: str
    feature: Optional[str] = None  # Feature Name associated with the agent execution
    feature_id: Optional[str] = None  # Feature ID associated with the agent execution MANDATORY (ULID)
    msg_id: Optional[str] = None  # Message ID (ULID) associated with the input
    session_id: Optional[str] = None  # Session ID (Conversation ID)
    user_input: str
    channel: str
    user: Optional[Dict[str, Any]] = None  # User information
    memory: Optional[list] = None  # List of previous messages
    additional_context: Optional[str] = (
        None  # Additional context to be used by the agent
    )
