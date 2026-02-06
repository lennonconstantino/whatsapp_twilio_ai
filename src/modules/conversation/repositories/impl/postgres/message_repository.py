import json
from typing import Any, Dict, List, Optional

from psycopg2 import sql
# from psycopg2.extras import Json, RealDictCursor # Removed

from src.core.database.postgres_async_repository import PostgresAsyncRepository
from src.core.database.postgres_async_session import AsyncPostgresDatabase
from src.core.utils import get_logger
from src.core.utils.exceptions import DuplicateError
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.message import Message
from src.modules.conversation.repositories.message_repository import MessageRepository

logger = get_logger(__name__)


class PostgresMessageRepository(PostgresAsyncRepository[Message], MessageRepository):
    def __init__(self, db: AsyncPostgresDatabase):
        super().__init__(db, "messages", Message)

    async def create(self, data: Dict[str, Any]) -> Optional[Message]:
        try:
            data = {**data}
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"] = json.dumps(data["metadata"])
            return await super().create(data)
        except Exception as e:
            # asyncpg errors are different. 
            # asyncpg.exceptions.UniqueViolationError
            if "duplicate key value violates unique constraint" in str(e) or "UniqueViolationError" in str(e):
                raise DuplicateError(f"Duplicate message: {str(e)}")
            raise

    async def find_by_conversation(
        self, conv_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE conv_id = %s "
            "ORDER BY timestamp ASC "
            "LIMIT %s OFFSET %s"
        )
        
        rows = await self._execute_query(query, (conv_id, limit, offset), fetch_all=True)
        return [self.model_class(**r) for r in rows]

    async def count_by_conversation(self, conv_id: str) -> int:
        query = sql.SQL("SELECT COUNT(*) as count FROM messages WHERE conv_id = %s")
        
        result = await self._execute_query(query, (conv_id,), fetch_one=True)
        return result["count"] if result else 0

    async def find_recent_by_conversation(self, conv_id: str, limit: int = 10) -> List[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE conv_id = %s "
            "ORDER BY timestamp DESC "
            "LIMIT %s"
        )
        
        rows = await self._execute_query(query, (conv_id, limit), fetch_all=True)
        messages = [self.model_class(**r) for r in rows]
        return list(reversed(messages))

    async def find_by_external_id(self, external_id: str) -> Optional[Message]:
        # JSONB operator ->> 
        query = sql.SQL(
            "SELECT * FROM messages WHERE metadata->>'message_sid' = %s LIMIT 1"
        )
        
        result = await self._execute_query(query, (external_id,), fetch_one=True)
        return self.model_class(**result) if result else None

    async def find_user_messages(self, conv_id: str, limit: int = 50) -> List[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE conv_id = %s AND message_owner = %s "
            "ORDER BY timestamp ASC "
            "LIMIT %s"
        )
        
        rows = await self._execute_query(query, (conv_id, MessageOwner.USER.value, limit), fetch_all=True)
        return [self.model_class(**r) for r in rows]
