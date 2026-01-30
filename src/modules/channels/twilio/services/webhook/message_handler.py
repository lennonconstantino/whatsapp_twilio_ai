import uuid
from typing import Optional

from starlette.concurrency import run_in_threadpool

from src.core.utils import get_logger
from src.core.queue.service import QueueService
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message

logger = get_logger(__name__)

class TwilioWebhookMessageHandler:
    """
    Component responsible for message type determination and persistence.
    """

    def __init__(
        self,
        conversation_service: ConversationService,
        twilio_service: TwilioService,
        queue_service: QueueService,
    ):
        self.conversation_service = conversation_service
        self.twilio_service = twilio_service
        self.queue_service = queue_service

    async def _enqueue_embedding(self, message: Message):
        """Enqueue embedding generation task."""
        if not message.body or not message.body.strip():
            return
            
        try:
            user_id = None
            if isinstance(message.metadata, dict):
                user_id = message.metadata.get("user_id")

            await self.queue_service.enqueue(
                task_name="generate_embedding",
                payload={
                    "content": message.body,
                    "metadata": {
                        "msg_id": message.msg_id,
                        "conv_id": message.conv_id,
                        "owner_id": message.owner_id,
                        "user_id": user_id,
                        "role": "user" if message.message_owner == MessageOwner.USER else "assistant",
                        "timestamp": message.timestamp.isoformat() if message.timestamp else None
                    }
                },
                owner_id=message.owner_id
            )
        except Exception as e:
            logger.error(f"Failed to enqueue embedding task for msg {message.msg_id}: {e}")

    def determine_message_type(
        self, num_media: int, media_content_type: Optional[str]
    ) -> MessageType:
        """Determine internal message type based on Twilio payload."""
        message_type = MessageType.TEXT

        if num_media and num_media > 0:
            if media_content_type:
                if "image" in media_content_type:
                    message_type = MessageType.IMAGE
                elif "audio" in media_content_type:
                    message_type = MessageType.AUDIO
                elif "video" in media_content_type:
                    message_type = MessageType.VIDEO
                else:
                    message_type = MessageType.DOCUMENT

        return message_type

    async def get_or_create_conversation(
        self, owner_id: str, payload: TwilioWhatsAppPayload
    ) -> Conversation:
        return await run_in_threadpool(
            self.conversation_service.get_or_create_conversation,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp",
        )

    async def persist_outbound_message(
        self,
        conversation: Conversation,
        owner_id: str,
        payload: TwilioWhatsAppPayload,
        response_sid: str,
        response_status: str,
        response_num_media: int,
        response_body: str,
        correlation_id: str,
        message_type: MessageType,
    ) -> Message:
        message_data = MessageCreateDTO(
            conv_id=conversation.conv_id,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=response_body,
            direction=MessageDirection.OUTBOUND,
            message_owner=MessageOwner.SYSTEM,
            message_type=message_type,
            content=response_body,
            correlation_id=correlation_id,
            metadata={
                "message_sid": response_sid,
                "status": response_status,
                "num_media": response_num_media,
                "media_url": None,
                "media_type": None,
                "local_sender": True,
            },
        )

        return await run_in_threadpool(
            self.conversation_service.add_message, conversation, message_data
        )

    async def persist_inbound_message(
        self,
        conversation: Conversation,
        owner_id: str,
        payload: TwilioWhatsAppPayload,
        message_type: MessageType,
        correlation_id: str,
    ) -> Message:
        # If AUDIO, body starts with placeholder or empty
        message_body = payload.body
        if message_type == MessageType.AUDIO:
            message_body = message_body or "[Áudio recebido, processando transcrição...]"

        message_data = MessageCreateDTO(
            conv_id=conversation.conv_id,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=message_body,
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=message_type,
            content=message_body,
            correlation_id=correlation_id,
            metadata={
                "message_sid": payload.message_sid,
                "num_media": payload.num_media,
                "media_url": payload.media_url if payload.media_url else None,
                "media_type": (
                    payload.media_content_type if payload.media_content_type else None
                ),
            },
        )

        return await run_in_threadpool(
            self.conversation_service.add_message, conversation, message_data
        )

    async def handle_duplicate_message(
        self, payload: TwilioWhatsAppPayload, conversation: Conversation
    ) -> TwilioWebhookResponseDTO:
        logger.info(
            "Duplicate inbound message caught (race condition)",
            message_sid=payload.message_sid,
        )

        # Fetch existing message to return consistent response
        existing_message = await run_in_threadpool(
            self.conversation_service.message_repo.find_by_external_id,
            payload.message_sid,
        )

        return TwilioWebhookResponseDTO(
            success=True,
            message="Already processed",
            conv_id=conversation.conv_id,
            msg_id=existing_message.msg_id if existing_message else None,
        )

    async def send_twilio_message(
        self, owner_id: str, payload: TwilioWhatsAppPayload
    ):
        return await run_in_threadpool(
            self.twilio_service.send_message,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=payload.body,
        )

    async def send_and_persist_response(
        self,
        owner_id: str,
        conversation_id: str,
        sender_number: str,
        recipient_number: str,
        body: str,
        correlation_id: str,
        is_error: bool = False,
        user_id: str | None = None,
    ):
        """
        Helper to persist response and enqueue sending task.
        """
        try:
            # 1. Persist Outbound Message FIRST (Status: Pending)
            message_data = MessageCreateDTO(
                conv_id=conversation_id,
                owner_id=owner_id,
                from_number=sender_number,
                to_number=recipient_number,
                body=body,
                direction=MessageDirection.OUTBOUND,
                message_owner=MessageOwner.SYSTEM,
                message_type=MessageType.TEXT,
                content=body,
                correlation_id=correlation_id,
                metadata={
                    "status": "queued",
                    "auto_response": True,
                    "is_error_fallback": is_error,
                    "user_id": user_id,
                },
            )

            # Re-fetch conversation to ensure attached to session if needed
            conversation = await run_in_threadpool(
                self.conversation_service.get_or_create_conversation,
                owner_id=owner_id,
                from_number=sender_number,
                to_number=recipient_number,
                channel="whatsapp",
            )

            message = await run_in_threadpool(
                self.conversation_service.add_message, conversation, message_data
            )

            if not message:
                logger.error("Failed to persist outbound message", correlation_id=correlation_id)
                return

            # 2. Enqueue Sending Task
            await self.queue_service.enqueue(
                task_name="send_whatsapp_message",
                payload={
                    "owner_id": owner_id,
                    "msg_id": message.msg_id,
                    "from_number": sender_number,
                    "to_number": recipient_number,
                    "body": body,
                    "correlation_id": correlation_id,
                },
                owner_id=owner_id,
                correlation_id=correlation_id
            )
            
            # 3. Enqueue Embedding (Optimistic)
            await self._enqueue_embedding(message)

        except Exception as e:
            logger.error(
                "Critical error handling outbound response",
                error=str(e),
                correlation_id=correlation_id,
            )

    async def update_message_body(self, msg_id: str, new_body: str):
        await run_in_threadpool(
            self.conversation_service.message_repo.update,
            id_value=msg_id,
            data={"body": new_body, "content": new_body},
            id_column="msg_id"
        )
