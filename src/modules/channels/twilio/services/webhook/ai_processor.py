import json
from typing import Dict, Any

from starlette.concurrency import run_in_threadpool

from src.core.utils import get_logger
from src.core.queue.service import QueueService
from src.modules.ai.engines.lchain.core.agents.agent_factory import AgentFactory
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.identity.services.identity_service import IdentityService
from src.modules.identity.utils.profile_memory import extract_profile_name, should_forget_profile
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler

logger = get_logger(__name__)

class TwilioWebhookAIProcessor:
    """
    Component responsible for handling AI processing and responses.
    """

    def __init__(
        self,
        identity_service: IdentityService,
        agent_factory: AgentFactory,
        queue_service: QueueService,
        message_handler: TwilioWebhookMessageHandler,
    ):
        self.identity_service = identity_service
        self.agent_factory = agent_factory
        self.queue_service = queue_service
        self.message_handler = message_handler

    async def enqueue_ai_task(
        self,
        owner_id: str,
        conversation_id: str,
        msg_id: str,
        payload_dump: Dict[str, Any],
        correlation_id: str,
    ):
        await self.queue_service.enqueue(
            task_name="process_ai_response",
            payload={
                "owner_id": owner_id,
                "conversation_id": conversation_id,
                "msg_id": msg_id,
                "payload": payload_dump,
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
            owner_id=owner_id,
        )

    async def handle_ai_response_task(self, task_payload: Dict[str, Any]):
        """
        Async wrapper for queue task.
        """
        logger.info("Worker received handle_ai_response_task", task_payload=task_payload)
        payload = TwilioWhatsAppPayload(**task_payload["payload"])

        await self.handle_ai_response(
            owner_id=task_payload["owner_id"],
            conversation_id=task_payload["conversation_id"],
            msg_id=task_payload["msg_id"],
            payload=payload,
            correlation_id=task_payload["correlation_id"],
        )

    async def handle_ai_response(
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
            # We can run this sync DB call in threadpool if IdentityService is sync
            # IdentityService methods seem to be synchronous based on usage in original code (run_in_threadpool)
            search_phone = (
                payload.from_number.replace("whatsapp:", "").strip()
                if payload.from_number
                else ""
            )
            
            user = await run_in_threadpool(self.identity_service.get_user_by_phone, search_phone)

            # 2. Resolve Feature (Dynamic based on user/owner config)
            feature = await run_in_threadpool(self.identity_service.get_active_feature, owner_id)

            user_dump = user.model_dump() if user else None

            if user and payload.body:
                if should_forget_profile(payload.body):
                    await run_in_threadpool(self.identity_service.clear_user_profile_name, user.user_id)
                    if user_dump is not None:
                        user_dump["profile_name"] = None
                else:
                    extracted_name = extract_profile_name(payload.body)
                    if extracted_name and (user_dump or {}).get("profile_name") != extracted_name:
                        await run_in_threadpool(
                            self.identity_service.update_user_profile_name,
                            user.user_id,
                            extracted_name,
                        )
                        if user_dump is not None:
                            user_dump["profile_name"] = extracted_name

            additional_context = ""
            if user_dump:
                profile_parts = []
                # Expose user_id to context so agents can use tools that require it
                if user_dump.get("user_id"):
                    profile_parts.append(f"- user_id: {user_dump['user_id']}")

                if user_dump.get("profile_name"):
                    profile_parts.append(f"- profile_name: {user_dump['profile_name']}")
                
                if user_dump.get("preferences"):
                    try:
                        prefs_str = json.dumps(user_dump['preferences'], ensure_ascii=False)
                        profile_parts.append(f"- preferences: {prefs_str}")
                    except Exception:
                        pass

                if profile_parts:
                    additional_context = "User Profile:\n" + "\n".join(profile_parts) + "\n"

            agent_context = {
                "owner_id": owner_id,
                "correlation_id": correlation_id,
                "msg_id": msg_id,
                "session_id": conversation_id,
                "user": user_dump,
                "channel": "whatsapp",
                "feature": feature.name if feature else None,
                "feature_id": feature.feature_id if feature else None,
                "memory": None,
                "additional_context": additional_context,
            }

            if user and payload.body and str(payload.body).strip():
                try:
                    await self.queue_service.enqueue(
                        task_name="generate_embedding",
                        payload={
                            "content": payload.body,
                            "metadata": {
                                "msg_id": msg_id,
                                "conv_id": conversation_id,
                                "owner_id": owner_id,
                                "user_id": user.user_id,
                                "role": "user",
                            },
                        },
                        owner_id=owner_id,
                        correlation_id=correlation_id,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to enqueue inbound embedding task",
                        error=str(e),
                        correlation_id=correlation_id,
                    )

            # 3. Run Agent (Synchronous Blocking Call)
            if user:
                # Agent is now created via Factory based on feature
                feature_name = feature.name if feature else "finance"
                agent = self.agent_factory.get_agent(feature_name)

                # Agent.run is likely blocking/CPU intensive
                response_text = await run_in_threadpool(
                    agent.run, user_input=payload.body, **agent_context
                )
                
                logger.info(
                    f"Agent raw response: {repr(response_text)}",
                    correlation_id=correlation_id
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
            await self.message_handler.send_and_persist_response(
                owner_id=owner_id,
                conversation_id=conversation_id,
                sender_number=payload.to_number,
                recipient_number=payload.from_number,
                body=response_text,
                correlation_id=correlation_id,
                user_id=user.user_id if user else None,
            )

            logger.info("AI response processed and sent", correlation_id=correlation_id)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(
                "Error in AI background processing",
                error=str(e),
                traceback=tb,
                correlation_id=correlation_id,
            )

            # Send friendly error message
            error_message = "Desculpe, estou enfrentando dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."

            await self.message_handler.send_and_persist_response(
                owner_id=owner_id,
                conversation_id=conversation_id,
                sender_number=payload.to_number,
                recipient_number=payload.from_number,
                body=error_message,
                correlation_id=correlation_id,
                is_error=True,
            )
