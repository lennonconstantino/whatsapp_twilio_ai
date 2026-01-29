from typing import Any, Dict

from starlette.concurrency import run_in_threadpool

from src.core.utils.logging import get_logger
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository

logger = get_logger(__name__)


class EmbeddingTasks:
    """
    Handlers for AI embedding background tasks.
    """

    def __init__(self, vector_repo: VectorMemoryRepository):
        self.vector_repo = vector_repo

    async def generate_embedding(self, payload: Dict[str, Any]):
        """
        Generate embedding for a message and save to vector store.
        Payload: {
            "content": str,
            "metadata": Dict
        }
        """
        content = payload.get("content")
        metadata = payload.get("metadata")
        
        if not content or not isinstance(content, str):
            logger.warning("Skipping embedding generation: Invalid content")
            return

        msg_id = metadata.get("msg_id", "unknown") if metadata else "unknown"
        logger.info(f"Generating embedding for message: {msg_id}")
        
        try:
            # Run blocking operations (Embedding API + DB Insert) in threadpool
            await run_in_threadpool(
                self.vector_repo.add_texts,
                texts=[content],
                metadatas=[metadata] if metadata else [{}]
            )
            logger.info(f"Embedding generated successfully for {msg_id}")
        except Exception as e:
            logger.error(f"Error generating embedding for {msg_id}: {e}")
            raise e
