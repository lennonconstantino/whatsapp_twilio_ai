import uuid
import os
from typing import Any, Dict, Optional

from fastapi import HTTPException

from src.core.utils.helpers import TwilioHelpers
from src.core.queue.service import QueueService
from src.core.utils import get_logger
from src.core.utils.exceptions import DuplicateError
from src.modules.ai.services.transcription_service import TranscriptionService
from src.modules.ai.engines.lchain.core.agents.agent_factory import AgentFactory
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.twilio_account_service import \
    TwilioAccountService
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.services.conversation_service import \
    ConversationService
from src.modules.identity.services.identity_service import IdentityService

logger = get_logger(__name__)

from starlette.concurrency import run_in_threadpool


class TwilioWebhookService:
    """
    Service to handle Twilio Webhooks orchestration.
    """

    def __init__(
        self,
        twilio_service: TwilioService,
        conversation_service: ConversationService,
        identity_service: IdentityService,
        twilio_account_service: TwilioAccountService,
        agent_factory: AgentFactory,
        queue_service: QueueService,
        transcription_service: Optional[TranscriptionService] = None,
    ):
        self.twilio_service = twilio_service
        self.conversation_service = conversation_service
        self.identity_service = identity_service
        self.twilio_account_service = twilio_account_service
        self.agent_factory = agent_factory
        self.queue_service = queue_service
        self.transcription_service = transcription_service

        # Register queue handlers
        self.queue_service.register_handler(
            "process_ai_response", self.handle_ai_response_task
        )
        self.queue_service.register_handler(
            "transcribe_audio", self.handle_audio_transcription_task
        )

    def _determine_message_type(
        self, num_media: int, media_content_type: str
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

    def resolve_owner_id(self, payload: TwilioWhatsAppPayload) -> str:
        """
        Resolve the Owner ID (Tenant) based on the To number or Account SID.
        """
        account = self.twilio_account_service.resolve_account(
            to_number=payload.to_number, account_sid=payload.account_sid
        )

        if not account:
            logger.error(
                "Owner lookup failed",
                to_number=payload.to_number,
                account_sid=payload.account_sid,
            )
            raise HTTPException(
                status_code=403, detail="Owner not found for inbound/outbound number"
            )

        return account.owner_id

    async def process_webhook(
        self, payload: TwilioWhatsAppPayload
    ) -> TwilioWebhookResponseDTO:
        """
        Main entry point for webhook processing.
        """
        # 1. Resolve Owner (Run sync DB op in threadpool)
        owner_id = await run_in_threadpool(self.resolve_owner_id, payload)

        # 1.5. Validate Owner Plan (Access Control)
        if not payload.local_sender:
            has_access = await run_in_threadpool(
                self.identity_service.validate_owner_access, owner_id
            )
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
            return await self._process_local_sender(owner_id, payload)
        else:
            return await self._process_inbound_message(owner_id, payload)

    async def _process_local_sender(
        self, owner_id: str, payload: TwilioWhatsAppPayload
    ) -> TwilioWebhookResponseDTO:
        """
        Handle local/system generated outbound messages via webhook (Simulation/Test flow).
        """
        logger.info("Processing local sender (outbound system message)")
        correlation_id = payload.message_sid or str(uuid.uuid4())
        message_type = self._determine_message_type(
            payload.num_media, payload.media_content_type
        )

        # Get/Create Conversation
        conversation = await run_in_threadpool(
            self.conversation_service.get_or_create_conversation,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp",
        )

        # Send to Twilio
        response = await run_in_threadpool(
            self.twilio_service.send_message,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=payload.body,
        )

        # Persist Outbound Message
        message_data = MessageCreateDTO(
            conv_id=conversation.conv_id,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=response.body,
            direction=MessageDirection.OUTBOUND,
            message_owner=MessageOwner.SYSTEM,
            message_type=message_type,
            content=response.body,
            correlation_id=correlation_id,
            metadata={
                "message_sid": response.sid,
                "status": response.status,
                "num_media": response.num_media,
                "media_url": None,
                "media_type": None,
                "local_sender": True,
            },
        )

        message = await run_in_threadpool(
            self.conversation_service.add_message, conversation, message_data
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
        message_type = self._determine_message_type(
            payload.num_media, payload.media_content_type
        )

        media_content = None
        if payload.media_url and message_type != MessageType.AUDIO:
             # For non-audio media, we might want to download or just log
             # Currently only downloading audio for transcription
             pass
            
        logger.info("--> Determined message type: %s", message_type)

        # 1. Get/Create Conversation
        conversation = await run_in_threadpool(
            self.conversation_service.get_or_create_conversation,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp",
        )

        # 2. Persist Inbound Message (User)
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

        try:
            message = await run_in_threadpool(
                self.conversation_service.add_message, conversation, message_data
            )
        except DuplicateError:
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

        logger.info(
            "Processed inbound message",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
            correlation_id=correlation_id,
        )

        # 3. Schedule Processing
        if message_type == MessageType.AUDIO and payload.media_url:
             # Async Transcription
             await self.queue_service.enqueue(
                task_name="transcribe_audio",
                payload={
                    "msg_id": message.msg_id,
                    "media_url": payload.media_url,
                    "media_type": payload.media_content_type,
                    "owner_id": owner_id,
                    "conversation_id": conversation.conv_id,
                    "payload_dump": payload.model_dump(),
                },
                correlation_id=correlation_id,
                owner_id=owner_id,
             )
        else:
            # Direct AI Response
            await self.queue_service.enqueue(
                task_name="process_ai_response",
                payload={
                    "owner_id": owner_id,
                    "conversation_id": conversation.conv_id,
                    "msg_id": message.msg_id,
                    "payload": payload.model_dump(),
                    "correlation_id": correlation_id,
                },
                correlation_id=correlation_id,
                owner_id=owner_id,
            )

        return TwilioWebhookResponseDTO(
            success=True,
            message="Message received and processing started",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
        )

    async def handle_ai_response_task(self, task_payload: Dict[str, Any]):
        """
        Async wrapper for queue task.
        """
        payload = TwilioWhatsAppPayload(**task_payload["payload"])

        await run_in_threadpool(
            self.handle_ai_response,
            owner_id=task_payload["owner_id"],
            conversation_id=task_payload["conversation_id"],
            msg_id=task_payload["msg_id"],
            payload=payload,
            correlation_id=task_payload["correlation_id"],
        )

    async def handle_audio_transcription_task(self, task_payload: Dict[str, Any]):
        """
        Handler for async audio transcription.
        """
        logger.info("Starting async audio transcription", task_payload=task_payload)
        
        msg_id = task_payload.get("msg_id")
        media_url = task_payload.get("media_url")
        media_type = task_payload.get("media_type")
        owner_id = task_payload.get("owner_id")
        conversation_id = task_payload.get("conversation_id")
        payload_dump = task_payload.get("payload_dump")
        
        if not all([msg_id, media_url]):
            logger.error("Missing required fields for transcription task")
            return

        media_content = None
        try:
            # 1. Download Media
            media_content = await run_in_threadpool(
                TwilioHelpers.download_media,
                media_type=media_type,
                media_url=media_url
            )
            
            if not media_content or not self.transcription_service:
                logger.warning("Failed to download media or transcription service unavailable")
                return

            # 2. Transcribe
            logger.info("Transcribing audio file...")
            transcription = await run_in_threadpool(
                self.transcription_service.transcribe, media_content
            )
            
            if transcription:
                logger.info("Audio transcribed successfully: %s", transcription)
                
                # 3. Update Message in Database
                # Append transcription to the placeholder
                new_body = f"[Transcrição de Áudio: {transcription}]"
                
                await run_in_threadpool(
                    self.conversation_service.message_repo.update,
                    id_value=msg_id,
                    data={"body": new_body, "content": new_body},
                    id_column="msg_id"
                )
                
                # Update payload dump body for the AI agent
                if payload_dump:
                    payload_dump["body"] = new_body

                # 4. Enqueue AI Response Task (Chain the next step)
                await self.queue_service.enqueue(
                    task_name="process_ai_response",
                    payload={
                        "owner_id": owner_id,
                        "conversation_id": conversation_id,
                        "msg_id": msg_id,
                        "payload": payload_dump,
                        "correlation_id": str(uuid.uuid4()),
                    },
                    correlation_id=str(uuid.uuid4()),
                    owner_id=owner_id
                )
            else:
                logger.warning("Transcription returned empty result")

        except Exception as e:
            logger.error("Error in async transcription task", error=str(e))
        finally:
             # Cleanup audio file
             if media_content and os.path.exists(media_content):
                 try:
                     os.remove(media_content)
                     logger.info("Cleaned up audio file: %s", media_content)
                 except Exception as cleanup_error:
                     logger.warning("Failed to cleanup audio file %s: %s", media_content, cleanup_error)

    def _send_and_persist_response(
        self,
        owner_id: str,
        conversation_id: str,
        sender_number: str,
        recipient_number: str,
        body: str,
        correlation_id: str,
        is_error: bool = False,
    ):
        """
        Helper to send message via Twilio and persist it.
        """
        try:
            # Send via Twilio
            response = self.twilio_service.send_message(
                owner_id=owner_id,
                from_number=sender_number,
                to_number=recipient_number,
                body=body,
            )

            if not response:
                logger.error(
                    "Failed to send response via Twilio", correlation_id=correlation_id
                )
                return

            # Persist Outbound Message
            message_data = MessageCreateDTO(
                conv_id=conversation_id,
                owner_id=owner_id,
                from_number=sender_number,
                to_number=recipient_number,
                body=response.body,
                direction=MessageDirection.OUTBOUND,
                message_owner=MessageOwner.SYSTEM,
                message_type=MessageType.TEXT,
                content=response.body,
                correlation_id=correlation_id,
                metadata={
                    "message_sid": response.sid,
                    "status": response.status,
                    "num_media": response.num_media,
                    "media_url": None,
                    "media_type": None,
                    "auto_response": True,
                    "is_error_fallback": is_error,
                },
            )

            # Re-fetch conversation to ensure attached to session if needed
            conversation = self.conversation_service.get_or_create_conversation(
                owner_id=owner_id,
                from_number=sender_number,
                to_number=recipient_number,
                channel="whatsapp",
            )

            self.conversation_service.add_message(conversation, message_data)

        except Exception as e:
            # If even sending the response fails, we just log it as critical
            logger.error(
                "Critical error sending response",
                error=str(e),
                correlation_id=correlation_id,
            )

    def handle_ai_response(
        self,
        owner_id: str,
        conversation_id: str,
        msg_id: str,
        payload: TwilioWhatsAppPayload,
        correlation_id: str,
    ):
        """
        Background task to run AI agent and send response.
        """
        logger.info("Starting AI processing", correlation_id=correlation_id)

        try:
            # 1. Get User Context
            search_phone = (
                payload.from_number.replace("whatsapp:", "").strip()
                if payload.from_number
                else ""
            )
            user = self.identity_service.get_user_by_phone(search_phone)

            # 2. Resolve Feature (Dynamic based on user/owner config)
            feature = self.identity_service.get_active_feature(owner_id)

            agent_context = {
                "owner_id": owner_id,
                "correlation_id": correlation_id,
                "msg_id": msg_id,
                "user": user.model_dump() if user else None,
                "channel": "whatsapp",
                "feature": feature.name if feature else None,
                "feature_id": feature.feature_id if feature else None,
                "memory": None,
                "additional_context": "",
            }

            # 3. Run Agent (Synchronous Blocking Call)
            # In a real async architecture, this should be run_in_executor
            if user:
                # Agent is now created via Factory based on feature
                feature_name = feature.name if feature else "finance"
                agent = self.agent_factory.get_agent(feature_name)

                response_text = agent.run(
                    user_input=payload.body, **agent_context
                )
            else:
                response_text = "Desculpe, não encontrei seu cadastro. Por favor entre em contato com o suporte."

            # Fallback for empty response to prevent Twilio Error 21619
            if not response_text or not str(response_text).strip():
                logger.warning(
                    "Agent returned empty response, using fallback",
                    correlation_id=correlation_id,
                )
                response_text = "Desculpe, ocorreu um erro interno ao processar sua mensagem. Tente novamente mais tarde."

            # 4. Send Response via Twilio
            self._send_and_persist_response(
                owner_id=owner_id,
                conversation_id=conversation_id,
                sender_number=payload.to_number,
                recipient_number=payload.from_number,
                body=response_text,
                correlation_id=correlation_id,
            )

            logger.info("AI response processed and sent", correlation_id=correlation_id)

        except Exception as e:
            logger.error(
                "Error in AI background processing",
                error=str(e),
                correlation_id=correlation_id,
            )

            # Send friendly error message
            error_message = "Desculpe, estou enfrentando dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."

            self._send_and_persist_response(
                owner_id=owner_id,
                conversation_id=conversation_id,
                sender_number=payload.to_number,
                recipient_number=payload.from_number,
                body=error_message,
                correlation_id=correlation_id,
                is_error=True,
            )
