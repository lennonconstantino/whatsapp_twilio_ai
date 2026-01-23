import json
import logging
from typing import Optional, Callable, Awaitable
from bullmq import Queue, Worker
from redis import asyncio as aioredis

from ..interfaces import QueueBackend
from ..models import QueueMessage
from src.core.config import settings

logger = logging.getLogger(__name__)

class BullMQBackend(QueueBackend):
    """
    BullMQ backend implementation.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.queue_name = "default_queue"
        # Parse redis_url to dict for bullmq
        # redis://[:password@]host[:port][/db]
        self.redis_opts = self._parse_redis_url(redis_url)
        
        self.queue = Queue(self.queue_name, {"connection": self.redis_opts})
        self.worker: Optional[Worker] = None

    def _parse_redis_url(self, url: str) -> dict:
        """
        Parse redis url into dictionary.
        """
        conn = aioredis.from_url(url)
        # conn.connection_pool.connection_kwargs contains:
        # host, port, db, password, etc.
        kwargs = conn.connection_pool.connection_kwargs
        return {
            "host": kwargs.get("host"),
            "port": kwargs.get("port"),
            "password": kwargs.get("password"),
            "db": kwargs.get("db", 0)
        }

    async def enqueue(self, message: QueueMessage) -> str:
        """Add message to queue."""
        # BullMQ job data
        job_data = message.model_dump(mode='json')
        
        # We map message.task_name to job name, but BullMQ uses job name for processor routing usually.
        # Here we use a generic processor, so job name can be the task name.
        job = await self.queue.add(message.task_name, job_data, {
            "jobId": message.id, # Use our ID as job ID
            "removeOnComplete": True,
            "removeOnFail": False # Keep failed jobs for inspection
        })
        return str(job.id)

    async def dequeue(self) -> Optional[QueueMessage]:
        """
        BullMQ is push-based mostly via Worker. 
        Manual dequeue is complex. We rely on start_consuming.
        """
        raise NotImplementedError("BullMQ backend supports start_consuming only")

    async def ack(self, message_id: str) -> None:
        """Handled by Worker automatically on success."""
        pass

    async def nack(self, message_id: str, retry_after: int = 0) -> None:
        """Handled by Worker automatically on failure."""
        pass

    async def start_consuming(self, handler: Callable[[QueueMessage], Awaitable[None]]) -> None:
        """
        Start BullMQ Worker.
        """
        async def process_job(job, token):
            # Convert job.data back to QueueMessage
            # job.data is the dict we dumped in enqueue
            try:
                # job.data might contain the full message dump or just payload
                # We dumped full message in enqueue: job_data = message.model_dump(...)
                
                # Reconstruct QueueMessage
                # Ensure datetime fields are parsed correctly if JSON
                message = QueueMessage(**job.data)
                
                logger.info(f"Processing BullMQ job {job.id} (Task: {message.task_name})")
                
                await handler(message)
                
                return "completed"
            except Exception as e:
                logger.error(f"Error processing BullMQ job {job.id}: {e}")
                raise e # BullMQ Worker handles this as failure/retry

        logger.info(f"Starting BullMQ Worker on queue '{self.queue_name}'...")
        
        self.worker = Worker(
            self.queue_name, 
            process_job, 
            {"connection": self.redis_opts}
        )
        
        # Worker runs in background. We need to keep this method alive if it's expected to block.
        # But QueueService.start_worker expects to control the loop?
        # No, if we override start_consuming, we take control.
        # But BullMQ Worker runs autonomously. We should block here to keep process alive.
        
        # We can use a specialized waiting event
        stop_event = asyncio.Event()
        try:
            await stop_event.wait() # Block forever until cancelled
        except asyncio.CancelledError:
            logger.info("Stopping BullMQ Worker...")
            await self.worker.close()
            await self.queue.close()
