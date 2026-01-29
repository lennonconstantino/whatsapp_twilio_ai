"""
Conversation Lifecycle component (V2).
Responsible for state transitions and expiration management.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository

logger = get_logger(__name__)


class ConversationLifecycle:
    """
    Component responsible for managing conversation lifecycle states.
    Handles valid transitions, expirations, and timeouts.
    """

    # Defined transitions based on documentation
    VALID_TRANSITIONS = {
        ConversationStatus.PENDING: [
            ConversationStatus.PROGRESS,
            ConversationStatus.HUMAN_HANDOFF,
            ConversationStatus.EXPIRED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.FAILED,
        ],
        ConversationStatus.PROGRESS: [
            ConversationStatus.HUMAN_HANDOFF,
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.IDLE_TIMEOUT,
            ConversationStatus.EXPIRED,
            ConversationStatus.FAILED,
        ],
        ConversationStatus.HUMAN_HANDOFF: [
            ConversationStatus.PROGRESS,  # Return to bot
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.FAILED,
        ],
        ConversationStatus.IDLE_TIMEOUT: [
            ConversationStatus.PROGRESS,
            ConversationStatus.HUMAN_HANDOFF,
            ConversationStatus.EXPIRED,
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.FAILED,
        ],
        # Terminal states have no outgoing transitions
        ConversationStatus.AGENT_CLOSED: [],
        ConversationStatus.SUPPORT_CLOSED: [],
        ConversationStatus.USER_CLOSED: [],
        ConversationStatus.EXPIRED: [],
        ConversationStatus.FAILED: [],
    }

    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    def _is_valid_transition(
        self, from_status: ConversationStatus, to_status: ConversationStatus
    ) -> bool:
        """Check if transition is valid according to state machine rules."""
        # Allow transition to same status (idempotency)
        if from_status == to_status:
            return True

        valid_next_states = self.VALID_TRANSITIONS.get(from_status, [])
        return to_status in valid_next_states

    def transition_to(
        self,
        conversation: Conversation,
        new_status: ConversationStatus,
        reason: str,
        initiated_by: str,
        expires_at: Optional[datetime] = None,
    ) -> Conversation:
        """
        Execute a state transition for a conversation.
        """
        current_status = ConversationStatus(conversation.status)

        if not self._is_valid_transition(current_status, new_status):
            raise ValueError(
                f"Invalid transition from {current_status} to {new_status}"
            )

        logger.info(
            "Transitioning conversation",
            conv_id=conversation.conv_id,
            from_status=current_status.value,
            to_status=new_status.value,
            reason=reason,
        )

        updated_conv = self.repository.update_status(
            conversation.conv_id,
            new_status,
            initiated_by=initiated_by,
            reason=reason,
            ended_at=datetime.now(timezone.utc) if new_status in ConversationStatus.closed_statuses() else None,
            expires_at=expires_at,
        )

        if not updated_conv:
            raise ConcurrencyError(
                f"Failed to transition conversation {conversation.conv_id} to {new_status.value}",
                current_version=conversation.version,
            )

        # Log history (could be async/event-driven, but kept inline for now)
        self._log_transition_history(
            updated_conv, current_status, new_status, reason, initiated_by
        )

        return updated_conv

    def _log_transition_history(
        self,
        conversation: Conversation,
        from_status: ConversationStatus,
        to_status: ConversationStatus,
        reason: str,
        initiated_by: str,
    ):
        """Log state transition to history table."""
        try:
            history_data = {
                "conv_id": conversation.conv_id,
                "from_status": from_status.value,
                "to_status": to_status.value,
                "changed_by": initiated_by,
                "reason": reason,
                "metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": conversation.context,
                },
            }
            self.repository.client.table("conversation_state_history").insert(
                history_data
            ).execute()
        except Exception as e:
            logger.error(
                "Failed to log transition history",
                error=str(e),
                conv_id=conversation.conv_id,
            )

    def transition_to_with_priority(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        reason: str,
        initiated_by: str,
    ) -> Conversation:
        """
        Transition to a closed state respecting status priority.

        Priority Order (Highest to Lowest):
        1. FAILED
        2. USER_CLOSED
        3. SUPPORT_CLOSED
        4. AGENT_CLOSED
        5. EXPIRED / IDLE_TIMEOUT
        """
        current_status = ConversationStatus(conversation.status)

        # If not closed yet, normal transition
        if not current_status.is_closed():
            return self.transition_to(conversation, status, reason, initiated_by)

        # Define priorities (lower number = higher priority)
        priorities = {
            ConversationStatus.FAILED: 1,
            ConversationStatus.USER_CLOSED: 2,
            ConversationStatus.SUPPORT_CLOSED: 3,
            ConversationStatus.AGENT_CLOSED: 4,
            ConversationStatus.EXPIRED: 5,
            ConversationStatus.IDLE_TIMEOUT: 5,
        }

        current_prio = priorities.get(current_status, 99)
        new_prio = priorities.get(status, 99)

        if new_prio < current_prio:
            logger.info(
                "Overriding closure status due to higher priority",
                conv_id=conversation.conv_id,
                old_status=current_status.value,
                new_status=status.value,
            )
            # Force transition for override
            return self._force_transition(conversation, status, reason, initiated_by)

        logger.info(
            "Ignoring transition request due to lower/equal priority",
            conv_id=conversation.conv_id,
            current_status=current_status.value,
            ignored_status=status.value,
        )
        return conversation

    def _force_transition(
        self,
        conversation: Conversation,
        new_status: ConversationStatus,
        reason: str,
        initiated_by: str,
    ) -> Conversation:
        """Force a transition regardless of current state validity."""
        updated_conv = self.repository.update_status(
            conversation.conv_id,
            new_status,
            initiated_by=initiated_by,
            reason=reason,
            ended_at=datetime.now(timezone.utc),
            force=True,
        )

        if not updated_conv:
            raise ConcurrencyError(
                f"Failed to force transition {conversation.conv_id}",
                current_version=conversation.version,
            )

        self._log_transition_history(
            updated_conv,
            ConversationStatus(conversation.status),
            new_status,
            reason,
            initiated_by,
        )
        return updated_conv

    def extend_expiration(
        self, conversation: Conversation, additional_minutes: int
    ) -> Conversation:
        """Extend conversation expiration time."""
        # Use repository method if available, or manual update
        new_expires = datetime.now(timezone.utc) + timedelta(minutes=additional_minutes)

        updated = self.repository.update(
            conversation.conv_id,
            {"expires_at": new_expires.isoformat()},
            id_column="conv_id",
            current_version=conversation.version,
        )

        if not updated:
            raise ConcurrencyError(
                "Failed to extend expiration", current_version=conversation.version
            )

        return updated

    def transfer_owner(
        self, conversation: Conversation, new_user_id: str, reason: str
    ) -> Conversation:
        """Transfer conversation to another user/agent."""
        context = conversation.context or {}
        context = context.copy()
        context.setdefault("transfer_history", []).append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "from_user_id": conversation.user_id,
                "to_user_id": new_user_id,
                "reason": reason,
            }
        )

        updated = self.repository.update(
            conversation.conv_id,
            {
                "user_id": new_user_id,
                "context": context,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            id_column="conv_id",
            current_version=conversation.version,
        )

        if not updated:
            raise ConcurrencyError(
                "Failed to transfer conversation", current_version=conversation.version
            )
        
        return updated
    
    def escalate(
        self, conversation: Conversation, supervisor_id: str, reason: str
    ) -> Conversation:
        """Escalate conversation."""
        context = conversation.context or {}
        context = context.copy()
        context["escalated"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "supervisor_id": supervisor_id,
            "reason": reason,
            "status": "open",
        }

        updated = self.repository.update(
            conversation.conv_id,
            {
                "status": ConversationStatus.PROGRESS.value,
                "context": context,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            id_column="conv_id",
            current_version=conversation.version,
        )

        if not updated:
            raise ConcurrencyError(
                "Failed to escalate conversation", current_version=conversation.version
            )
        
        return updated

    def process_expirations(self, limit: int = 100) -> int:
        """
        Process expired conversations.
        Returns count of processed items.
        """
        candidates = self.repository.find_expired_candidates(limit=limit)
        processed = 0

        for conv in candidates:
            try:
                # Double check expiration in memory to be safe
                if not conv.is_expired():
                    continue

                self.transition_to(
                    conv,
                    ConversationStatus.EXPIRED,
                    reason="ttl_expired",
                    initiated_by="system",
                )
                processed += 1
            except ConcurrencyError:
                logger.warning(
                    "Concurrency conflict expiring conversation", conv_id=conv.conv_id
                )
            except Exception as e:
                logger.error(
                    "Error expiring conversation", conv_id=conv.conv_id, error=str(e)
                )

        return processed

    def process_idle_timeouts(self, idle_minutes: int, limit: int = 100) -> int:
        """
        Process idle conversations (move from PROGRESS to IDLE_TIMEOUT).
        """
        threshold = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
        candidates = self.repository.find_idle_candidates(
            threshold.isoformat(), limit=limit
        )
        processed = 0

        for conv in candidates:
            try:
                # Only PROGRESS state goes to IDLE_TIMEOUT
                # PENDING stays PENDING until full expiration
                if conv.status != ConversationStatus.PROGRESS.value:
                    continue

                self.transition_to(
                    conv,
                    ConversationStatus.IDLE_TIMEOUT,
                    reason="inactivity_timeout",
                    initiated_by="system",
                )
                processed += 1
            except ConcurrencyError:
                logger.warning(
                    "Concurrency conflict processing idle", conv_id=conv.conv_id
                )
            except Exception as e:
                logger.error(
                    "Error processing idle conversation",
                    conv_id=conv.conv_id,
                    error=str(e),
                )

        return processed
