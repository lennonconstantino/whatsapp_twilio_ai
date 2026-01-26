from enum import Enum


class SubscriptionStatus(str, Enum):
    """
    Enum for subscription statuses.
    
    Defines the status of a user's subscription:
    - ACTIVE: Subscription is currently active
    - CANCELED: Subscription has been canceled
    - EXPIRED: Subscription has expired
    - TRIAL: Subscription is in a trial period
    """
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    TRIAL = "trial"

    def __repr__(self) -> str:
        return f"SubscriptionStatus.{self.name}"
    