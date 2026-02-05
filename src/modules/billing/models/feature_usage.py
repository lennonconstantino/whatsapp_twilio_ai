from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class FeatureUsageBase(BaseModel):
    owner_id: str
    feature_id: str
    current_usage: int = 0
    quota_limit: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    last_reset_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_override: bool = False
    override_reason: Optional[str] = None
    override_by: Optional[str] = None
    override_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeatureUsageCreate(FeatureUsageBase):
    pass


class FeatureUsageUpdate(BaseModel):
    current_usage: Optional[int] = None
    quota_limit: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    last_reset_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_override: Optional[bool] = None
    override_reason: Optional[str] = None
    override_by: Optional[str] = None
    override_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class FeatureUsage(FeatureUsageBase):
    usage_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
