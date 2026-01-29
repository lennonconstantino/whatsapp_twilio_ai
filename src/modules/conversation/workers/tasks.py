from typing import Any, Dict

from src.core.utils import get_logger
from src.modules.conversation.components.conversation_lifecycle import \
    ConversationLifecycle

logger = get_logger(__name__)


class ConversationTasks:
    """
    Handlers for conversation background tasks.
    """

    def __init__(self, lifecycle: ConversationLifecycle):
        self.lifecycle = lifecycle

    async def process_idle_conversations(self, payload: Dict[str, Any]):
        """Handler for processing idle conversations."""
        limit = payload.get("limit", 100)
        idle_minutes = payload.get("idle_minutes")

        logger.info("Starting idle conversation processing task", limit=limit)
        try:
            count = self.lifecycle.process_idle_timeouts(
                idle_minutes=idle_minutes, limit=limit
            )
            logger.info("Completed idle conversation processing task", count=count)
        except Exception as e:
            logger.error(f"Error in idle conversation task: {e}")
            raise e

    async def process_expired_conversations(self, payload: Dict[str, Any]):
        """Handler for processing expired conversations."""
        limit = payload.get("limit", 100)

        logger.info("Starting expired conversation processing task", limit=limit)
        try:
            count = self.lifecycle.process_expirations(limit=limit)
            logger.info("Completed expired conversation processing task", count=count)
        except Exception as e:
            logger.error(f"Error in expired conversation task: {e}")
            raise e
