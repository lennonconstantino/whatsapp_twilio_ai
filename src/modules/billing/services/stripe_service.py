import stripe
from typing import Dict, Any, Optional

from src.core.config import settings
from src.modules.billing.services.payment_gateway import IPaymentGateway

class StripeService(IPaymentGateway):
    """
    Stripe implementation of Payment Gateway.
    """

    def __init__(self):
        self.api_key = settings.stripe.api_key
        self.webhook_secret = settings.stripe.webhook_secret
        
        if self.api_key:
            stripe.api_key = self.api_key

    def create_customer(self, email: str, name: str, metadata: Dict[str, Any]) -> str:
        if not self.api_key:
            raise ValueError("Stripe API Key not configured")
            
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata
        )
        return customer.id

    def create_subscription(self, customer_id: str, price_id: str) -> str:
        if not self.api_key:
            raise ValueError("Stripe API Key not configured")

        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
        )
        return subscription.id

    def cancel_subscription(self, subscription_id: str) -> bool:
        if not self.api_key:
            raise ValueError("Stripe API Key not configured")

        try:
            stripe.Subscription.delete(subscription_id)
            return True
        except stripe.error.StripeError:
            return False

    def construct_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        if not self.webhook_secret:
            raise ValueError("Stripe Webhook Secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError as e:
            # Invalid payload
            raise e
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise e
