import logging
from typing import Dict, Any, Optional, Callable, Awaitable
import asyncio
from datetime import datetime

from .interfaces import QueueBackend
from .models import QueueMessage
from .backends.sqlite import SqliteQueueBackend
from src.core.config import settings

logger = logging.getLogger(__name__)

class QueueService:
    """
    Service to manage queue operations.
    """
    
    def __init__(self, backend: Optional[QueueBackend] = None):
        self.backend = backend or self._init_backend()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}

    def _init_backend(self) -> QueueBackend:
        if hasattr(settings, "queue"):
            backend_type = settings.queue.backend
            db_path = settings.queue.sqlite_db_path
        else:
            backend_type = "sqlite"
            db_path = "queue.db"
        
        if backend_type == "sqlite":
            return SqliteQueueBackend(db_path=db_path)
        
        # Future: Redis, SQS, etc.
        raise ValueError(f"Unsupported queue backend: {backend_type}")

    def register_handler(self, task_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Register a handler function for a specific task name."""
        self._handlers[task_name] = handler
        logger.info(f"Registered handler for task: {task_name}")

    async def enqueue(self, task_name: str, payload: Dict[str, Any], **kwargs) -> str:
        """Enqueue a task."""
        message = QueueMessage(
            task_name=task_name,
            payload=payload,
            correlation_id=kwargs.get("correlation_id"),
            owner_id=kwargs.get("owner_id")
        )
        return await self.backend.enqueue(message)

    async def process_one(self) -> bool:
        """
        Process a single message from the queue.
        Returns True if a message was processed, False if queue was empty.
        """
        message = await self.backend.dequeue()
        if not message:
            return False

        try:
            handler = self._handlers.get(message.task_name)
            if not handler:
                logger.error(f"No handler found for task: {message.task_name}")
                # Nack with long delay or dead letter? For now, nack with delay
                await self.backend.nack(message.id, retry_after=60)
                return True

            logger.info(f"Processing task {message.task_name} (ID: {message.id})")
            await handler(message.payload)
            
            await self.backend.ack(message.id)
            return True

        except Exception as e:
            logger.error(f"Error processing task {message.task_name} (ID: {message.id}): {e}")
            # Exponential backoff: 5s, 10s, 20s, etc.
            retry_delay = 5 * (2 ** message.attempts)
            await self.backend.nack(message.id, retry_after=retry_delay)
            return True

    async def start_worker(self, interval: float = 1.0):
        """Start the worker loop (runs until cancelled)."""
        logger.info("Starting queue worker...")
        while True:
            try:
                processed = await self.process_one()
                if not processed:
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Worker stopped.")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)
