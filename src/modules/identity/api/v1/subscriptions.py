from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.modules.identity.services.subscription_service import SubscriptionService
from src.modules.identity.services.user_service import UserService
from src.modules.identity.models.subscription import Subscription, SubscriptionCreate
from src.modules.identity.models.user import UserRole

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/current", response_model=Subscription)
@inject
def get_current_subscription(
    x_auth_id: str = Header(..., alias="X-Auth-ID"),
    subscription_service: SubscriptionService = Depends(Provide[Container.subscription_service]),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """Get active subscription for the current user's organization."""
    user = user_service.get_user_by_auth_id(x_auth_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    subscription = subscription_service.get_active_subscription(user.owner_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active subscription not found"
        )
    return subscription


@router.get("/owner/{owner_id}", response_model=Subscription)
@inject
def get_owner_subscription(
    owner_id: str,
    x_auth_id: str = Header(..., alias="X-Auth-ID"),
    subscription_service: SubscriptionService = Depends(Provide[Container.subscription_service]),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """
    Get active subscription for an owner.
    Restricted to users belonging to that owner or system admins (future).
    """
    user = user_service.get_user_by_auth_id(x_auth_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this subscription")

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
    x_auth_id: str = Header(..., alias="X-Auth-ID"),
    subscription_service: SubscriptionService = Depends(Provide[Container.subscription_service]),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    """
    Subscribe owner to a plan.
    Requires ADMIN role.
    """
    user = user_service.get_user_by_auth_id(x_auth_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.owner_id != subscription_data.owner_id:
        raise HTTPException(status_code=403, detail="Cannot create subscription for another organization")

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can manage subscriptions")

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
