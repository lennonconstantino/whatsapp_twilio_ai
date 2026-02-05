from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.ai_result.models.ai_result import AIResult


class AIResultRepository(ABC):
    """
    Abstract Base Class for AI Result Repository.
    Defines the contract for AI result data access.
    """

    @abstractmethod
    def find_by_message(self, msg_id: str, limit: int = 100) -> List[AIResult]:
        """Find AI results by message ID."""
        pass

    @abstractmethod
    def find_by_feature(self, feature_id: str, limit: int = 100) -> List[AIResult]:
        """Find AI results by feature ID."""
        pass

    @abstractmethod
    def find_recent_by_feature(
        self, feature_id: str, limit: int = 50
    ) -> List[AIResult]:
        """Find recent AI results for a feature."""
        pass

    @abstractmethod
    def create_result(
        self,
        msg_id: str,
        feature_id: int,
        result_json: dict,
        result_type: AIResultType = AIResultType.AGENT_LOG,
        correlation_id: Optional[str] = None,
    ) -> Optional[AIResult]:
        """Create a new AI result."""
        pass

    @abstractmethod
    def delete_older_than(self, days: int) -> int:
        """Delete AI results older than N days."""
        pass
