import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QueueMessage(BaseModel):
    """
    Represents a message in the queue.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    attempts: int = 0
    status: str = "pending"  # pending, processing, failed, completed

    # Optional metadata
    correlation_id: Optional[str] = None
    owner_id: Optional[str] = None
    error_reason: Optional[str] = None
