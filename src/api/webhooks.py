"""
API routes for Twilio webhook integration.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Header
from typing import Optional
from pydantic import BaseModel

from src.models.domain import Message, MessageCreateDTO, TwilioWebhookResponseDTO, TwilioWhatsAppPayload, User
from src.utils.helpers import TwilioHelpers
from src.config import settings

from ..models import MessageCreateDTO, MessageDirection, MessageOwner, MessageType, ConversationStatus
from ..services import ConversationService, TwilioService
from ..repositories import TwilioAccountRepository
from ..utils import get_logger, get_db

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

def __detemine_message_type(NumMedia: int, MediaContentType0: str) -> MessageType:
    message_type = MessageType.TEXT

    if NumMedia and NumMedia > 0:
        if MediaContentType0:
            if "image" in MediaContentType0:
                message_type = MessageType.IMAGE
            elif "audio" in MediaContentType0:
                message_type = MessageType.AUDIO
            elif "video" in MediaContentType0:
                message_type = MessageType.VIDEO
            else:
                message_type = MessageType.DOCUMENT

    return message_type

def __sender(owner_id: int, payload: TwilioWhatsAppPayload, twilio_service: TwilioService) -> TwilioWebhookResponseDTO:
    print(f" Enviando via Client...")

    message_type = __detemine_message_type(payload.num_media, payload.media_content_type)

    # Get or create conversation
    conversation_service = ConversationService()
    conversation = conversation_service.get_or_create_conversation(
        owner_id=owner_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        channel="whatsapp"
    )

    response = twilio_service.send_message(
        owner_id=owner_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        body=payload.body
    )
    
    # Create message outbound
    message_data = MessageCreateDTO(
        conv_id=conversation.conv_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        body=response["body"],
        direction=MessageDirection.OUTBOUND,
        message_owner=MessageOwner.SYSTEM,
        message_type=message_type,
        content=response["body"],
        metadata={
            "message_sid": response["sid"],
            "status": response["status"],
            "num_media": getattr(response["message"], "num_media", 0),
            "media_url": None,
            "media_type": None
        }
    )
    
    message = conversation_service.add_message(conversation, message_data)        
    
    logger.info(
        "Processed outbound message",
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )

    return TwilioWebhookResponseDTO(
        success=True,
        message=message.body if message else None,
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )    

def __receive_and_response(owner_id: int, payload: TwilioWhatsAppPayload, twilio_service: TwilioService) -> TwilioWebhookResponseDTO:
    # Normal Flow
    message_type = __detemine_message_type(payload.num_media, payload.media_content_type)

    # Get or create conversation
    conversation_service = ConversationService()
    conversation = conversation_service.get_or_create_conversation(
        owner_id=owner_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        channel="whatsapp"
    )

    # Validar estado antes de adicionar mensagem (ISSUE #6)
    if conversation.is_closed() or conversation.is_expired():
        logger.warning(
            "Attempt to add message to closed/expired conversation",
            conv_id=conversation.conv_id,
            status=conversation.status,
            is_expired=conversation.is_expired()
        )
        
        # Se estava expirada mas não fechada, fecha agora
        if not conversation.is_closed() and conversation.is_expired():
            conversation_service.close_conversation(conversation, ConversationStatus.EXPIRED)
        
        # Criar nova conversa forçadamente
        conversation = conversation_service._create_new_conversation(
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp",
            user_id=None,
            metadata={}
        )

    # Create message inbound
    message_data = MessageCreateDTO(
        conv_id=conversation.conv_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        body=payload.body,
        direction=MessageDirection.INBOUND,
        message_owner=MessageOwner.USER,
        message_type=message_type,
        content=payload.body,
        metadata={
            "message_sid": payload.message_sid,
            "num_media": payload.num_media,
            "media_url": payload.media_url if payload.media_url else None,
            "media_type": payload.media_content_type if payload.media_content_type else None
        }
    )
    
    message = conversation_service.add_message(conversation, message_data)
    
    logger.info(
        "Processed inbound message",
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )

    # outbound
    # TODO
    user = User(owner_id=owner_id, profile_name="User Profile", first_name="User", last_name="Profile")
    response_text = TwilioHelpers.generate_response(user_message=payload.body, user=user)

    # send message to twilio whatsapp
    response = twilio_service.send_message(owner_id=owner_id, from_number=payload.to_number, to_number=payload.from_number, body=response_text)

    # Create message outbound
    message_data = MessageCreateDTO(
        conv_id=conversation.conv_id,
        from_number=payload.to_number,
        to_number=payload.from_number,
        body=response["body"],
        direction=MessageDirection.OUTBOUND,
        message_owner=MessageOwner.SYSTEM,
        message_type=message_type,
        content=response["message"].body,
        metadata={
            "message_sid": response["sid"],
            "status": response["status"],
            "num_media": getattr(response["message"], "num_media", 0),
            "media_url": None,
            "media_type": None
        }
    )
    
    message = conversation_service.add_message(conversation, message_data)        
    
    logger.info(
        "Processed outbound message",
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )

    return TwilioWebhookResponseDTO(
        success=True,
        message="Message processed successfully",
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )

def __get_owner_id(payload: TwilioWhatsAppPayload) -> int:
    # Determine owner_id from To number
    # In production, you'd look this up from twilio_accounts table
    # For now, use a placeholder
    db_client = get_db()
    twilio_repo = TwilioAccountRepository(db_client)
    to_number = payload.to_number or ""
    if to_number.startswith("whatsapp:"):
        to_number = to_number.split(":", 1)[1]
    account = None
    if payload.account_sid:
        account = twilio_repo.find_by_account_sid(payload.account_sid)
    if not account and to_number:
        account = twilio_repo.find_by_phone_number(to_number)
    if not account and getattr(settings.twilio, "account_sid", None):
        account = twilio_repo.find_by_account_sid(settings.twilio.account_sid)
    if not account:
        logger.error("Owner lookup failed", to_number=payload.to_number, account_sid=payload.account_sid)
        raise HTTPException(status_code=403, detail="Owner not found for inbound/outbound number")
    logger.info("Owner resolved", owner_id=account.owner_id, to_number=to_number, account_sid=payload.account_sid)
    return account.owner_id

def __verify_idempotency(payload: TwilioWhatsAppPayload, conversation_service: ConversationService) -> Message:
    """Verify if a message has already been processed."""
    existing_message = conversation_service.message_repo.find_by_external_id(
        payload.message_sid
    )
    if existing_message:
        logger.info("Duplicate webhook, already processed", 
                    message_sid=payload.message_sid)
        return existing_message
    
    return None

@router.post("/inbound", response_model=TwilioWebhookResponseDTO)
async def handle_inbound_message(
    request: Request,
    payload: TwilioWhatsAppPayload = Depends(parse_twilio_payload),
    X_Twilio_Signature: Optional[str] = Header(None, alias="X-Twilio-Signature"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Handle inbound messages from Twilio.
    
    This endpoint receives webhooks when a message is sent to a Twilio number.
    """
    logger.info(
        "Received inbound message",
        from_number=payload.from_number,
        to_number=payload.to_number,
        message_sid=payload.message_sid
    )
    
    try:
        twilio_service = TwilioService()
        conversation_service = ConversationService()
        # Validate webhook signature and api_key - Production
        if settings.api.environment != "development":
            # Requer pelo menos uma forma de autenticação
            if not x_api_key and not X_Twilio_Signature:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required (X-API-Key or X-Twilio-Signature)"
                )
            
            # if has internal API key, validate
            if x_api_key:
                #client_ip = request.client.host
    
                # Lista de IPs confiáveis (localhost, rede interna)
                #trusted_ips = ["127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12"]

                if x_api_key != settings.twilio.internal_api_key:
                    raise HTTPException(403, "Invalid API key")
            
            # if has X-Twilio-Signature, validate
            elif X_Twilio_Signature:
                is_valid = twilio_service.validate_webhook_signature(
                    str(request.url),
                    await request.form(),
                    X_Twilio_Signature
                )
                if not is_valid:
                    raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Verificar idempotência
        existing_message = __verify_idempotency(payload, conversation_service)
        if existing_message:
            return TwilioWebhookResponseDTO(
                success=True,
                message="Already processed",
                conv_id=existing_message.conv_id,
                msg_id=existing_message.msg_id
            )

        # Owner id Tenant
        owner_id = __get_owner_id(payload)

        # Local Sender
        if payload.local_sender:
            return __sender(owner_id=owner_id, payload=payload, twilio_service=twilio_service)

        # Normal Flow
        return __receive_and_response(owner_id=owner_id, payload=payload, twilio_service=twilio_service)

        
    except Exception as e:
        logger.error("Error processing inbound message", error=str(e))
        # Don't raise HTTPException to avoid Twilio retries
        return TwilioWebhookResponseDTO(
            success=False,
            message=f"Error: {str(e)}"
        )


@router.post("/status", response_model=TwilioWebhookResponseDTO)
async def handle_status_callback(
    request: Request,
    MessageSid: str = Form(..., alias="MessageSid"),
    MessageStatus: str = Form(..., alias="MessageStatus"),
    ErrorCode: Optional[str] = Form(None, alias="ErrorCode"),
    ErrorMessage: Optional[str] = Form(None, alias="ErrorMessage"),
    X_Twilio_Signature: Optional[str] = Header(None, alias="X-Twilio-Signature")
):
    """
    Handle message status callbacks from Twilio.
    
    This endpoint receives updates about message delivery status.
    """
    logger.info(
        "Received status callback",
        message_sid=MessageSid,
        status=MessageStatus,
        error_code=ErrorCode
    )
    
    try:
        # TODO: Update message status in database
        # For now, just log it
        
        if ErrorCode:
            logger.warning(
                "Message delivery error",
                message_sid=MessageSid,
                error_code=ErrorCode,
                error_message=ErrorMessage
            )
        
        return TwilioWebhookResponseDTO(
            success=True,
            message="Status updated successfully"
        )
        
    except Exception as e:
        logger.error("Error processing status callback", error=str(e))
        return TwilioWebhookResponseDTO(
            success=False,
            message=f"Error: {str(e)}"
        )


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhooks."""
    return {"status": "ok", "service": "twilio-webhooks"}
