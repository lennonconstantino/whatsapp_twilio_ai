from datetime import datetime
from typing import Any, Optional, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from src.modules.billing.enums.billing_period import BillingPeriod
from src.modules.billing.models.plan_feature import PlanFeature


class PlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: int = Field(0, ge=0)
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    is_public: bool = True
    max_users: Optional[int] = Field(None, ge=1)
    max_projects: Optional[int] = Field(None, ge=1)
    config_json: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: Optional[int] = Field(None, ge=0)
    billing_period: Optional[BillingPeriod] = None
    is_public: Optional[bool] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_projects: Optional[int] = Field(None, ge=1)
    config_json: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class Plan(PlanBase):
    plan_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanWithFeatures(Plan):
    features: List[PlanFeature] = []
