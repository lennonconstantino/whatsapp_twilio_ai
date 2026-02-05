
import uuid
from typing import Dict, Any

from src.core.utils.exceptions import DuplicateError
from src.core.queue.service import QueueService
from src.core.utils import get_logger
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.webhook.ai_processor import TwilioWebhookAIProcessor
from src.modules.channels.twilio.services.webhook.audio_processor import TwilioWebhookAudioProcessor
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler
from src.modules.channels.twilio.services.webhook.owner_resolver import TwilioWebhookOwnerResolver
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.enums.conversation_status import ConversationStatus


logger = get_logger(__name__)


class TwilioWebhookService:
    """
    Service to handle Twilio Webhooks orchestration.
    Refactored to use specialized components.
    """

    def __init__(
        self,
        owner_resolver: TwilioWebhookOwnerResolver,
        message_handler: TwilioWebhookMessageHandler,
        audio_processor: TwilioWebhookAudioProcessor,
        ai_processor: TwilioWebhookAIProcessor,
        queue_service: QueueService,
    ):
        self.owner_resolver = owner_resolver
        self.message_handler = message_handler
        self.audio_processor = audio_processor
        self.ai_processor = ai_processor
        self.queue_service = queue_service

        # Register queue handlers
        self.queue_service.register_handler(
            "process_ai_response", self.ai_processor.handle_ai_response_task
        )
        self.queue_service.register_handler(
            "transcribe_audio", self.audio_processor.handle_audio_transcription_task
        )
        self.queue_service.register_handler(
            "process_twilio_event", self.handle_webhook_event_task
        )

    async def enqueue_webhook_event(
        self, payload: TwilioWhatsAppPayload
    ) -> TwilioWebhookResponseDTO:
        """
        Enqueue the raw webhook event for async processing.
        Returns immediate 200 OK to Twilio.
        """
        # Determine owner_id from AccountSid (fast check, no DB if possible, but currently resolver needs DB)
        # Note: We can pass payload to queue and let worker resolve owner.
        # But QueueService.enqueue takes optional owner_id.
        # For now, we'll let the worker resolve the owner to avoid DB hit here.
        
        await self.queue_service.enqueue(
            "process_twilio_event",
            payload.model_dump(by_alias=True),
            correlation_id=payload.message_sid or str(uuid.uuid4())
        )
        
        return TwilioWebhookResponseDTO(
            success=True,
            message="Event received and enqueued",
            conv_id=None,
            msg_id=None
        )

    async def handle_webhook_event_task(self, payload_dict: Dict[str, Any]):
        """
        Worker handler for processing the raw webhook event.
        Rehydrates payload and calls process_webhook logic.
        """
        try:
            # Rehydrate payload
            payload = TwilioWhatsAppPayload(**payload_dict)
            await self.process_webhook(payload)
        except Exception as e:
            logger.error("Failed to process webhook event task", error=str(e))
            raise # Let queue retry

    async def process_webhook(
        self, payload: TwilioWhatsAppPayload
    ) -> TwilioWebhookResponseDTO:
        """
        Main entry point for webhook processing.
        """
        # 1. Resolve Owner
        owner_id = self.owner_resolver.resolve_owner_id(payload)

        # 1.5. Validate Owner Plan (Access Control)
        if not payload.local_sender:
            has_access = await self.owner_resolver.validate_owner_access(owner_id)
            if not has_access:
                logger.warning(
                    "Processing blocked due to inactive plan", owner_id=owner_id
                )
                return TwilioWebhookResponseDTO(
                    success=True,
                    message="Plan inactive or expired. Message processing skipped.",
                    conv_id=None,
                    msg_id=None,
                )

        # 2. Route based on flow (Local Sender vs Normal Inbound)
        if payload.local_sender:
            return await self._process_outbound_message(owner_id, payload)
        else:
            return await self._process_inbound_message(owner_id, payload)

    async def _process_outbound_message(
        self, owner_id: str, payload: TwilioWhatsAppPayload
    ) -> TwilioWebhookResponseDTO:
        """
        Handle local/system generated outbound messages via webhook (Simulation/Test flow).
        """
        logger.info("Processing local sender (outbound system message)")
        correlation_id = payload.message_sid or str(uuid.uuid4())
        message_type = self.message_handler.determine_message_type(
            payload.num_media, payload.media_content_type
        )

        # Get/Create Conversation
        conversation = await self.message_handler.get_or_create_conversation(
            owner_id, payload
        )

        # Send to Twilio
        response = await self.message_handler.send_twilio_message(owner_id, payload)

        if not response:
            logger.error("Failed to send outbound message via Twilio", owner_id=owner_id)
            return TwilioWebhookResponseDTO(
                success=False,
                message="Failed to send message to Twilio provider",
                conv_id=conversation.conv_id,
                msg_id=None,
            )

        # Persist Outbound Message
        message = await self.message_handler.persist_outbound_message(
            conversation=conversation,
            owner_id=owner_id,
            payload=payload,
            response_sid=response.sid,
            response_status=response.status,
            response_num_media=response.num_media,
            response_body=response.body,
            correlation_id=correlation_id,
            message_type=message_type,
        )

        logger.info(
            "Processed outbound message",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
            correlation_id=correlation_id,
        )

        return TwilioWebhookResponseDTO(
            success=True,
            message=message.body if message else None,
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
        )

    async def _process_inbound_message(
        self, owner_id: str, payload: TwilioWhatsAppPayload
    ) -> TwilioWebhookResponseDTO:
        """
        Handle normal user inbound messages.
        """
        logger.info("Processing inbound message with auto-response")
        correlation_id = payload.message_sid or str(uuid.uuid4())
        message_type = self.message_handler.determine_message_type(
            payload.num_media, payload.media_content_type
        )

        logger.info("--> Determined message type: %s", message_type)

        # 1. Get/Create Conversation
        conversation = await self.message_handler.get_or_create_conversation(
            owner_id, payload
        )

        # Check for Human Handoff
        is_handoff = conversation.status == ConversationStatus.HUMAN_HANDOFF.value
        if is_handoff:
            logger.info(
                "Conversation is in HUMAN_HANDOFF mode. Skipping AI processing.",
                conv_id=conversation.conv_id
            )

        # 2. Persist Inbound Message (User)
        try:
            message = await self.message_handler.persist_inbound_message(
                conversation=conversation,
                owner_id=owner_id,
                payload=payload,
                message_type=message_type,
                correlation_id=correlation_id,
            )
        except DuplicateError:
            return await self.message_handler.handle_duplicate_message(
                payload, conversation
            )

        logger.info(
            "Processed inbound message",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
            correlation_id=correlation_id,
            handoff_active=is_handoff
        )

        # 3. Schedule Processing (Only if NOT in Handoff)
        if is_handoff:
            # TODO: Emit WebSocket event for Agent Dashboard (Realtime Notification)
            return TwilioWebhookResponseDTO(
                success=True,
                message="Message received (Handoff Active)",
                conv_id=conversation.conv_id,
                msg_id=message.msg_id if message else None,
            )

        if message_type == MessageType.AUDIO and payload.media_url:
            # Async Transcription
            await self.audio_processor.enqueue_transcription_task(
                msg_id=message.msg_id,
                media_url=payload.media_url,
                media_type=payload.media_content_type,
                owner_id=owner_id,
                conversation_id=conversation.conv_id,
                payload_dump=payload.model_dump(),
                correlation_id=correlation_id,
            )
        else:
            # Direct AI Response
            await self.ai_processor.enqueue_ai_task(
                owner_id=owner_id,
                conversation_id=conversation.conv_id,
                msg_id=message.msg_id,
                payload_dump=payload.model_dump(),
                correlation_id=correlation_id,
            )

        return TwilioWebhookResponseDTO(
            success=True,
            message="Message received and processing started",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
        )
