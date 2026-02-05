from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class PlanFeatureBase(BaseModel):
    plan_id: str
    feature_id: str
    is_enabled: bool = True
    quota_limit: Optional[int] = None
    config_value: Dict[str, Any] = Field(default_factory=dict)
    display_order: Optional[int] = None
    is_highlighted: bool = False
    description: Optional[str] = None


class PlanFeatureCreate(PlanFeatureBase):
    pass


class PlanFeatureUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    quota_limit: Optional[int] = None
    config_value: Optional[Dict[str, Any]] = None
    display_order: Optional[int] = None
    is_highlighted: Optional[bool] = None
    description: Optional[str] = None


class PlanFeature(PlanFeatureBase):
    plan_feature_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
