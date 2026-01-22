"""
API routes for Twilio webhook integration.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from supabase import Client

from src.core.utils import get_logger, get_db
from src.core.config import settings

from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.channels.twilio.services.webhook_service import TwilioWebhookService
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository

from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.identity.services.user_service import UserService
from src.modules.identity.services.feature_service import FeatureService
from src.modules.identity.repositories.user_repository import UserRepository
from src.modules.identity.repositories.feature_repository import FeatureRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["webhooks"])

async def parse_twilio_payload(request: Request) -> TwilioWhatsAppPayload:
    """Parse Twilio form data into payload model"""
    form_data = await request.form()

    return TwilioWhatsAppPayload(
        message_sid=form_data.get('MessageSid'),
        account_sid=form_data.get('AccountSid'), # Owner
        
        body=form_data.get('Body'),
        message_type=form_data.get("MessageType"),
        
        from_number=form_data.get('From'),
        wa_id=form_data.get("WaId"),
        profile_name=form_data.get("ProfileName"),
        
        to_number=form_data.get('To'),
        
        num_media=form_data.get('NumMedia'),
        num_segments=form_data.get('NumSegments'),
        
        sms_status=form_data.get('SmsStatus'),
        api_version=form_data.get('ApiVersion'),
        channel_metadata=form_data.get('ChannelMetadata'),

        media_url=form_data.get('MediaUrl0'), # Getting the URL of the file
        media_content_type=form_data.get('MediaContentType0'),  # Getting the extension for the file

        date_created=form_data.get('DateCreated'),

        to_country=form_data.get('ToCountry'),
        to_state=form_data.get('ToState'),
        to_city=form_data.get('ToCity'),
        from_city=form_data.get('FromCity'),
        from_zip=form_data.get('FromZip'),
        to_zip=form_data.get('ToZip'),
        from_country=form_data.get('FromCountry'),

        local_sender=form_data.get('LocalSender')
    )

async def get_webhook_service(
    db: Client = Depends(get_db)
) -> TwilioWebhookService:
    """Dependency to get TwilioWebhookService instance."""
    # Repositories
    twilio_repo = TwilioAccountRepository(db)
    user_repo = UserRepository(db)
    feature_repo = FeatureRepository(db)
    
    # Services
    twilio_service = TwilioService(twilio_repo)
    # ConversationService handles its own DB connection internally currently
    conversation_service = ConversationService() 
    user_service = UserService(user_repo)
    feature_service = FeatureService(feature_repo)
    
    return TwilioWebhookService(
        twilio_service=twilio_service,
        conversation_service=conversation_service,
        user_service=user_service,
        feature_service=feature_service,
        twilio_account_repo=twilio_repo
    )

async def validate_twilio_request(
    request: Request,
    X_Twilio_Signature: Optional[str] = Header(None, alias="X-Twilio-Signature"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Validate request authenticity (API Key or Twilio Signature).
    """
    if settings.api.environment != "development":
        if not x_api_key and not X_Twilio_Signature:
            raise HTTPException(
                status_code=401,
                detail="Authentication required (X-API-Key or X-Twilio-Signature)"
            )
        
        if x_api_key:
            if x_api_key != settings.twilio.internal_api_key:
                raise HTTPException(403, "Invalid API key")
        
        elif X_Twilio_Signature:
            # Use a lightweight instance or helper for validation
            twilio_service = TwilioService() 
            is_valid = twilio_service.validate_webhook_signature(
                str(request.url),
                await request.form(),
                X_Twilio_Signature
            )
            if not is_valid:
                raise HTTPException(status_code=403, detail="Invalid signature")

@router.post("/inbound", response_model=TwilioWebhookResponseDTO)
async def handle_inbound_message(
    background_tasks: BackgroundTasks,
    payload: TwilioWhatsAppPayload = Depends(parse_twilio_payload),
    service: TwilioWebhookService = Depends(get_webhook_service),
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
