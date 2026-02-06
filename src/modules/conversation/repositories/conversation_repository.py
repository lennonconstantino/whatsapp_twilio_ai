from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation


class ConversationRepository(ABC):
    """
    Abstract Base Class for Conversation Repository.
    Defines the contract for conversation data access.
    """

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """Create a new conversation."""
        pass

    @abstractmethod
    async def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[Conversation]:
        """Find conversation by ID."""
        pass

    @abstractmethod
    async def update(
        self,
        id_value: Any,
        data: Dict[str, Any],
        id_column: str = "id",
        current_version: Optional[int] = None,
    ) -> Optional[Conversation]:
        """Update a conversation."""
        pass

    @abstractmethod
    async def find_active_by_session_key(
        self, owner_id: str, session_key: str
    ) -> Optional[Conversation]:
        """Find active conversation by session key."""
        pass

    @abstractmethod
    async def find_active_by_owner(
        self, owner_id: str, limit: int = 100
    ) -> List[Conversation]:
        """Find all active conversations for an owner."""
        pass

    @abstractmethod
    async def find_by_status(
        self,
        owner_id: str,
        status: ConversationStatus,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Conversation]:
        """Find conversations by status and optional agent_id."""
        pass

    @abstractmethod
    async def find_all_by_session_key(
        self, owner_id: str, session_key: str, limit: int = 10
    ) -> List[Conversation]:
        """Find all conversations for a session key (including closed ones)."""
        pass

    @abstractmethod
    async def find_expired_candidates(self, limit: int = 100) -> List[Conversation]:
        """Find active conversations that have passed their expiration time."""
        pass

    @abstractmethod
    async def find_idle_candidates(
        self, idle_threshold_iso: Union[str, datetime], limit: int = 100
    ) -> List[Conversation]:
        """Find conversations that have been idle since before the threshold."""
        pass

    @abstractmethod
    async def update_context(
        self, conv_id: str, context: dict, expected_version: Optional[int] = None
    ) -> Optional[Conversation]:
        """Update conversation context."""
        pass

    @abstractmethod
    async def update_timestamp(self, conv_id: str) -> Optional[Conversation]:
        """Update conversation timestamp."""
        pass

    @staticmethod
    @abstractmethod
    def calculate_session_key(number1: str, number2: str) -> str:
        """Calculate session key from two numbers."""
        pass

    @abstractmethod
    async def find_by_session_key(
        self, owner_id: str, from_number: str, to_number: str
    ) -> Optional[Conversation]:
        """Find active conversation by calculating session key."""
        pass

    @abstractmethod
    async def update_status(
        self,
        conv_id: str,
        status: ConversationStatus,
        *,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        ended_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        force: bool = False,
    ) -> Optional[Conversation]:
        """Update conversation status."""
        pass

    @abstractmethod
    async def cleanup_expired_conversations(self, limit: int = 100) -> int:
        """Process expiration for expired conversations."""
        pass

    @abstractmethod
    async def close_by_message_policy(
        self,
        conv: Conversation,
        *,
        should_close: bool,
        message_owner: Any,
        message_text: Optional[str] = None,
    ) -> bool:
        """Close conversation based on message policy."""
        pass

    # Methods that might be duplicates but exist in Supabase implementation
    # Included for compatibility
    async def find_idle_conversations(
        self, idle_minutes: int, limit: int = 100
    ) -> List[Conversation]:
        """Find idle conversations (optional implementation)."""
        # Default implementation could be raising NotImplementedError or bridging to find_idle_candidates
        raise NotImplementedError("find_idle_conversations not implemented")

    async def find_expired_conversations(self, limit: int = 100) -> List[Conversation]:
        """Find expired conversations (alias for find_expired_candidates)."""
        return await self.find_expired_candidates(limit)
