from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.modules.identity.enums.billing_period import BillingPeriod


class PlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: int = Field(0, ge=0)
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    is_public: bool = True
    max_users: Optional[int] = Field(None, ge=1)
    max_projects: Optional[int] = Field(None, ge=1)
    config_json: dict[str, Any] = Field(default_factory=dict)


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
    config_json: Optional[dict[str, Any]] = None
    active: Optional[bool] = None


class Plan(PlanBase):
    """
    Model for representing a subscription plan.

    This model extends the base plan attributes with additional fields
    specific to a subscription plan, such as plan ID, creation timestamp,
    update timestamp, and active status.
    """

    plan_id: str
    created_at: datetime
    updated_at: datetime
    active: bool = True

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        return f"Plan(plan_id={self.plan_id}, name={self.name}, display_name={self.display_name}, price_cents={self.price_cents}, billing_period={self.billing_period}, is_public={self.is_public}, max_users={self.max_users}, max_projects={self.max_projects}, active={self.active})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Plan):
            return False
        return self.plan_id == other.plan_id

    def __hash__(self) -> int:
        return hash(self.plan_id)
