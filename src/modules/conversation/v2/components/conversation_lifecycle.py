"""
Conversation Lifecycle component (V2).
Responsible for state transitions and expiration management.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from src.modules.conversation.v2.repositories.conversation_repository import ConversationRepositoryV2
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError

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
            ConversationStatus.EXPIRED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.FAILED
        ],
        ConversationStatus.PROGRESS: [
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.IDLE_TIMEOUT,
            ConversationStatus.EXPIRED,
            ConversationStatus.FAILED
        ],
        ConversationStatus.IDLE_TIMEOUT: [
            ConversationStatus.PROGRESS,
            ConversationStatus.EXPIRED,
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.FAILED
        ],
        # Terminal states have no outgoing transitions
        ConversationStatus.AGENT_CLOSED: [],
        ConversationStatus.SUPPORT_CLOSED: [],
        ConversationStatus.USER_CLOSED: [],
        ConversationStatus.EXPIRED: [],
        ConversationStatus.FAILED: []
    }

    def __init__(self, repository: ConversationRepositoryV2):
        self.repository = repository

    def _is_valid_transition(self, from_status: ConversationStatus, to_status: ConversationStatus) -> bool:
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
        expires_at: Optional[datetime] = None
    ) -> Conversation:
        """
        Execute a state transition for a conversation.
        """
        current_status = ConversationStatus(conversation.status)
        
        if not self._is_valid_transition(current_status, new_status):
            raise ValueError(f"Invalid transition from {current_status} to {new_status}")

        logger.info(
            "Transitioning conversation",
            conv_id=conversation.conv_id,
            from_status=current_status.value,
            to_status=new_status.value,
            reason=reason
        )

        update_data = {
            "status": new_status.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # If entering a terminal state, set ended_at
        if new_status in ConversationStatus.closed_statuses():
            update_data["ended_at"] = datetime.now(timezone.utc).isoformat()
            
        # Update expires_at if provided (e.g., when moving to PROGRESS)
        if expires_at:
            update_data["expires_at"] = expires_at.isoformat()

        # Perform update with Optimistic Locking
        updated_conv = self.repository.update(
            conversation.conv_id,
            update_data,
            id_column="conv_id",
            current_version=conversation.version
        )
        
        if not updated_conv:
             raise ConcurrencyError(
                 f"Failed to transition conversation {conversation.conv_id} to {new_status.value}", 
                 current_version=conversation.version
             )

        # Log history (could be async/event-driven, but kept inline for now)
        self._log_transition_history(
            updated_conv, 
            current_status, 
            new_status, 
            reason, 
            initiated_by
        )
        
        return updated_conv

    def _log_transition_history(
        self, 
        conversation: Conversation,
        from_status: ConversationStatus,
        to_status: ConversationStatus,
        reason: str,
        initiated_by: str
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
                    "context": conversation.context
                }
            }
            self.repository.client.table("conversation_state_history").insert(history_data).execute()
        except Exception as e:
            logger.error("Failed to log transition history", error=str(e), conv_id=conversation.conv_id)

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
                    initiated_by="system"
                )
                processed += 1
            except ConcurrencyError:
                logger.warning("Concurrency conflict expiring conversation", conv_id=conv.conv_id)
            except Exception as e:
                logger.error("Error expiring conversation", conv_id=conv.conv_id, error=str(e))
                
        return processed

    def process_idle_timeouts(self, idle_minutes: int, limit: int = 100) -> int:
        """
        Process idle conversations (move from PROGRESS to IDLE_TIMEOUT).
        """
        threshold = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
        candidates = self.repository.find_idle_candidates(threshold.isoformat(), limit=limit)
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
                    initiated_by="system"
                )
                processed += 1
            except ConcurrencyError:
                logger.warning("Concurrency conflict processing idle", conv_id=conv.conv_id)
            except Exception as e:
                logger.error("Error processing idle conversation", conv_id=conv.conv_id, error=str(e))
                
        return processed
