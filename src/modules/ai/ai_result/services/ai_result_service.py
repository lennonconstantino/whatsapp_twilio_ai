"""
AI Result service for managing AI processing results.
"""
from typing import Optional, List, Dict, Any

from src.modules.ai.ai_result.models.ai_result import AIResult
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.ai_result.repositories.ai_result_repository import AIResultRepository
from src.core.utils import get_logger, get_db

logger = get_logger(__name__)


class AIResultService:
    """
    Service for AI result management.
    
    Responsibilities:
    - Store AI processing results
    - Retrieve results by message or feature
    - Analyze processing history
    """
    
    def __init__(
        self,
        ai_result_repo: Optional[AIResultRepository] = None
    ):
        """
        Initialize the service.
        
        Args:
            ai_result_repo: AI Result repository
        """
        db_client = get_db()
        self.ai_result_repo = ai_result_repo or AIResultRepository(db_client)
    
    def create_result(
        self,
        msg_id: str,
        feature_id: int,
        result_json: Dict[str, Any],
        result_type: AIResultType = AIResultType.AGENT_LOG,
        correlation_id: Optional[str] = None
    ) -> Optional[AIResult]:
        """
        Create a new AI processing result.
        
        Args:
            msg_id: Message ID (ULID)
            feature_id: Feature ID that processed the message
            result_json: AI processing result data
            result_type: Type of result (TOOL, AGENT_LOG)
            correlation_id: Optional Trace ID
            
        Returns:
            Created AIResult or None
        """
        try:
            result = self.ai_result_repo.create_result(
                msg_id=msg_id,
                feature_id=feature_id,
                result_json=result_json,
                result_type=result_type,
                correlation_id=correlation_id
            )
            
            logger.info(
                "AI result created",
                ai_result_id=result.ai_result_id if result else None,
                msg_id=msg_id,
                feature_id=feature_id,
                result_type=result_type.value if hasattr(result_type, 'value') else result_type,
                correlation_id=correlation_id
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Error creating AI result",
                msg_id=msg_id,
                feature_id=feature_id,
                correlation_id=correlation_id,
                error=str(e)
            )
            raise
    
    def get_results_by_message(
        self,
        msg_id: str,
        limit: int = 100
    ) -> List[AIResult]:
        """
        Get all AI results for a message.
        
        Args:
            msg_id: Message ID (ULID)
            limit: Maximum number of results
            
        Returns:
            List of AIResult instances
        """
        return self.ai_result_repo.find_by_message(msg_id, limit)
    
    def get_results_by_feature(
        self,
        feature_id: int,
        limit: int = 100
    ) -> List[AIResult]:
        """
        Get all AI results for a feature.
        
        Args:
            feature_id: Feature ID
            limit: Maximum number of results
            
        Returns:
            List of AIResult instances
        """
        return self.ai_result_repo.find_by_feature(feature_id, limit)
    
    def get_recent_results_by_feature(
        self,
        feature_id: int,
        limit: int = 50
    ) -> List[AIResult]:
        """
        Get recent AI results for a feature.
        
        Args:
            feature_id: Feature ID
            limit: Maximum number of results
            
        Returns:
            List of recent AIResult instances
        """
        return self.ai_result_repo.find_recent_by_feature(feature_id, limit)
    
    def get_result_by_id(self, ai_result_id: int) -> Optional[AIResult]:
        """
        Get an AI result by ID.
        
        Args:
            ai_result_id: AI Result ID
            
        Returns:
            AIResult or None
        """
        return self.ai_result_repo.find_by_id(
            ai_result_id,
            id_column="ai_result_id"
        )
    
    def analyze_feature_performance(
        self,
        feature_id: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze AI feature performance based on results.
        
        Args:
            feature_id: Feature ID
            limit: Number of recent results to analyze
            
        Returns:
            Performance metrics dictionary
        """
        results = self.get_recent_results_by_feature(feature_id, limit)
        
        if not results:
            return {
                "feature_id": feature_id,
                "total_results": 0,
                "message": "No results found"
            }
        
        # Calculate basic metrics
        total = len(results)
        
        # Extract processing times if available
        processing_times = []
        for result in results:
            if "processing_time" in result.result_json:
                processing_times.append(result.result_json["processing_time"])
        
        metrics = {
            "feature_id": feature_id,
            "total_results": total,
            "first_result": results[-1].processed_at if results else None,
            "last_result": results[0].processed_at if results else None,
        }
        
        if processing_times:
            metrics["avg_processing_time"] = sum(processing_times) / len(processing_times)
            metrics["min_processing_time"] = min(processing_times)
            metrics["max_processing_time"] = max(processing_times)
        
        # Extract success/error rates if available
        successes = sum(
            1 for r in results 
            if r.result_json.get("status") == "success"
        )
        errors = sum(
            1 for r in results 
            if r.result_json.get("status") == "error"
        )
        
        if successes or errors:
            metrics["success_rate"] = successes / total if total > 0 else 0
            metrics["error_rate"] = errors / total if total > 0 else 0
        
        return metrics
    
    def delete_old_results(
        self,
        days: int = 90,
        limit: int = 1000
    ) -> int:
        """
        Delete AI results older than specified days.
        (For data retention policies)
        
        Args:
            days: Number of days to keep results
            limit: Maximum number of results to delete at once
            
        Returns:
            Number of results deleted
        """
        # This would need a custom query with date filtering
        # For now, return 0 as placeholder
        logger.info(f"Delete old results not implemented yet (days={days})")
        return 0
