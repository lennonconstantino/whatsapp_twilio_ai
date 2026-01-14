"""
AI Result repository for database operations.
"""
from typing import List, Optional
from supabase import Client

from src.core.database.base_repository import BaseRepository
from src.core.models import AIResult
from src.core.utils import get_logger

logger = get_logger(__name__)


class AIResultRepository(BaseRepository[AIResult]):
    """Repository for AIResult entity operations."""
    
    def __init__(self, client: Client):
        """Initialize AI result repository with ULID validation."""
        super().__init__(client, "ai_results", AIResult, validates_ulid=True)  # ✅ Enable ULID validation
    
    def find_by_message(self, msg_id: str, limit: int = 100) -> List[AIResult]:
        """
        Find AI results by message ID.
        
        Args:
            msg_id: Message ID
            limit: Maximum number of results to return
            
        Returns:
            List of AIResult instances
        """
        return self.find_by({"msg_id": msg_id}, limit=limit)
    
    def find_by_feature(
        self,
        feature_id: str,
        limit: int = 100
    ) -> List[AIResult]:
        """
        Find AI results by feature ID.
        
        Args:
            feature_id: Feature ID
            limit: Maximum number of results to return
            
        Returns:
            List of AIResult instances
        """
        return self.find_by({"feature_id": feature_id}, limit=limit)
    
    def find_recent_by_feature(
        self,
        feature_id: str,
        limit: int = 50
    ) -> List[AIResult]:
        """
        Find recent AI results for a feature.
        
        Args:
            feature_id: Feature ID
            limit: Maximum number of results to return
            
        Returns:
            List of recent AIResult instances
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("feature_id", feature_id)\
                .order("processed_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding recent AI results", error=str(e))
            raise
    
    def create_result(
        self,
        msg_id: str,
        feature_id: str,
        result_json: dict
    ) -> Optional[AIResult]:
        """
        Create a new AI result.
        
        Args:
            msg_id: Message ID
            feature_id: Feature ID
            result_json: AI processing result
            
        Returns:
            Created AIResult instance or None
        """
        data = {
            "msg_id": msg_id,
            "feature_id": feature_id,
            "result_json": result_json
        }
        return self.create(data)
