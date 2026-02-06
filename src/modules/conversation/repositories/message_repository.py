from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.modules.conversation.models.message import Message


class MessageRepository(ABC):
    """
    Abstract Base Class for Message Repository.
    Defines the contract for message data access.
    """

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Optional[Message]:
        """Create a new message."""
        pass

    @abstractmethod
    async def find_by_id(self, id_value: Any, id_column: Optional[str] = None) -> Optional[Message]:
        """Find a message by ID."""
        pass

    @abstractmethod
    async def update(
        self,
        id_value: Any,
        data: Dict[str, Any],
        id_column: Optional[str] = None,
        current_version: Optional[int] = None,
    ) -> Optional[Message]:
        """Update a message."""
        pass

    @abstractmethod
    async def find_by_conversation(
        self, conv_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """Find messages by conversation ID."""
        pass

    @abstractmethod
    async def find_by_external_id(self, external_id: str) -> Optional[Message]:
        """Find message by external ID."""
        pass

    @abstractmethod
    async def find_recent_by_conversation(
        self, conv_id: str, limit: int = 10
    ) -> List[Message]:
        """Find recent messages from a conversation."""
        pass

    @abstractmethod
    async def find_user_messages(self, conv_id: str, limit: int = 50) -> List[Message]:
        """Find user messages from a conversation."""
        pass

    @abstractmethod
    async def count_by_conversation(self, conv_id: str) -> int:
        """Count messages in a conversation."""
        pass
