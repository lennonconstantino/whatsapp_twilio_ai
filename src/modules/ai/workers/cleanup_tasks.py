from dependency_injector.wiring import Provide, inject

from src.core.config import settings
from src.core.di.container import Container
from src.core.utils import get_logger
from src.modules.ai.ai_result.repositories.ai_result_repository import (
    AIResultRepository,
)

logger = get_logger(__name__)


class AICleanupTasks:
    """Tasks for AI data cleanup."""

    @inject
    def __init__(
        self,
        ai_result_repo: AIResultRepository = Provide[Container.ai_result_repository],
    ):
        self.ai_result_repo = ai_result_repo

    async def cleanup_old_logs(self, payload: dict) -> dict:
        """
        Delete AI logs older than configured retention period.
        
        Args:
            payload: Job payload (can override retention_days)
        """
        retention_days = payload.get("retention_days", settings.ai.log_retention_days)
        
        logger.info("Starting AI log cleanup", retention_days=retention_days)
        
        try:
            # Note: This is a synchronous call (repository is sync/not async def)
            # If the repository becomes async, we should await it.
            # Based on inspection, Supabase/Postgres implementations are sync methods 
            # (they don't use async def).
            count = self.ai_result_repo.delete_older_than(days=retention_days)
            
            logger.info("AI log cleanup completed", deleted_count=count)
            return {"status": "success", "deleted_count": count}
        except Exception as e:
            logger.error("AI log cleanup failed", error=str(e))
            raise
