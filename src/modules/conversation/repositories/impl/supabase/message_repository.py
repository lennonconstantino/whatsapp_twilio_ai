"""
Message repository for database operations.
"""

from typing import Any, Dict, List, Optional

from supabase import Client
from starlette.concurrency import run_in_threadpool

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.core.utils.exceptions import DuplicateError
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.message import Message
from src.modules.conversation.repositories.message_repository import MessageRepository

logger = get_logger(__name__)


class SupabaseMessageRepository(SupabaseRepository[Message], MessageRepository):
    """Repository for Message entity operations."""

    def __init__(self, client: Client):
        """Initialize message repository with ULID validation."""
        super().__init__(
            client, "messages", Message, validates_ulid=True
        )  # ✅ Enable ULID validation

    async def create(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        Create a new message with unique constraint handling.
        """
        def _create():
            try:
                return super(SupabaseMessageRepository, self).create(data)
            except Exception as e:
                # Check for unique violation (Postgres code 23505)
                # APIError from postgrest usually has 'code' attribute
                if hasattr(e, "code") and e.code == "23505":
                    logger.warning("Duplicate message detected", error=str(e))
                    raise DuplicateError(f"Duplicate message: {str(e)}")

                # Check message string if code not available (fallback)
                if "duplicate key value violates unique constraint" in str(e):
                    logger.warning("Duplicate message detected (text check)", error=str(e))
                    raise DuplicateError(f"Duplicate message: {str(e)}")

                raise e
        
        return await run_in_threadpool(_create)

    async def find_by_conversation(
        self, conv_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """
        Find messages by conversation ID.
        """
        def _find():
            try:
                result = (
                    self.client.table(self.table_name)
                    .select("*")
                    .eq("conv_id", conv_id)
                    .order("timestamp", desc=False)
                    .range(offset, offset + limit - 1)
                    .execute()
                )

                return [self.model_class(**item) for item in result.data]
            except Exception as e:
                logger.error("Error finding messages by conversation", error=str(e))
                raise
        
        return await run_in_threadpool(_find)

    async def find_by_external_id(self, external_id: str) -> Optional[Message]:
        """
        Find message by external ID (Twilio MessageSid) stored in metadata.
        """
        def _find():
            try:
                # Query JSONB column metadata ->> message_sid
                # Note: supabase-py / postgrest supports JSONB filtering
                result = (
                    self.client.table(self.table_name)
                    .select("*")
                    .eq("metadata->>message_sid", external_id)
                    .execute()
                )

                if result.data and len(result.data) > 0:
                    return self.model_class(**result.data[0])
                return None

            except Exception as e:
                logger.error(
                    "Error finding message by external ID",
                    external_id=external_id,
                    error=str(e),
                )
                raise
        
        return await run_in_threadpool(_find)

    async def find_recent_by_conversation(
        self, conv_id: str, limit: int = 10
    ) -> List[Message]:
        """
        Find recent messages from a conversation.
        """
        def _find():
            try:
                result = (
                    self.client.table(self.table_name)
                    .select("*")
                    .eq("conv_id", conv_id)
                    .order("timestamp", desc=True)
                    .limit(limit)
                    .execute()
                )

                # Return in chronological order (oldest first)
                messages = [self.model_class(**item) for item in result.data]
                return list(reversed(messages))
            except Exception as e:
                logger.error("Error finding recent messages", error=str(e))
                raise
        
        return await run_in_threadpool(_find)

    async def find_user_messages(self, conv_id: str, limit: int = 50) -> List[Message]:
        """
        Find user messages from a conversation.
        """
        def _find():
            try:
                result = (
                    self.client.table(self.table_name)
                    .select("*")
                    .eq("conv_id", conv_id)
                    .eq("message_owner", MessageOwner.USER.value)
                    .order("timestamp", desc=False)
                    .limit(limit)
                    .execute()
                )

                return [self.model_class(**item) for item in result.data]
            except Exception as e:
                logger.error("Error finding user messages", error=str(e))
                raise
        
        return await run_in_threadpool(_find)

    async def count_by_conversation(self, conv_id: str) -> int:
        """
        Count messages in a conversation.
        """
        def _count():
            return self.count({"conv_id": conv_id})
        
        return await run_in_threadpool(_count)
