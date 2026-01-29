from abc import ABC, abstractmethod
from typing import List, Any, Dict

class MemoryInterface(ABC):
    """
    Interface for Memory Management (L1 Cache, L2 Persistence, L3 Vector).
    Responsible for retrieving and storing conversation context.
    """

    @abstractmethod
    def get_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the conversation history for a given session.
        Returns a list of messages in a dict format compatible with the Agent (role/content).
        """
        pass

    @abstractmethod
    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Adds a message to the conversation history.
        """
        pass
