
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from src.modules.identity.enums.subscription_status import SubscriptionStatus
from src.modules.identity.models.plan import Plan


class SubscriptionBase(BaseModel):
    status: SubscriptionStatus = SubscriptionStatus.TRIAL
    expires_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    config_json: dict[str, Any] = Field(default_factory=dict)


class SubscriptionCreate(SubscriptionBase):
    owner_id: str
    plan_id: str


class SubscriptionUpdate(BaseModel):
    plan_id: Optional[str] = None
    status: Optional[SubscriptionStatus] = None
    expires_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    config_json: Optional[dict[str, Any]] = None


class Subscription(SubscriptionBase):
    subscription_id: str
    owner_id: str
    plan_id: str
    started_at: datetime
    canceled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        return f"Subscription(subscription_id={self.subscription_id}, owner_id={self.owner_id}, plan_id={self.plan_id}, status={self.status}, expires_at={self.expires_at}, trial_ends_at={self.trial_ends_at}, config_json={self.config_json}, started_at={self.started_at}, canceled_at={self.canceled_at}, created_at={self.created_at}, updated_at={self.updated_at})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Subscription):
            return False
        return self.subscription_id == other.subscription_id
    
    def __hash__(self) -> int:
        return hash(self.subscription_id)


class SubscriptionWithPlan(Subscription):
    """Subscription com informações do Plan"""
    plan: Plan
    
    def __repr__(self) -> str:
        return f"SubscriptionWithPlan(subscription_id={self.subscription_id}, owner_id={self.owner_id}, plan_id={self.plan_id}, status={self.status}, expires_at={self.expires_at}, trial_ends_at={self.trial_ends_at}, config_json={self.config_json}, started_at={self.started_at}, canceled_at={self.canceled_at}, created_at={self.created_at}, updated_at={self.updated_at}, plan={self.plan})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubscriptionWithPlan):
            return False
        return self.subscription_id == other.subscription_id
    
    def __hash__(self) -> int:
        return hash(self.subscription_id)
    