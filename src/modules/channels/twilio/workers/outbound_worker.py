import asyncio
from typing import Any, Dict

from src.core.utils.logging import get_logger
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.conversation.repositories.message_repository import MessageRepository


logger = get_logger(__name__)


class TwilioOutboundWorker:
    """
    Worker responsible for processing outbound message tasks.
    Consumes tasks from 'send_whatsapp_message' queue.
    """

    def __init__(
        self,
        twilio_service: TwilioService,
        message_repo: MessageRepository,
    ):
        self.twilio_service = twilio_service
        self.message_repo = message_repo

    async def handle_send_message_task(self, task_payload: Dict[str, Any]):
        """
        Process background task to send WhatsApp message.
        """
        nested_payload = task_payload.get("payload")
        payload = nested_payload if isinstance(nested_payload, dict) else task_payload

        owner_id = task_payload.get("owner_id") or payload.get("owner_id")
        correlation_id = task_payload.get("correlation_id") or payload.get("correlation_id")

        msg_id = payload.get("msg_id")
        from_number = payload.get("from_number")
        to_number = payload.get("to_number")
        body = payload.get("body")

        missing_fields = [
            field_name
            for field_name, value in {
                "owner_id": owner_id,
                "from_number": from_number,
                "to_number": to_number,
                "body": body,
            }.items()
            if not value
        ]
        if missing_fields:
            raise ValueError(
                f"send_whatsapp_message payload inválido; campos ausentes: {', '.join(missing_fields)}"
            )

        logger.info(
            "Processing outbound message task",
            msg_id=msg_id,
            correlation_id=correlation_id
        )

        try:
            # 1. Send via Twilio API
            response = await self.twilio_service.send_message(
                owner_id=owner_id,
                from_number=from_number,
                to_number=to_number,
                body=body,
            )

            # 2. Update Message Status in DB (if persisted message exists)
            if msg_id and response:
                existing_message = await self.message_repo.find_by_id(
                    msg_id, id_column="msg_id"
                )
                existing_metadata = (
                    dict(existing_message.metadata) if existing_message and existing_message.metadata else {}
                )
                existing_metadata.update(
                    {
                        "message_sid": response.sid,
                        "status": response.status,
                        "num_media": response.num_media,
                        "delivery_status": "sent",
                    }
                )

                await self.message_repo.update(
                    id_value=msg_id,
                    data={"metadata": existing_metadata},
                    id_column="msg_id",
                )

                logger.info(
                    "Outbound message sent successfully",
                    sid=response.sid,
                    msg_id=msg_id
                )

        except Exception as e:
            logger.error(
                "Failed to process outbound message task",
                error=str(e),
                msg_id=msg_id,
                correlation_id=correlation_id
            )
            # Depending on queue configuration, this might retry automatically.
            raise
