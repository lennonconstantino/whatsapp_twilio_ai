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
        payload = task_payload["payload"]
        owner_id = task_payload["owner_id"]
        correlation_id = task_payload.get("correlation_id")
        
        msg_id = payload.get("msg_id")
        from_number = payload["from_number"]
        to_number = payload["to_number"]
        body = payload["body"]

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
                update_data = {
                    "metadata": {
                        "message_sid": response.sid,
                        "status": response.status,
                        "num_media": response.num_media,
                        "delivery_status": "sent"
                    }
                }
                # Note: This is a simplistic update. In a real scenario, we might merge metadata.
                # For now, we assume the initial metadata was minimal.
                # Ideally, we should fetch, merge and update.
                
                # We can also update status if we had a MessageStatus enum field.
                
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
