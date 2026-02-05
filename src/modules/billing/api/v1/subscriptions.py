from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.api.dependencies import get_authenticated_user
from src.modules.identity.models.user import User
from src.modules.billing.services.subscription_service import SubscriptionService
from src.modules.billing.models.subscription import Subscription

router = APIRouter(prefix="/subscriptions", tags=["Billing Subscriptions"])

class SubscriptionCreateRequest(BaseModel):
    owner_id: str
    plan_id: str
    trial_days: Optional[int] = None
    payment_method_id: Optional[str] = None

class SubscriptionUpgradeRequest(BaseModel):
    new_plan_id: str
    triggered_by: str = "user"

class SubscriptionCancelRequest(BaseModel):
    reason: Optional[str] = None
    immediately: bool = False
    triggered_by: str = "user"

@router.post("/", response_model=Subscription, status_code=status.HTTP_201_CREATED)
@inject
def create_subscription(
    req: SubscriptionCreateRequest,
    current_user: User = Depends(get_authenticated_user),
    service: SubscriptionService = Depends(Provide[Container.billing_subscription_service])
):
    if req.owner_id != current_user.owner_id:
        raise HTTPException(status_code=403, detail="Cannot create subscription for another owner")
    try:
        return service.create_subscription(
            owner_id=req.owner_id,
            plan_id=req.plan_id,
            trial_days=req.trial_days,
            payment_method_id=req.payment_method_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subscription_id}/upgrade", response_model=Subscription)
@inject
def upgrade_subscription(
    subscription_id: str,
    req: SubscriptionUpgradeRequest,
    current_user: User = Depends(get_authenticated_user),
    service: SubscriptionService = Depends(Provide[Container.billing_subscription_service])
):
    try:
        return service.upgrade_subscription(
            subscription_id=subscription_id,
            new_plan_id=req.new_plan_id,
            triggered_by=req.triggered_by
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{subscription_id}/cancel", response_model=Subscription)
@inject
def cancel_subscription(
    subscription_id: str,
    req: SubscriptionCancelRequest,
    current_user: User = Depends(get_authenticated_user),
    service: SubscriptionService = Depends(Provide[Container.billing_subscription_service])
):
    try:
        return service.cancel_subscription(
            subscription_id=subscription_id,
            immediately=req.immediately,
            reason=req.reason,
            triggered_by=req.triggered_by
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
