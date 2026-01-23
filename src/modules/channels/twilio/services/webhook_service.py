import uuid
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks, HTTPException

from src.core.utils import get_logger
from src.core.config import settings
from src.core.utils.exceptions import DuplicateError
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository

from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.models.message import Message

from src.modules.identity.services.user_service import UserService
from src.modules.identity.services.feature_service import FeatureService
from src.modules.ai.engines.lchain.core.agents.routing_agent import RoutingAgent

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
        user_service: UserService,
        feature_service: FeatureService,
        twilio_account_repo: TwilioAccountRepository,
        agent_runner: RoutingAgent
    ):
        self.twilio_service = twilio_service
        self.conversation_service = conversation_service
        self.user_service = user_service
        self.feature_service = feature_service
        self.twilio_account_repo = twilio_account_repo
        self.agent_runner = agent_runner

    def _determine_message_type(self, num_media: int, media_content_type: str) -> MessageType:
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
        to_number = payload.to_number or ""
        if to_number.startswith("whatsapp:"):
            to_number = to_number.split(":", 1)[1]
        
        account = None
        
        # 1. Try by Account SID
        if payload.account_sid:
            account = self.twilio_account_repo.find_by_account_sid(payload.account_sid)
        
        # 2. Try by Phone Number
        if not account and to_number:
            account = self.twilio_account_repo.find_by_phone_number(to_number)
            
        # 3. Fallback to default from settings (Development only ideally)
        if not account and getattr(settings.twilio, "account_sid", None):
             account = self.twilio_account_repo.find_by_account_sid(settings.twilio.account_sid)

        if not account:
            logger.error("Owner lookup failed", to_number=payload.to_number, account_sid=payload.account_sid)
            raise HTTPException(status_code=403, detail="Owner not found for inbound/outbound number")
            
        return account.owner_id

    async def process_webhook(
        self, 
        payload: TwilioWhatsAppPayload, 
        background_tasks: BackgroundTasks
    ) -> TwilioWebhookResponseDTO:
        """
        Main entry point for webhook processing.
        """
        # 1. Resolve Owner (Run sync DB op in threadpool)
        owner_id = await run_in_threadpool(self.resolve_owner_id, payload)

        # 2. Check Idempotency
        existing_message = await run_in_threadpool(
            self.conversation_service.message_repo.find_by_external_id, 
            payload.message_sid
        )
        if existing_message:
            logger.info("Duplicate webhook, already processed", message_sid=payload.message_sid)
            return TwilioWebhookResponseDTO(
                success=True,
                message="Already processed",
                conv_id=existing_message.conv_id,
                msg_id=existing_message.msg_id
            )

        # 3. Route based on flow (Local Sender vs Normal Inbound)
        if payload.local_sender:
            return await self._process_local_sender(owner_id, payload)
        else:
            return await self._process_inbound_message(owner_id, payload, background_tasks)

    async def _process_local_sender(self, owner_id: str, payload: TwilioWhatsAppPayload) -> TwilioWebhookResponseDTO:
        """
        Handle local/system generated outbound messages via webhook (Simulation/Test flow).
        """
        logger.info("Processing local sender (outbound system message)")
        correlation_id = payload.message_sid or str(uuid.uuid4())
        message_type = self._determine_message_type(payload.num_media, payload.media_content_type)

        # Get/Create Conversation
        conversation = await run_in_threadpool(
            self.conversation_service.get_or_create_conversation,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp"
        )

        # Send to Twilio
        response = await run_in_threadpool(
            self.twilio_service.send_message,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=payload.body
        )
        
        # Persist Outbound Message
        message_data = MessageCreateDTO(
            conv_id=conversation.conv_id,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=response["body"],
            direction=MessageDirection.OUTBOUND,
            message_owner=MessageOwner.SYSTEM,
            message_type=message_type,
            content=response["body"],
            correlation_id=correlation_id,
            metadata={
                "message_sid": response["sid"],
                "status": response["status"],
                "num_media": getattr(response["message"], "num_media", 0),
                "media_url": None,
                "media_type": None,
                "local_sender": True
            }
        )
        
        message = await run_in_threadpool(self.conversation_service.add_message, conversation, message_data)        
        
        logger.info(
            "Processed outbound message",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
            correlation_id=correlation_id
        )

        return TwilioWebhookResponseDTO(
            success=True,
            message=message.body if message else None,
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None
        )

    async def _process_inbound_message(
        self, 
        owner_id: str, 
        payload: TwilioWhatsAppPayload,
        background_tasks: BackgroundTasks
    ) -> TwilioWebhookResponseDTO:
        """
        Handle normal user inbound messages.
        """
        logger.info("Processing inbound message with auto-response")
        correlation_id = payload.message_sid or str(uuid.uuid4())
        message_type = self._determine_message_type(payload.num_media, payload.media_content_type)

        # 1. Get/Create Conversation
        conversation = await run_in_threadpool(
            self.conversation_service.get_or_create_conversation,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp"
        )

        # 2. Persist Inbound Message (User)
        message_data = MessageCreateDTO(
            conv_id=conversation.conv_id,
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            body=payload.body,
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=message_type,
            content=payload.body,
            correlation_id=correlation_id,
            metadata={
                "message_sid": payload.message_sid,
                "num_media": payload.num_media,
                "media_url": payload.media_url if payload.media_url else None,
                "media_type": payload.media_content_type if payload.media_content_type else None
            }
        )
        
        try:
            message = await run_in_threadpool(self.conversation_service.add_message, conversation, message_data)
        except DuplicateError:
            logger.info("Duplicate inbound message caught (race condition)", message_sid=payload.message_sid)
            
            # Fetch existing message to return consistent response
            existing_message = await run_in_threadpool(
                self.conversation_service.message_repo.find_by_external_id, 
                payload.message_sid
            )
            
            return TwilioWebhookResponseDTO(
                success=True,
                message="Already processed",
                conv_id=conversation.conv_id,
                msg_id=existing_message.msg_id if existing_message else None
            )
        
        logger.info(
            "Processed inbound message",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id if message else None,
            correlation_id=correlation_id
        )

        # 3. Schedule AI Processing in Background
        # Pass minimal data needed for reconstruction to avoid pickling large objects if using process pool
        # For BackgroundTasks (thread pool), objects are fine.
        background_tasks.add_task(
            self.handle_ai_response,
            owner_id=owner_id,
            conversation_id=conversation.conv_id,
            user_message=message,
            payload=payload,
            correlation_id=correlation_id
        )

        return TwilioWebhookResponseDTO(
            success=True,
            message="Message received and processing started",
            conv_id=conversation.conv_id,
            msg_id=message.msg_id
        )

    def handle_ai_response(
        self,
        owner_id: str,
        conversation_id: str,
        user_message: Message,
        payload: TwilioWhatsAppPayload,
        correlation_id: str
    ):
        """
        Background task to run AI agent and send response.
        """
        logger.info("Starting AI processing", correlation_id=correlation_id)
        
        try:
            # 1. Get User Context
            search_phone = payload.from_number.replace("whatsapp:", "").strip() if payload.from_number else ""
            user = self.user_service.get_user_by_phone(search_phone)
            
            # 2. Resolve Feature (TODO: Make dynamic based on user/owner config)
            result = self.feature_service.validate_feature_path("src/modules/ai/engines/lchain/feature")
            feature = self.feature_service.get_feature_by_name(owner_id, result["feature"]+"_agent")

            agent_context = {
                "owner_id": owner_id, 
                "correlation_id": correlation_id,
                "msg_id": user_message.msg_id,
                "user": user.model_dump() if user else None,
                "channel": "whatsapp",
                "feature_id": feature.feature_id if feature else None,
                "memory": None,
                "additional_context": "",
            }

            # 3. Run Agent (Synchronous Blocking Call)
            # In a real async architecture, this should be run_in_executor
            if user:
                # Agent is now injected via DI (agent_runner)
                response_text = self.agent_runner.run(user_input=payload.body, **agent_context)
            else:
                response_text = "Desculpe, não encontrei seu cadastro. Por favor entre em contato com o suporte."

            # Fallback for empty response to prevent Twilio Error 21619
            if not response_text or not str(response_text).strip():
                logger.warning("Agent returned empty response, using fallback", correlation_id=correlation_id)
                response_text = "Desculpe, ocorreu um erro interno ao processar sua mensagem. Tente novamente mais tarde."

            # 4. Send Response via Twilio
            response = self.twilio_service.send_message(
                owner_id=owner_id, 
                from_number=payload.to_number, 
                to_number=payload.from_number, 
                body=response_text
            )
            
            if not response:
                logger.error("Failed to send AI response via Twilio", correlation_id=correlation_id)
                return

            # 5. Persist Outbound Message (System)
            message_data = MessageCreateDTO(
                conv_id=conversation_id,
                owner_id=owner_id,
                from_number=payload.to_number,
                to_number=payload.from_number,
                body=response["body"],
                direction=MessageDirection.OUTBOUND,
                message_owner=MessageOwner.SYSTEM,
                message_type=MessageType.TEXT, # Assuming AI returns text for now
                content=response["body"],
                correlation_id=correlation_id,
                metadata={
                    "message_sid": response["sid"],
                    "status": response["status"],
                    "num_media": getattr(response["message"], "num_media", 0),
                    "media_url": None,
                    "media_type": None,
                    "auto_response": True
                }
            )
            
            # Re-fetch conversation to ensure attached to session if needed, or pass ID
            # conversation_service.add_message expects conversation object mostly for ID. 
            # Ideally add_message should accept ID. Looking at code:
            # message = conversation_service.add_message(conversation, message_data)
            # Let's get conversation object again to be safe or mock it if only ID is used.
            # Assuming get_conversation_by_id exists or similar.
            # For now, using get_or_create again is safe but slightly inefficient.
            # Ideally conversation_service should have get_by_id.
            # Let's check conversation_service in next step. For now, get_or_create.
            conversation = self.conversation_service.get_or_create_conversation(
                owner_id=owner_id,
                from_number=payload.from_number,
                to_number=payload.to_number,
                channel="whatsapp"
            )
            
            self.conversation_service.add_message(conversation, message_data)
            
            logger.info("AI response processed and sent", correlation_id=correlation_id)

        except Exception as e:
            logger.error("Error in AI background processing", error=str(e), correlation_id=correlation_id)
