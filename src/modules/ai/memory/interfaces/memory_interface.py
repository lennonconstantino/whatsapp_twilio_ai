from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional

class MemoryInterface(ABC):
    """
    Interface for Memory Management (L1 Cache, L2 Persistence, L3 Vector).
    Responsible for retrieving and storing conversation context.
    """

    @abstractmethod
    async def get_context(
        self,
        session_id: str,
        limit: int = 10,
        query: Optional[str] = None,
        owner_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the conversation history for a given session.
        Returns a list of messages in a dict format compatible with the Agent (role/content).
        
        Args:
            session_id: The session/conversation ID.
            limit: Max number of recent messages.
            query: Optional query string for semantic search (L3).
            owner_id: Optional owner/tenant scope for retrieval filters.
            user_id: Optional user scope for retrieval filters.
        """
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Adds a message to the conversation history.
        """
        pass
