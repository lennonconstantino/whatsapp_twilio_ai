from fastapi import APIRouter, Header, Request, HTTPException, Depends
from dependency_injector.wiring import inject, Provide
import structlog

from src.core.di.container import Container
from src.modules.billing.services.stripe_service import StripeService

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Billing Webhooks"])

@router.post("/stripe")
@inject
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    stripe_service: StripeService = Depends(Provide[Container.stripe_service])
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()
    
    try:
        event = stripe_service.construct_event(payload, stripe_signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e: # SignatureVerificationError inherits from Exception
        # We catch broad exception here to avoid importing stripe in API layer directly
        # if possible, but StripeService raises specific errors.
        logger.error(f"Webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event.get('type')
    logger.info(f"Received Stripe event: {event_type}")

    # TODO: Delegate to a specific handler service
    if event_type == 'checkout.session.completed':
        # Payment successful, create/activate subscription
        pass
    elif event_type == 'invoice.payment_succeeded':
        # Renew subscription
        pass
    elif event_type == 'customer.subscription.deleted':
        # Cancel subscription
        pass

    return {"status": "success"}
