from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable, Awaitable
import asyncio
from .models import QueueMessage

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
    
    async def start_consuming(self, handler: Callable[[QueueMessage], Awaitable[None]]) -> None:
        """
        Start consuming messages and pass them to handler.
        This method might block or run forever.
        Default implementation for pull-based backends (polling).
        """
        while True:
            try:
                msg = await self.dequeue()
                if msg:
                    try:
                        await handler(msg)
                        await self.ack(msg.id)
                    except Exception as e:
                        # Logic for retry should be handled by backend specific nack
                        # But here we can calculate retry
                        await self.nack(msg.id, retry_after=10) # Default retry
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)
