from typing import Any, Dict, List, Optional

from psycopg2 import sql
from psycopg2.extras import Json, RealDictCursor

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.core.utils import get_logger
from src.core.utils.exceptions import DuplicateError
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.message import Message

logger = get_logger(__name__)


class PostgresMessageRepository(PostgresRepository[Message]):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "messages", Message)

    def create(self, data: Dict[str, Any]) -> Optional[Message]:
        try:
            data = {**data}
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"] = Json(data["metadata"])
            return super().create(data)
        except Exception as e:
            if "duplicate key value violates unique constraint" in str(e):
                raise DuplicateError(f"Duplicate message: {str(e)}")
            raise

    def find_by_conversation(
        self, conv_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE conv_id = %s "
            "ORDER BY timestamp ASC "
            "LIMIT %s OFFSET %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (conv_id, limit, offset))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

    def find_recent_by_conversation(self, conv_id: str, limit: int = 10) -> List[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE conv_id = %s "
            "ORDER BY timestamp DESC "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (conv_id, limit))
                rows = cur.fetchall()
                messages = [self.model_class(**r) for r in rows]
                return list(reversed(messages))
            finally:
                cur.close()

    def find_by_external_id(self, external_id: str) -> Optional[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE metadata->>'message_sid' = %s LIMIT 1"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (external_id,))
                row = cur.fetchone()
                return self.model_class(**row) if row else None
            finally:
                cur.close()

    def find_user_messages(self, conv_id: str, limit: int = 50) -> List[Message]:
        query = sql.SQL(
            "SELECT * FROM messages WHERE conv_id = %s AND message_owner = %s "
            "ORDER BY timestamp ASC "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (conv_id, MessageOwner.USER.value, limit))
                rows = cur.fetchall()
                return [self.model_class(**r) for r in rows]
            finally:
                cur.close()

