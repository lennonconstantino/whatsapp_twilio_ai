from fastapi import APIRouter, Header, Request, HTTPException, Depends
from dependency_injector.wiring import inject, Provide
import structlog

from src.core.di.container import Container
from src.modules.billing.services.stripe_service import StripeService
from src.modules.billing.services.webhook_handler_service import WebhookHandlerService

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Billing Webhooks"])

@router.post("/stripe")
@inject
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    stripe_service: StripeService = Depends(Provide[Container.stripe_service]),
    webhook_handler: WebhookHandlerService = Depends(Provide[Container.webhook_handler_service])
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
    await webhook_handler.handle_event(event)

    return {"status": "success"}
