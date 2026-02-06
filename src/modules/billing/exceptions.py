class BillingError(Exception):
    """Base exception for billing module errors."""
    pass


class BillingRepositoryError(BillingError):
    """Raised when a repository operation fails due to infrastructure issues."""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class SubscriptionNotFoundError(BillingError):
    """Raised when a subscription is expected but not found."""
    pass


class PlanNotFoundError(BillingError):
    """Raised when a plan is expected but not found."""
    pass


class FeatureUsageError(BillingError):
    """Raised when feature usage operation fails."""
    pass
