from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from src.modules.billing.services.subscription_service import SubscriptionService
from src.modules.billing.services.plan_service import PlanService
from src.modules.billing.enums.subscription_status import SubscriptionStatus

logger = structlog.get_logger()

class WebhookHandlerService:
    """
    Handles Stripe webhooks and updates local billing state.
    """

    def __init__(
        self,
        subscription_service: SubscriptionService,
        plan_service: PlanService
    ):
        self.subscription_service = subscription_service
        self.plan_service = plan_service

    async def handle_event(self, event: Dict[str, Any]):
        """
        Dispatch Stripe event to appropriate handler.
        """
        event_type = event.get('type')
        data = event.get('data', {}).get('object', {})

        logger.info(f"Processing Stripe event: {event_type}", event_id=event.get('id'))

        try:
            if event_type == 'checkout.session.completed':
                await self._handle_checkout_session_completed(data)
            elif event_type == 'invoice.payment_succeeded':
                await self._handle_invoice_payment_succeeded(data)
            elif event_type == 'customer.subscription.deleted':
                await self._handle_subscription_deleted(data)
            else:
                logger.info(f"Unhandled event type: {event_type}")
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {str(e)}", exc_info=True)
            raise e

    async def _handle_checkout_session_completed(self, session: Dict[str, Any]):
        """
        Handle successful checkout. Create new subscription.
        """
        # Extract details
        client_reference_id = session.get('client_reference_id')
        stripe_subscription_id = session.get('subscription')
        stripe_customer_id = session.get('customer')
        metadata = session.get('metadata', {})
        plan_id = metadata.get('plan_id')

        if not client_reference_id:
            logger.warning("Missing client_reference_id in checkout session. Cannot link to user.")
            return

        if not plan_id:
            logger.warning("Missing plan_id in checkout session metadata. Cannot determine plan.")
            return

        logger.info(f"Checkout completed for user {client_reference_id}, plan {plan_id}")

        # Check if subscription already exists (idempotency or upgrade)
        # For now, we assume checkout creates a new subscription.
        # Ideally, we should check if user already has an active subscription.
        
        existing_sub = self.subscription_service.subscription_repo.find_by_owner(client_reference_id)
        if existing_sub and existing_sub.status == SubscriptionStatus.ACTIVE:
            logger.info(f"User {client_reference_id} already has an active subscription. Updating metadata instead of creating new.")
            # Optionally update the existing subscription with new stripe info if missing
            return

        # Create subscription
        self.subscription_service.create_subscription(
            owner_id=client_reference_id,
            plan_id=plan_id,
            metadata={
                "stripe_subscription_id": stripe_subscription_id,
                "stripe_customer_id": stripe_customer_id,
                "checkout_session_id": session.get('id')
            }
        )
        logger.info(f"Created subscription for user {client_reference_id}")

    async def _handle_invoice_payment_succeeded(self, invoice: Dict[str, Any]):
        """
        Handle recurring payment success. Update subscription status/dates.
        """
        stripe_subscription_id = invoice.get('subscription')
        if not stripe_subscription_id:
            return

        # Find subscription by stripe_subscription_id
        subscription = self.subscription_service.subscription_repo.find_by_stripe_subscription_id(stripe_subscription_id)
        
        if not subscription:
            logger.warning(f"Subscription not found for Stripe ID {stripe_subscription_id}")
            return

        # Update status to ACTIVE if it was not
        if subscription.status != SubscriptionStatus.ACTIVE:
             self.subscription_service.subscription_repo.update(
                subscription.subscription_id,
                {"status": SubscriptionStatus.ACTIVE}
            )
             logger.info(f"Updated subscription {subscription.subscription_id} status to ACTIVE")

        # Update period end?
        # Typically Stripe handles logic, but we might want to sync current_period_end
        # from invoice.lines.data[0].period.end or similar.
        # For simplicity, we trust Stripe's webhooks for status changes.

    async def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]):
        """
        Handle subscription cancellation from Stripe side.
        """
        stripe_subscription_id = subscription_data.get('id')
        if not stripe_subscription_id:
            return

        subscription = self.subscription_service.subscription_repo.find_by_stripe_subscription_id(stripe_subscription_id)
        
        if not subscription:
            logger.warning(f"Subscription not found for Stripe ID {stripe_subscription_id}")
            return

        # Cancel internally
        self.subscription_service.cancel_subscription(
            subscription_id=subscription.subscription_id,
            immediately=True,
            reason="Canceled via Stripe",
            triggered_by="stripe"
        )
        logger.info(f"Canceled subscription {subscription.subscription_id} due to Stripe event")
