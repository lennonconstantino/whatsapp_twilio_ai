from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IPaymentGateway(ABC):
    """
    Interface for payment gateways (Stripe, Paddle, etc.)
    """

    @abstractmethod
    def create_customer(self, email: str, name: str, metadata: Dict[str, Any]) -> str:
        """Create a customer in the payment gateway and return the ID."""
        pass

    @abstractmethod
    def create_subscription(self, customer_id: str, price_id: str) -> str:
        """Create a subscription."""
        pass

    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        pass

    @abstractmethod
    def construct_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Verify and construct webhook event."""
        pass
