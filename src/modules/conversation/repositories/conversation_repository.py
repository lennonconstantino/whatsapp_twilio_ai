"""
Conversation repository for database operations (V2).
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.models.conversation import Conversation

logger = get_logger(__name__)


class ConversationRepository(SupabaseRepository[Conversation]):
    """
    Repository for Conversation entity operations.
    Focused purely on data access, without business logic leakage.
    """

    def __init__(self, client: Client):
        """Initialize conversation repository."""
        super().__init__(
            client,
            "conversations",
            Conversation,
            validates_ulid=True,
            exclude_on_create=["session_key"],
        )

    def create(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """
        Create a new conversation.
        """
        data.pop("session_key", None)

        # Ensure version is initialized for Optimistic Locking
        if "version" not in data:
            data["version"] = 1

        # We keep the history logging here as it's a data consistency requirement,
        # but ideally it could be an event listener. For now, we keep it simple.
        conversation = super().create(data)

        if conversation:
            self._log_initial_history(conversation)

        return conversation

    def _log_initial_history(self, conversation: Conversation) -> None:
        """Log initial state history."""
        try:
            now = datetime.now(timezone.utc)
            history_data = {
                "conv_id": conversation.conv_id,
                "from_status": None,
                "to_status": conversation.status,
                "changed_by": "system",
                "reason": "conversation_created",
                "metadata": {
                    "timestamp": now.isoformat(),
                    "original_initiated_by": "system",
                    "context": "creation",
                },
            }
            self.client.table("conversation_state_history").insert(
                history_data
            ).execute()
        except Exception as e:
            logger.error(
                "Failed to write conversation state history on create",
                conv_id=conversation.conv_id,
                error=str(e),
            )

    def find_active_by_session_key(
        self, owner_id: str, session_key: str
    ) -> Optional[Conversation]:
        """
        Find active conversation by session key.
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .eq("session_key", session_key)
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding conversation by session key", error=str(e))
            raise

    def find_active_by_owner(
        self, owner_id: str, limit: int = 100
    ) -> List[Conversation]:
        """
        Find all active conversations for an owner.
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .order("started_at", desc=True)
                .limit(limit)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding active conversations by owner", error=str(e))
            raise

    def find_all_by_session_key(
        self, owner_id: str, session_key: str, limit: int = 10
    ) -> List[Conversation]:
        """
        Find all conversations for a session key (including closed ones).
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .eq("session_key", session_key)
                .order("started_at", desc=True)
                .limit(limit)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding conversations by session key", error=str(e))
            raise

    def find_expired_candidates(self, limit: int = 100) -> List[Conversation]:
        """
        Find active conversations that have passed their expiration time.
        Does NOT update them, just returns candidates.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = (
                self.client.table(self.table_name)
                .select("*")
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .lt("expires_at", now)
                .limit(limit)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding expired conversations", error=str(e))
            raise

    def find_idle_candidates(
        self, idle_threshold_iso: str, limit: int = 100
    ) -> List[Conversation]:
        """
        Find conversations that have been idle since before the threshold.
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .lt("updated_at", idle_threshold_iso)
                .limit(limit)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding idle conversations", error=str(e))
            raise

    def update_context(
        self, conv_id: str, context: dict, expected_version: Optional[int] = None
    ) -> Optional[Conversation]:
        """
        Update conversation context.
        """
        return self.update(
            conv_id,
            {"context": context},
            id_column="conv_id",
            current_version=expected_version,
        )

    def update(
        self,
        id_value: Union[int, str],
        data: Dict[str, Any],
        id_column: str = "id",
        current_version: Optional[int] = None,
    ) -> Optional[Conversation]:
        """
        Override base update to add optimistic locking check for conversations.
        If the update returns no data, verify whether the record version changed
        between reads and raise ConcurrencyError accordingly.
        """
        # Read current before attempting update when version is not explicitly provided
        current = None
        if current_version is None:
            try:
                current = self.find_by_id(id_value, id_column=id_column)
            except Exception:
                current = None
        result = super().update(id_value, data, id_column=id_column, current_version=current_version)
        if result is not None:
            return result
        try:
            after = self.find_by_id(id_value, id_column=id_column)
        except Exception:
            after = None
        if current and after and after.version != current.version:
            raise ConcurrencyError(
                f"Expected version {current.version}, found {after.version}",
                current_version=after.version,
            )
        return None

    def update_timestamp(self, conv_id: str) -> Optional[Conversation]:
        data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        return self.update(conv_id, data, id_column="conv_id")

    @staticmethod
    def calculate_session_key(number1: str, number2: str) -> str:
        clean1 = number1.strip()
        clean2 = number2.strip()
        if not clean1.startswith("whatsapp:"):
            clean1 = f"whatsapp:{clean1}"
        if not clean2.startswith("whatsapp:"):
            clean2 = f"whatsapp:{clean2}"
        numbers = sorted([clean1, clean2])
        return f"{numbers[0]}::{numbers[1]}"

    def find_by_session_key(
        self, owner_id: str, from_number: str, to_number: str
    ) -> Optional[Conversation]:
        try:
            session_key = self.calculate_session_key(from_number, to_number)
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("owner_id", owner_id)
                .eq("session_key", session_key)
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .limit(1)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding conversation by session key", error=str(e))
            raise

    def find_idle_conversations(self, idle_minutes: int, limit: int = 100) -> List[Conversation]:
        try:
            threshold = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
            result = (
                self.client.table(self.table_name)
                .select("*")
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .lt("updated_at", threshold.isoformat())
                .limit(limit)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding idle conversations", error=str(e))
            raise

    def find_expired_conversations(self, limit: int = 100) -> List[Conversation]:
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = (
                self.client.table(self.table_name)
                .select("*")
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])
                .lt("expires_at", now)
                .limit(limit)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding expired conversations", error=str(e))
            raise

    def update_status(
        self,
        conv_id: str,
        status: ConversationStatus,
        *,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        ended_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        force: bool = False,
    ) -> Optional[Conversation]:
        current = self.find_by_id(conv_id, id_column="conv_id")
        if not current:
            return None
        from_status = ConversationStatus(current.status)
        to_status = status if isinstance(status, ConversationStatus) else ConversationStatus(status)
        if not force:
            valid_next = {
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
                    ConversationStatus.PROGRESS,
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
                ConversationStatus.AGENT_CLOSED: [],
                ConversationStatus.SUPPORT_CLOSED: [],
                ConversationStatus.USER_CLOSED: [],
                ConversationStatus.EXPIRED: [],
                ConversationStatus.FAILED: [],
            }
            # Debug logging for transition validation
            if from_status != to_status:
                 allowed = valid_next.get(from_status, [])
                 if to_status not in allowed:
                     logger.error(f"Invalid transition detected: {from_status} -> {to_status}. Allowed: {allowed}")
                     raise ValueError(f"Invalid transition from {from_status} to {to_status}")
        update_data: Dict[str, Any] = {
            "status": to_status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if ended_at or to_status in ConversationStatus.closed_statuses():
            update_data["ended_at"] = (ended_at or datetime.now(timezone.utc)).isoformat()
        if expires_at:
            update_data["expires_at"] = expires_at.isoformat()
        updated = (
            self.client.table(self.table_name)
            .update(update_data)
            .eq("conv_id", conv_id)
            .eq("version", current.version)
            .execute()
        )
        updated_data = updated.data or []
        if not updated_data:
            after = self.find_by_id(conv_id, id_column="conv_id")
            if after and after.version != current.version:
                raise ConcurrencyError(f"Expected version {current.version}, found {after.version}", current_version=after.version)
            return None
        new_conv = self.model_class(**updated_data[0])
        try:
            changed_by = initiated_by if initiated_by in {"agent", "support", "user", "system"} else "system"
            self.client.table("conversation_state_history").insert(
                {
                    "conv_id": conv_id,
                    "from_status": from_status.value,
                    "to_status": to_status.value,
                    "changed_by": changed_by,
                    "reason": reason,
                    "metadata": {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "original_initiated_by": initiated_by,
                        "context": current.context,
                    },
                }
            ).execute()
        except Exception as e:
            logger.error("Failed to write conversation state history", conv_id=conv_id, error=str(e))
        return new_conv

    def cleanup_expired_conversations(self, limit: int = 100) -> int:
        processed = 0
        candidates = self.find_expired_conversations(limit)
        for conv in candidates:
            try:
                result = self.update_status(
                    conv.conv_id,
                    ConversationStatus.EXPIRED,
                    ended_at=datetime.now(timezone.utc),
                    initiated_by="system",
                    reason="ttl_expired",
                )
                if result:
                    processed += 1
            except ConcurrencyError:
                logger.warning("Concurrency conflict expiring conversation", conv_id=conv.conv_id)
            except Exception as e:
                logger.error("Error expiring conversation", conv_id=conv.conv_id, error=str(e))
        return processed

    def close_by_message_policy(
        self,
        conv: Conversation,
        *,
        should_close: bool,
        message_owner: Any,
        message_text: Optional[str] = None,
    ) -> bool:
        if not should_close:
            return False
        owner = getattr(message_owner, "value", message_owner)
        status_map = {
            "agent": ConversationStatus.AGENT_CLOSED,
            "support": ConversationStatus.SUPPORT_CLOSED,
            "user": ConversationStatus.USER_CLOSED,
        }
        target = status_map.get(owner, ConversationStatus.EXPIRED)
        result = self.update_status(
            conv.conv_id,
            target,
            initiated_by=owner,
            reason="message_policy",
            ended_at=datetime.now(timezone.utc),
        )
        if result:
            if message_text:
                self.update_context(conv.conv_id, conv.context or {})
            return True
        return False
