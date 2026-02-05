import asyncio
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

from src.core.utils.logging import get_logger
from .models import QueueMessage

logger = get_logger(__name__)


class QueueBackend(ABC):
    """
    Abstract base class for queue backends.
    """

    @abstractmethod
    async def enqueue(self, message: QueueMessage) -> str:
        """
        Add a message to the queue.
        Returns the message ID.
        """
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[QueueMessage]:
        """
        Retrieve and lock the next message from the queue.
        Returns None if queue is empty.
        Used by pull-based backends.
        """
        pass

    @abstractmethod
    async def ack(self, message_id: str) -> None:
        """
        Acknowledge successful processing of a message.
        Removes the message from the queue.
        """
        pass

    @abstractmethod
    async def nack(self, message_id: str, retry_after: int = 0) -> None:
        """
        Negative acknowledgement.
        Return message to queue, potentially with a delay.
        """
        pass

    @abstractmethod
    async def fail(self, message_id: str, error: str = "") -> None:
        """
        Mark message as permanently failed (DLQ).
        """
        pass

    async def start_consuming(
        self, handler: Callable[[QueueMessage], Awaitable[None]]
    ) -> None:
        """
        Start consuming messages and pass them to handler.
        This method might block or run forever.
        Default implementation for pull-based backends (polling).
        """
        MAX_RETRIES = 3  # Hardcoded for now, or move to settings

        logger.info("Starting consumer loop", backend=self.__class__.__name__)

        while True:
            try:
                msg = await self.dequeue()
                if msg:
                    try:
                        await handler(msg)
                        await self.ack(msg.id)
                    except Exception as e:
                        # Check max retries
                        if msg.attempts >= MAX_RETRIES:
                            logger.error(
                                "Message failed permanently",
                                message_id=msg.id,
                                attempts=msg.attempts,
                                error=str(e),
                            )
                            await self.fail(msg.id, error=str(e))
                        else:
                            # Exponential backoff: 10s, 20s, 40s...
                            retry_after = 10 * (2 ** msg.attempts)
                            logger.warning(
                                "Message failed, retrying",
                                message_id=msg.id,
                                attempts=msg.attempts,
                                retry_after=retry_after,
                                error=str(e),
                            )
                            await self.nack(msg.id, retry_after=retry_after)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                break
            except Exception as e:
                logger.error("Error in consumer loop", error=str(e))
                await asyncio.sleep(5)
