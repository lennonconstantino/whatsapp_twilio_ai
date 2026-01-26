from typing import List, Optional, Protocol, Dict
from src.core.database.interface import IRepository
from src.modules.ai.ai_result.models.ai_result import AIResult
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType

class IAIResultRepository(IRepository[AIResult], Protocol):
    """Interface for AI Result repository."""
    
    def find_by_message(self, msg_id: str, limit: int = 100) -> List[AIResult]:
        """Find AI results by message ID."""
        ...
    
    def find_by_feature(self, feature_id: str, limit: int = 100) -> List[AIResult]:
        """Find AI results by feature ID."""
        ...
        
    def find_recent_by_feature(self, feature_id: str, limit: int = 50) -> List[AIResult]:
        """Find recent AI results for a feature."""
        ...
        
    def create_result(
        self,
        msg_id: str,
        feature_id: int,
        result_json: dict,
        result_type: AIResultType = AIResultType.AGENT_LOG,
        correlation_id: Optional[str] = None
    ) -> Optional[AIResult]:
        """Create a new AI result."""
        ...
