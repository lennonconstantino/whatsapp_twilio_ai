"""
Conversation Finder component (V2).
Responsible for finding and creating conversations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.utils import get_logger
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository

logger = get_logger(__name__)


class ConversationFinder:
    """
    Component responsible for locating active conversations or creating new ones.
    Encapsulates session key calculation and history lookup.
    """

    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    def calculate_session_key(self, number1: str, number2: str) -> str:
        """
        Calculate session key for two phone numbers.
        The session key is always the same regardless of order.
        """
        # Normalize: ensure both have whatsapp: prefix
        clean1 = number1.strip()
        clean2 = number2.strip()

        if not clean1.startswith("whatsapp:"):
            clean1 = f"whatsapp:{clean1}"
        if not clean2.startswith("whatsapp:"):
            clean2 = f"whatsapp:{clean2}"

        # Sort alphabetically to ensure consistency
        numbers = sorted([clean1, clean2])
        return f"{numbers[0]}::{numbers[1]}"

    async def find_active(
        self, owner_id: str, from_number: str, to_number: str
    ) -> Optional[Conversation]:
        """
        Find an active conversation based on phone numbers.
        """
        session_key = self.calculate_session_key(from_number, to_number)
        return await self.repository.find_active_by_session_key(owner_id, session_key)

    async def find_last_conversation(
        self, owner_id: str, from_number: str, to_number: str
    ) -> Optional[Conversation]:
        """
        Find the most recent conversation (active or closed) for context linking.
        """
        session_key = self.calculate_session_key(from_number, to_number)
        conversations = await self.repository.find_all_by_session_key(
            owner_id, session_key, limit=1
        )
        return conversations[0] if conversations else None

    async def create_new(
        self,
        owner_id: str,
        from_number: str,
        to_number: str,
        channel: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        previous_conversation: Optional[Conversation] = None,
    ) -> Conversation:
        """
        Create a new conversation, optionally linking to a previous one.
        """
        session_key = self.calculate_session_key(from_number, to_number)
        now = datetime.now(timezone.utc)

        # Default expiration for PENDING state
        expires_at = now + timedelta(
            minutes=settings.conversation.pending_expiration_minutes
        )

        # Prepare metadata with linking info if available
        new_metadata = metadata.copy() if metadata else {}

        if previous_conversation:
            new_metadata.update(
                {
                    "previous_conversation_id": previous_conversation.conv_id,
                    "previous_status": previous_conversation.status,
                    "previous_ended_at": (
                        previous_conversation.ended_at.isoformat()
                        if previous_conversation.ended_at
                        else None
                    ),
                    "linked_at": now.isoformat(),
                }
            )

            # If previous was FAILED, flag for recovery context
            if previous_conversation.status == ConversationStatus.FAILED.value:
                new_metadata["recovery_mode"] = True

        data = {
            "owner_id": owner_id,
            "from_number": from_number,
            "to_number": to_number,
            "channel": channel,
            "status": ConversationStatus.PENDING.value,
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "context": {},
            "metadata": new_metadata,
        }

        if user_id:
            data["user_id"] = user_id

        conversation = await self.repository.create(data)

        logger.info(
            "Created new conversation",
            conv_id=conversation.conv_id if conversation else None,
            owner_id=owner_id,
            session_key=session_key,
        )

        return conversation
