"""
Conversation Service (V2).
Facade for conversation management using decomposed components.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.utils import get_logger
from src.core.utils.exceptions import DuplicateError
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.repositories.message_repository import \
    MessageRepository
from src.modules.conversation.components.conversation_closer import \
    ConversationCloser
from src.modules.conversation.components.conversation_finder import \
    ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import \
    ConversationLifecycle
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository

logger = get_logger(__name__)


class ConversationService:
    """
    Service for complete conversation management.
    Orchestrates Finder, Lifecycle, and Closer components.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        finder: ConversationFinder,
        lifecycle: ConversationLifecycle,
        closer: ConversationCloser,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.finder = finder
        self.lifecycle = lifecycle
        self.closer = closer

    def get_or_create_conversation(
        self,
        owner_id: str,
        from_number: str,
        to_number: str,
        channel: str = "whatsapp",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        """
        Find an active conversation or create a new one.
        Handles expiration logic if an 'active' conversation is actually expired.
        """
        # 1. Try to find active conversation
        conversation = self.finder.find_active(owner_id, from_number, to_number)

        if conversation:
            # 2. Check validity (expiration)
            is_expired = conversation.is_expired()
            is_closed = (
                conversation.is_closed()
            )  # Should generally be false here given find_active logic

            if is_expired or is_closed:
                logger.info(
                    "Found conversation but it is expired/closed",
                    conv_id=conversation.conv_id,
                    status=conversation.status,
                )

                # Close if needed
                if not is_closed:
                    self.lifecycle.transition_to(
                        conversation,
                        ConversationStatus.EXPIRED,
                        reason="expired_before_new",
                        initiated_by="system",
                    )

                # Create new linked conversation
                return self.finder.create_new(
                    owner_id,
                    from_number,
                    to_number,
                    channel,
                    user_id,
                    metadata,
                    previous_conversation=conversation,
                )

            return conversation

        # 3. No active found, create new (checking history for context)
        last_conv = self.finder.find_last_conversation(owner_id, from_number, to_number)
        return self.finder.create_new(
            owner_id,
            from_number,
            to_number,
            channel,
            user_id,
            metadata,
            previous_conversation=last_conv,
        )

    def add_message(
        self, conversation: Conversation, message_create: MessageCreateDTO
    ) -> Message:
        """
        Add a message to the conversation and handle state transitions.
        """
        from src.core.utils.exceptions import ConcurrencyError
        
        # 1. Detect closure intent BEFORE creating message (optional, but cleaner logic)
        # However, we usually want to persist the message even if it closes the chat.

        # Persist message
        message_data = message_create.model_dump(mode="json")
        message_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        try:
            message = self.message_repo.create(message_data)
        except DuplicateError:
            logger.warning(
                "Duplicate message in add_message (V2)", conv_id=conversation.conv_id
            )
            raise

        # 2. Check for Closure Intent (User Cancellation)
        closure_result = self.closer.detect_intent(message, conversation)

        if closure_result.should_close:
            logger.info("Closure intent detected", conv_id=conversation.conv_id)
            self._handle_transition_with_retry(
                conversation,
                closure_result.suggested_status or ConversationStatus.USER_CLOSED,
                reason="user_intent_detected",
                initiated_by="user",
            )
            return message

        # 3. Handle State Transitions based on Message Owner
        current_status = ConversationStatus(conversation.status)

        if message_create.message_owner in [
            MessageOwner.AGENT.value,
            MessageOwner.SYSTEM.value,
            MessageOwner.SUPPORT.value,
        ]:
            # AGENT/SYSTEM message
            if current_status == ConversationStatus.PENDING:
                # Agent Acceptance: PENDING -> PROGRESS
                expires_at = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.conversation.expiration_minutes
                )
                self._handle_transition_with_retry(
                    conversation,
                    ConversationStatus.PROGRESS,
                    reason="agent_acceptance",
                    initiated_by="agent",
                    expires_at=expires_at,
                )

                # Update context with acceptance info
                self._update_acceptance_context(conversation, message_create)

        elif message_create.message_owner == MessageOwner.USER.value:
            # USER message
            if current_status == ConversationStatus.IDLE_TIMEOUT:
                # Reactivation: IDLE -> PROGRESS
                self._handle_transition_with_retry(
                    conversation,
                    ConversationStatus.PROGRESS,
                    reason="user_reactivation",
                    initiated_by="user",
                )
                self._update_reactivation_context(conversation)

        # Update timestamp to prevent idle timeout (for any message)
        self.conversation_repo.update_timestamp(conversation.conv_id)

        return message
    
    def _handle_transition_with_retry(
        self,
        conversation: Conversation,
        new_status: ConversationStatus,
        reason: str,
        initiated_by: str,
        expires_at: Optional[datetime] = None,
        max_retries: int = 3,
    ) -> None:
        """Handle state transition with retry on concurrency conflicts."""
        from src.core.utils.exceptions import ConcurrencyError
        
        current_conv = conversation
        
        for attempt in range(max_retries):
            try:
                self.lifecycle.transition_to(
                    current_conv,
                    new_status,
                    reason,
                    initiated_by,
                    expires_at=expires_at,
                )
                return
            except ConcurrencyError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        "Concurrency error during transition, retrying",
                        conv_id=conversation.conv_id,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    # Reload conversation data
                    current_conv = self.conversation_repo.find_by_id(
                        conversation.conv_id, id_column="conv_id"
                    )
                    if not current_conv:
                        logger.error(
                            "Conversation not found during retry",
                            conv_id=conversation.conv_id
                        )
                        return
                else:
                    logger.error(
                        "Failed to transition after retries",
                        conv_id=conversation.conv_id,
                        error=str(e)
                    )
                    # Re-raise the last error if needed by caller
                    raise

    def close_conversation(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        initiated_by: str = "system",
        reason: str = "closed_by_service",
    ) -> Conversation:
        """
        Explicitly close a conversation.
        """
        return self.lifecycle.transition_to(conversation, status, reason, initiated_by)

    def close_conversation_with_priority(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        initiated_by: str = "system",
        reason: str = "closed_by_service",
    ) -> Conversation:
        """
        Close a conversation respecting status priority.
        """
        return self.lifecycle.transition_to_with_priority(
            conversation, status, reason, initiated_by
        )

    def process_expired_conversations(self, limit: int = 100) -> int:
        """
        Process expired conversations (PENDING -> EXPIRED, PROGRESS -> EXPIRED).
        """
        return self.lifecycle.process_expirations(limit)

    def process_idle_conversations(self, idle_minutes: int, limit: int = 100) -> int:
        """
        Process idle conversations (PROGRESS -> IDLE_TIMEOUT).
        """
        return self.lifecycle.process_idle_timeouts(idle_minutes, limit)

    def extend_expiration(
        self, conversation: Conversation, additional_minutes: Optional[int] = None
    ) -> Conversation:
        """Extend conversation expiration time."""
        minutes = additional_minutes or settings.conversation.expiration_minutes
        return self.lifecycle.extend_expiration(conversation, minutes)

    def transfer_conversation(
        self, conversation: Conversation, new_user_id: str, reason: str
    ) -> Conversation:
        """Transfer conversation to another agent with retry on concurrency conflicts."""
        from src.core.utils.exceptions import ConcurrencyError
        
        max_retries = 3
        current_conv = conversation
        
        for attempt in range(max_retries):
            try:
                return self.lifecycle.transfer_owner(current_conv, new_user_id, reason)
            except ConcurrencyError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        "Concurrency error during transfer, retrying",
                        conv_id=conversation.conv_id,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    # Reload conversation data
                    current_conv = self.conversation_repo.find_by_id(
                        conversation.conv_id, id_column="conv_id"
                    )
                    if not current_conv:
                        raise ValueError(f"Conversation {conversation.conv_id} not found during retry")
                else:
                    logger.error(
                        "Failed to transfer conversation after retries",
                        conv_id=conversation.conv_id,
                        error=str(e)
                    )
                    raise
        
        raise RuntimeError("Transfer failed after maximum retries")

    def escalate_conversation(
        self, conversation: Conversation, supervisor_id: str, reason: str
    ) -> Conversation:
        """Escalate conversation to supervisor."""
        return self.lifecycle.escalate(conversation, supervisor_id, reason)

    def get_conversation_by_id(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.conversation_repo.find_by_id(conv_id, id_column="conv_id")

    def get_active_conversations(
        self, owner_id: str, limit: int = 100
    ) -> List[Conversation]:
        """Get active conversations for an owner."""
        return self.conversation_repo.find_active_by_owner(owner_id, limit)

    def get_conversation_messages(
        self, conv_id: str, limit: int = 100, offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation."""
        return self.message_repo.find_by_conversation(conv_id, limit, offset)

    def _update_acceptance_context(
        self, conversation: Conversation, message_create: MessageCreateDTO
    ):
        """Helper to update context when agent accepts."""
        context = conversation.context or {}
        context = context.copy()
        context["accepted_by"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_type": message_create.message_owner,
            "user_id": getattr(message_create, "user_id", None),
        }
        self.conversation_repo.update_context(conversation.conv_id, context)

    def _update_reactivation_context(self, conversation: Conversation):
        """Helper to update context on reactivation."""
        context = conversation.context or {}
        context = context.copy()
        context["reactivated_from_idle"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "triggered_by": "user",
        }
        self.conversation_repo.update_context(conversation.conv_id, context)
