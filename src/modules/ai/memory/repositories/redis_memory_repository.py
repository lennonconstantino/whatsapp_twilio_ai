import json
from typing import Any, Dict, List, Optional

import redis

from src.core.utils.logging import get_logger
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface

logger = get_logger(__name__)


class RedisMemoryRepository(MemoryInterface):
    """
    Redis implementation of MemoryInterface (L1 Cache).
    Stores chat history as a list of JSON strings.
    Synchronous implementation to be compatible with current Agent architecture.
    """

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Connection string (e.g. redis://localhost:6379)
            ttl_seconds: Expiration time for keys (default 1h)
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self._disabled = False
        self._disabled_reason: str | None = None

    def _disable(self, reason: str) -> None:
        if self._disabled:
            return
        self._disabled = True
        self._disabled_reason = reason
        logger.warning(
            "Redis indisponível; desativando cache de memória (L1)",
            redis_url=self.redis_url,
            reason=reason,
        )

    def get_context(self, session_id: str, limit: int = 10, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the last N messages from Redis list.
        Ignores query (L1 Cache is purely chronological).
        """
        if self._disabled:
            return []

        key = self._get_key(session_id)
        try:
            # Get last N messages (Redis lists are 0-indexed)
            # lrange(key, -limit, -1) gets the last N elements
            raw_messages = self.redis.lrange(key, -limit, -1)
            
            messages = []
            for raw_msg in raw_messages:
                try:
                    messages.append(json.loads(raw_msg))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode message from Redis key {key}: {raw_msg}")
                    continue
            
            return messages
        except redis.exceptions.ConnectionError as e:
            self._disable(str(e))
            return []
        except Exception as e:
            logger.error(f"Error reading context from Redis for {session_id}: {e}")
            return []

    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Appends a message to the Redis list and refreshes TTL.
        """
        if self._disabled:
            return

        key = self._get_key(session_id)
        try:
            json_msg = json.dumps(message)
            with self.redis.pipeline() as pipe:
                pipe.rpush(key, json_msg)
                # Keep only last 50 messages to avoid infinite growth if TTL is refreshed often
                pipe.ltrim(key, -50, -1) 
                pipe.expire(key, self.ttl_seconds)
                pipe.execute()
        except redis.exceptions.ConnectionError as e:
            self._disable(str(e))
        except Exception as e:
            logger.error(f"Error adding message to Redis for {session_id}: {e}")

    def _get_key(self, session_id: str) -> str:
        return f"ai:memory:{session_id}"
