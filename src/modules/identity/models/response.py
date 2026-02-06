from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.modules.identity.models.owner import Owner
from src.modules.billing.models.subscription import (Subscription,
                                                      SubscriptionWithPlan)
from src.modules.identity.models.user import User


class OwnerWithSubscription(Owner):
    """
    Model for representing an owner with an active subscription.
    """

    subscription: Optional[SubscriptionWithPlan] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfile(User):
    """
    Model for representing a user profile with owner and permissions.
    """

    owner: OwnerWithSubscription
    permissions: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class RegisterOrganizationRequest(BaseModel):
    """
    Model for representing a request to register a new organization.
    """

    organization_name: str = Field(..., min_length=1, max_length=255)
    organization_email: EmailStr
    admin_external_auth_id: str
    admin_email: EmailStr
    admin_first_name: Optional[str] = None
    admin_last_name: Optional[str] = None
    plan_id: str = "plan_free"  # Default para plano free

    model_config = ConfigDict(from_attributes=True)


class RegisterOrganizationResponse(BaseModel):
    """
    Model for representing the response after registering a new organization.
    """

    owner: Owner
    admin_user: User
    subscription: Subscription

    model_config = ConfigDict(from_attributes=True)
