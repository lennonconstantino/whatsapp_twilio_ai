from typing import Any, Dict, List

from src.core.utils.logging import get_logger
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface
from src.modules.ai.memory.repositories.redis_memory_repository import RedisMemoryRepository
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.conversation.enums.message_owner import MessageOwner

logger = get_logger(__name__)


class HybridMemoryService(MemoryInterface):
    """
    Hybrid Memory Service (L1 Cache + L2 Persistence).
    Orchestrates data flow between Redis and PostgreSQL.
    """

    def __init__(
        self,
        redis_repo: RedisMemoryRepository,
        message_repo: MessageRepository,
    ):
        self.redis_repo = redis_repo
        self.message_repo = message_repo

    def get_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves context with Read-Through strategy:
        1. Try L1 (Redis)
        2. If miss, try L2 (DB) and populate L1
        """
        # 1. Try Redis
        try:
            messages = self.redis_repo.get_context(session_id, limit)
            if messages:
                logger.debug(f"Cache HIT for session {session_id}")
                return messages
        except Exception as e:
            logger.warning(f"Error reading from Redis: {e}")

        # 2. Fallback to DB
        logger.debug(f"Cache MISS for session {session_id}. Fetching from DB.")
        try:
            # session_id is conversation_id (conv_id)
            db_messages = self.message_repo.find_recent_by_conversation(session_id, limit)
            
            if not db_messages:
                return []

            # Convert to Agent format
            agent_messages = []
            for msg in db_messages:
                # Map Message entity to Agent dict format
                role = "user" if msg.message_owner == MessageOwner.USER else "assistant"
                content = msg.body or ""
                
                # Basic validation
                if not content.strip():
                    continue
                    
                formatted_msg = {
                    "role": role,
                    "content": content
                }
                agent_messages.append(formatted_msg)

            # 3. Populate Redis (Async ideally, but sync for now)
            # We need to add them to Redis.
            # RedisMemoryRepository.add_message appends to list.
            # Since we have the whole list, we might want to bulk set, 
            # but RedisMemoryRepository only has add_message.
            # For now, let's just add them one by one or create a bulk method later.
            # CAUTION: If we append one by one, we might duplicate if not careful.
            # But Redis cache was empty (MISS), so it should be fine.
            # However, find_recent_by_conversation returns OLD -> NEW.
            # So we can just push them.
            
            # Optimization: Only populate if list is not empty
            if agent_messages:
                # We should probably clear the key first to be safe, but TTL should handle it.
                # If cache was partial miss (unlikely with list), we might append duplicates.
                # Ideally, we should set the whole list.
                # But RedisMemoryRepository doesn't expose 'set_context'.
                # Let's just return DB result for now and let the NEXT user message trigger an add.
                # Wait, Read-Through implies populating the cache on read.
                
                # Let's iterate and add.
                for msg in agent_messages:
                    self.redis_repo.add_message(session_id, msg)
                    
            return agent_messages

        except Exception as e:
            logger.error(f"Error reading from DB for session {session_id}: {e}")
            return []

    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Adds message to Memory (Write-Through or Write-Back).
        In our architecture:
        - DB write happens in Webhook (Source of Truth).
        - Here we just update the Cache (Redis).
        """
        # We assume DB is already updated by the time this is called, 
        # OR this is called by Agent to "remember" something (but Agent relies on Webhook for persistence).
        # Actually, Agent sends response -> Webhook -> DB.
        # Then Webhook should update Cache.
        # But if Agent calls memory.add_message, it's updating the "Thought" memory?
        # The MemoryInterface is for Conversation History.
        
        # If the Agent adds a message here, it should be reflected in Redis.
        self.redis_repo.add_message(session_id, message)
