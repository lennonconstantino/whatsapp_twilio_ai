from typing import Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.core.di.container import Container
from src.modules.identity.api.dependencies import (get_authenticated_owner_id,
                                                   get_authenticated_user)
from src.modules.identity.models.subscription import (Subscription,
                                                      SubscriptionCreate)
from src.modules.identity.models.user import User, UserRole
from src.modules.identity.services.subscription_service import \
    SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/current", response_model=Subscription)
@inject
def get_current_subscription(
    owner_id: str = Depends(get_authenticated_owner_id),
    subscription_service: SubscriptionService = Depends(
        Provide[Container.subscription_service]
    ),
):
    """Get active subscription for the current user's organization."""
    subscription = subscription_service.get_active_subscription(owner_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active subscription not found",
        )
    return subscription


@router.get("/owner/{owner_id}", response_model=Subscription)
@inject
def get_owner_subscription(
    owner_id: str,
    authenticated_owner_id: str = Depends(get_authenticated_owner_id),
    subscription_service: SubscriptionService = Depends(
        Provide[Container.subscription_service]
    ),
):
    """
    Get active subscription for an owner.
    Restricted to users belonging to that owner or system admins (future).
    """
    if authenticated_owner_id != owner_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this subscription"
        )

    subscription = subscription_service.get_active_subscription(owner_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active subscription not found",
        )
    return subscription


@router.post("/", response_model=Subscription, status_code=status.HTTP_201_CREATED)
@inject
def create_subscription(
    subscription_data: SubscriptionCreate,
    user: User = Depends(get_authenticated_user),
    subscription_service: SubscriptionService = Depends(
        Provide[Container.subscription_service]
    ),
):
    """
    Subscribe owner to a plan.
    Requires ADMIN role.
    """
    if user.owner_id != subscription_data.owner_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot create subscription for another organization",
        )

    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only admins can manage subscriptions"
        )

    try:
        return subscription_service.create_subscription(subscription_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{subscription_id}/cancel", response_model=Subscription)
@inject
def cancel_subscription(
    subscription_id: str,
    owner_id: str = Depends(get_authenticated_owner_id),
    subscription_service: SubscriptionService = Depends(
        Provide[Container.subscription_service]
    ),
):
    """Cancel a subscription."""
    subscription = subscription_service.cancel_subscription(subscription_id, owner_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
        )
    return subscription
