"""
Message repository for database operations.
"""

from typing import Any, Dict, List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.core.utils.exceptions import DuplicateError
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.message import Message

logger = get_logger(__name__)


class MessageRepository(SupabaseRepository[Message]):
    """Repository for Message entity operations."""

    def __init__(self, client: Client):
        """Initialize message repository with ULID validation."""
        super().__init__(
            client, "messages", Message, validates_ulid=True
        )  # ✅ Enable ULID validation

    def create(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        Create a new message with unique constraint handling.
        """
        try:
            return super().create(data)
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

    def find_by_conversation(
        self, conv_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """
        Find messages by conversation ID.

        Args:
            conv_id: Conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of Message instances
        """
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

    def find_by_external_id(self, external_id: str) -> Optional[Message]:
        """
        Find message by external ID (Twilio MessageSid) stored in metadata.

        Args:
            external_id: External message ID (e.g. SM...)

        Returns:
            Message instance or None if not found
        """
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

    def find_recent_by_conversation(
        self, conv_id: str, limit: int = 10
    ) -> List[Message]:
        """
        Find recent messages from a conversation.

        Args:
            conv_id: Conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of recent Message instances (newest first)
        """
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

    def find_user_messages(self, conv_id: str, limit: int = 50) -> List[Message]:
        """
        Find user messages from a conversation.

        Args:
            conv_id: Conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of user Message instances
        """
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

    def count_by_conversation(self, conv_id: str) -> int:
        """
        Count messages in a conversation.

        Args:
            conv_id: Conversation ID

        Returns:
            Number of messages
        """
        return self.count({"conv_id": conv_id})
