from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.services.subscription_service import SubscriptionService
from src.modules.identity.models.subscription import Subscription, SubscriptionCreate

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/owner/{owner_id}", response_model=Subscription)
@inject
def get_owner_subscription(
    owner_id: str,
    subscription_service: SubscriptionService = Depends(Provide[Container.subscription_service]),
):
    """Get active subscription for an owner."""
    subscription = subscription_service.get_active_subscription(owner_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active subscription not found"
        )
    return subscription


@router.post("/", response_model=Subscription, status_code=status.HTTP_201_CREATED)
@inject
def create_subscription(
    subscription_data: SubscriptionCreate,
    subscription_service: SubscriptionService = Depends(Provide[Container.subscription_service]),
):
    """Subscribe owner to a plan."""
    try:
        return subscription_service.create_subscription(subscription_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{subscription_id}/cancel", response_model=Subscription)
@inject
def cancel_subscription(
    subscription_id: str,
    subscription_service: SubscriptionService = Depends(Provide[Container.subscription_service]),
):
    """Cancel a subscription."""
    subscription = subscription_service.cancel_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return subscription
