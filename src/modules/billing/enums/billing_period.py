from enum import Enum


class BillingPeriod(str, Enum):
    """
    Enum for billing periods.

    Defines the duration for which a subscription is valid:
    - MONTHLY: Subscription valid for one month
    - YEARLY: Subscription valid for one year
    - LIFETIME: Subscription valid indefinitely
    """

    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

    def __repr__(self) -> str:
        return f"BillingPeriod.{self.name}"
