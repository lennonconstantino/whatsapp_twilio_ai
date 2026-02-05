from enum import Enum


class SubscriptionStatus(str, Enum):
    """
    Enum for subscription statuses.

    Defines the status of a user's subscription:
    - INCOMPLETE: Created but payment not confirmed
    - TRIALING: In trial period
    - ACTIVE: Active and paid
    - PAST_DUE: Payment failed but still active (grace period)
    - PAUSED: Temporarily paused
    - PENDING_CANCELLATION: Active until period end
    - CANCELED: Canceled and no longer active
    - EXPIRED: Ended naturally
    - UNPAID: Failed payment, access revoked
    - SUSPENDED: Suspended by admin
    """

    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    PENDING_CANCELLATION = "pending_cancellation"
    CANCELED = "canceled"
    EXPIRED = "expired"
    UNPAID = "unpaid"
    SUSPENDED = "suspended"

    def __repr__(self) -> str:
        return f"SubscriptionStatus.{self.name}"
