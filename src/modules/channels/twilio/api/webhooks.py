"""
API routes for Twilio webhook integration.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from src.core.utils import get_logger
from src.core.di.container import Container

from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.channels.twilio.services.webhook_service import TwilioWebhookService
from .dependencies import parse_twilio_payload, validate_twilio_request


logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["webhooks"])

@router.post("/inbound", response_model=TwilioWebhookResponseDTO)
@inject
async def handle_inbound_message(
    background_tasks: BackgroundTasks,
    payload: TwilioWhatsAppPayload = Depends(parse_twilio_payload),
    service: TwilioWebhookService = Depends(Provide[Container.twilio_webhook_service]),
    _: None = Depends(validate_twilio_request)
):
    """
    Handle inbound messages from Twilio.
    
    This endpoint receives webhooks when a message is sent to a Twilio number.
    It processes the message asynchronously (AI response) to avoid Twilio timeouts.
    """
    logger.info(
        "Received inbound message",
        from_number=payload.from_number,
        to_number=payload.to_number,
        message_sid=payload.message_sid
    )
    
    try:
        return await service.process_webhook(payload, background_tasks)
    except Exception as e:
        logger.error("Error processing inbound message", error=str(e))
        # Don't raise HTTPException to avoid Twilio retries
        return TwilioWebhookResponseDTO(
            success=False,
            message=f"Error: {str(e)}"
        )
