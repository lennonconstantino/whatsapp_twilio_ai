from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
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
