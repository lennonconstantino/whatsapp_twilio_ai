"""
Conversation repository for database operations (V2).
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from supabase import Client

from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger

logger = get_logger(__name__)


class ConversationRepositoryV2(SupabaseRepository[Conversation]):
    """
    Repository for Conversation entity operations (V2).
    Focused purely on data access, without business logic leakage.
    """
    
    def __init__(self, client: Client):
        """Initialize conversation repository."""
        super().__init__(client, "conversations", Conversation, validates_ulid=True)
    
    def create(self, data: Dict[str, Any]) -> Optional[Conversation]:
        """
        Create a new conversation.
        """
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
                    "context": "creation"
                }
            }
            self.client.table("conversation_state_history").insert(history_data).execute()
        except Exception as e:
            logger.error(
                "Failed to write conversation state history on create",
                conv_id=conversation.conv_id,
                error=str(e)
            )

    def find_active_by_session_key(
        self,
        owner_id: str,
        session_key: str
    ) -> Optional[Conversation]:
        """
        Find active conversation by session key.
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("session_key", session_key)\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .order("started_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding conversation by session key", error=str(e))
            raise

    def find_all_by_session_key(
        self,
        owner_id: str,
        session_key: str,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Find all conversations for a session key (including closed ones).
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("session_key", session_key)\
                .order("started_at", desc=True)\
                .limit(limit)\
                .execute()
            
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
            result = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .lt("expires_at", now)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding expired conversations", error=str(e))
            raise
    
    def find_idle_candidates(
        self,
        idle_threshold_iso: str,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Find conversations that have been idle since before the threshold.
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .lt("updated_at", idle_threshold_iso)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding idle conversations", error=str(e))
            raise

    def update_context(
        self,
        conv_id: str,
        context: dict,
        expected_version: Optional[int] = None
    ) -> Optional[Conversation]:
        """
        Update conversation context.
        """
        return self.update(
            conv_id, 
            {"context": context}, 
            id_column="conv_id", 
            current_version=expected_version
        )
