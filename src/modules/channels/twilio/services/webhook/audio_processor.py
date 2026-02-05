import os
import uuid
from typing import Dict, Any, Optional

from starlette.concurrency import run_in_threadpool

from src.core.utils import get_logger
from src.modules.channels.twilio.utils.helpers import download_media
from src.core.queue.service import QueueService
from src.modules.ai.services.transcription_service import TranscriptionService
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler

logger = get_logger(__name__)

class TwilioWebhookAudioProcessor:
    """
    Component responsible for handling audio transcription tasks.
    """

    def __init__(
        self,
        transcription_service: Optional[TranscriptionService],
        queue_service: QueueService,
        message_handler: TwilioWebhookMessageHandler,
    ):
        self.transcription_service = transcription_service
        self.queue_service = queue_service
        self.message_handler = message_handler

    async def enqueue_transcription_task(
        self,
        msg_id: str,
        media_url: str,
        media_type: str,
        owner_id: str,
        conversation_id: str,
        payload_dump: Dict[str, Any],
        correlation_id: str,
    ):
        await self.queue_service.enqueue(
            task_name="transcribe_audio",
            payload={
                "msg_id": msg_id,
                "media_url": media_url,
                "media_type": media_type,
                "owner_id": owner_id,
                "conversation_id": conversation_id,
                "payload_dump": payload_dump,
            },
            correlation_id=correlation_id,
            owner_id=owner_id,
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
                download_media,
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
                new_body = f"[Transcrição de Áudio: {transcription}]"
                
                await self.message_handler.update_message_body(msg_id, new_body)
                
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
