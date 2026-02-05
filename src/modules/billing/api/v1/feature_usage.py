from typing import Dict, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.billing.services.feature_usage_service import FeatureUsageService

router = APIRouter(prefix="/feature-usage", tags=["Billing Feature Usage"])

class FeatureAccessResultDTO(BaseModel):
    allowed: bool
    reason: str
    current_usage: int = 0
    quota_limit: Optional[int] = None
    percentage_used: float = 0.0
    feature_id: Optional[str] = None
    owner_id: Optional[str] = None
    is_approaching_limit: bool
    is_critical: bool

class FeatureUsageSummaryDTO(BaseModel):
    feature_key: str
    feature_name: str
    current_usage: int
    quota_limit: Optional[int]
    percentage_used: float
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    is_active: bool
    is_override: bool

@router.get("/{owner_id}/summary", response_model=Dict[str, FeatureUsageSummaryDTO])
@inject
def get_usage_summary(
    owner_id: str,
    service: FeatureUsageService = Depends(Provide[Container.feature_usage_service])
):
    # Service returns Dict[str, dataclass]. FastAPI/Pydantic can often handle this,
    # but explicit conversion might be needed if dataclass isn't perfectly aligned or if properties are involved.
    # The dataclass in service has properties/methods? No, FeatureUsageSummary is simple dataclass.
    # FeatureAccessResult has properties.
    
    # For FeatureUsageSummary, it's a simple dataclass, so it should be fine.
    return service.get_usage_summary(owner_id)

@router.get("/{owner_id}/check/{feature_key}", response_model=FeatureAccessResultDTO)
@inject
def check_feature_access(
    owner_id: str,
    feature_key: str,
    service: FeatureUsageService = Depends(Provide[Container.feature_usage_service])
):
    result = service.check_feature_access(owner_id, feature_key)
    # result is a dataclass with properties is_approaching_limit and is_critical.
    # Pydantic doesn't automatically serialize properties unless configured.
    # We might need to construct the DTO explicitly.
    
    return FeatureAccessResultDTO(
        allowed=result.allowed,
        reason=result.reason,
        current_usage=result.current_usage,
        quota_limit=result.quota_limit,
        percentage_used=result.percentage_used,
        feature_id=result.feature_id,
        owner_id=result.owner_id,
        is_approaching_limit=result.is_approaching_limit,
        is_critical=result.is_critical
    )
