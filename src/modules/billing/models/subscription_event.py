from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionEventBase(BaseModel):
    subscription_id: str
    event_type: str
    from_plan_id: Optional[str] = None
    to_plan_id: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    triggered_by: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    reason: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionEventCreate(SubscriptionEventBase):
    pass


class SubscriptionEvent(SubscriptionEventBase):
    event_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
