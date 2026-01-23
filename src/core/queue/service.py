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
            redis_url = getattr(settings.queue, "redis_url", "redis://localhost:6379")
        else:
            backend_type = "sqlite"
            db_path = "queue.db"
            redis_url = "redis://localhost:6379"
        
        if backend_type == "sqlite":
            return SqliteQueueBackend(db_path=db_path)
        
        if backend_type == "bullmq":
            from .backends.bullmq import BullMQBackend
            return BullMQBackend(redis_url=redis_url)
        
        # Future: SQS, etc.
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

    async def _process_message(self, message: QueueMessage):
        """
        Internal handler used by the backend consumer.
        """
        handler = self._handlers.get(message.task_name)
        if not handler:
            logger.error(f"No handler found for task: {message.task_name}")
            raise ValueError(f"No handler found for task: {message.task_name}")

        logger.info(f"Processing task {message.task_name} (ID: {message.id})")
        await handler(message.payload)

    async def start_worker(self, interval: float = 1.0):
        """
        Start the worker loop (runs until cancelled).
        Delegates to backend's start_consuming which handles the loop mechanism (pull vs push).
        """
        logger.info("Starting queue worker service...")
        
        # We pass self._process_message as the handler to the backend.
        # The backend is responsible for:
        # 1. Fetching/Receiving message
        # 2. Calling this handler
        # 3. Ack/Nack based on success/failure
        
        await self.backend.start_consuming(self._process_message)
