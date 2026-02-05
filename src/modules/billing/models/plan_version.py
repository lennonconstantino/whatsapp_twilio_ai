from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field

from src.modules.billing.enums.billing_period import BillingPeriod


class PlanVersionBase(BaseModel):
    plan_id: str
    version_number: int
    price_cents: int
    billing_period: BillingPeriod
    max_users: Optional[int] = None
    max_projects: Optional[int] = None
    config_json: Dict[str, Any] = Field(default_factory=dict)
    effective_from: datetime = Field(default_factory=datetime.utcnow)
    effective_until: Optional[datetime] = None
    is_active: bool = True
    change_reason: Optional[str] = None
    changed_by: Optional[str] = None
    change_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanVersionCreate(PlanVersionBase):
    pass


class PlanVersion(PlanVersionBase):
    version_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
