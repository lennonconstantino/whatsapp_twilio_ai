
from typing import Any, Dict, Optional
from pydantic import BaseModel


class AgentContext(BaseModel):
    correlation_id: str    
    owner_id: str
    user_input: str
    channel: str
    user: Optional[Dict[str, Any]] = None # User information
    memory: Optional[list] = None # List of previous messages
    additional_context: Optional[str] = None # Additional context to be used by the agent
    