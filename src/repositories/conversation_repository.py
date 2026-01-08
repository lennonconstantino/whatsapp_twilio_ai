"""
Conversation repository for database operations.
"""
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from supabase import Client

from .base import BaseRepository
from ..models import Conversation, ConversationStatus, MessageOwner
from ..utils import get_logger

logger = get_logger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation entity operations."""
    
    def __init__(self, client: Client):
        """Initialize conversation repository."""
        super().__init__(client, "conversations", Conversation)
    
    def find_active_conversation(
        self,
        owner_id: int,
        from_number: str,
        to_number: str
    ) -> Optional[Conversation]:
        """
        Find an active conversation for the given parameters.
        
        Args:
            owner_id: Owner ID
            from_number: From phone number
            to_number: To phone number
            
        Returns:
            Active Conversation instance or None
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("from_number", from_number)\
                .eq("to_number", to_number)\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .order("started_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding active conversation", error=str(e))
            raise
    
    def find_active_by_owner(self, owner_id: int, limit: int = 100) -> List[Conversation]:
        """
        Find all active conversations for an owner.
        
        Args:
            owner_id: Owner ID
            limit: Maximum number of conversations to return
            
        Returns:
            List of active Conversation instances
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("owner_id", owner_id)\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .order("updated_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding active conversations", error=str(e))
            raise
    
    def find_expired_conversations(self, limit: int = 100) -> List[Conversation]:
        """
        Find conversations that have expired.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of expired Conversation instances
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
    
    def find_idle_conversations(
        self,
        idle_minutes: int,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Find conversations that have been idle for specified minutes.
        
        Args:
            idle_minutes: Minutes of inactivity
            limit: Maximum number of conversations to return
            
        Returns:
            List of idle Conversation instances
        """
        try:
            threshold = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
            threshold_iso = threshold.isoformat()
            
            result = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .lt("updated_at", threshold_iso)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding idle conversations", error=str(e))
            raise
    
    def update_status(
        self,
        conv_id: int,
        status: ConversationStatus,
        ended_at: Optional[datetime] = None
    ) -> Optional[Conversation]:
        """
        Update conversation status.
        
        Args:
            conv_id: Conversation ID
            status: New status
            ended_at: Optional end timestamp
            
        Returns:
            Updated Conversation instance or None
        """
        data = {
            "status": status.value
        }
        
        if ended_at:
            data["ended_at"] = ended_at.isoformat()
        
        return self.update(conv_id, data, id_column="conv_id")
    
    def update_timestamp(self, conv_id: int) -> Optional[Conversation]:
        """
        Update conversation timestamp to current time.
        
        Args:
            conv_id: Conversation ID
            
        Returns:
            Updated Conversation instance or None
        """
        data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        return self.update(conv_id, data, id_column="conv_id")
    
    def update_context(
        self,
        conv_id: int,
        context: dict
    ) -> Optional[Conversation]:
        """
        Update conversation context.
        
        Args:
            conv_id: Conversation ID
            context: New context data
            
        Returns:
            Updated Conversation instance or None
        """
        data = {
            "context": context
        }
        return self.update(conv_id, data, id_column="conv_id")
    
    def extend_expiration(
        self,
        conv_id: int,
        additional_minutes: int
    ) -> Optional[Conversation]:
        """
        Extend conversation expiration time.
        
        Args:
            conv_id: Conversation ID
            additional_minutes: Minutes to add to expiration
            
        Returns:
            Updated Conversation instance or None
        """
        conversation = self.find_by_id(conv_id, id_column="conv_id")
        if not conversation:
            return None
        
        current_expires = conversation.expires_at or datetime.now(timezone.utc)
        new_expires = current_expires + timedelta(minutes=additional_minutes)
        
        data = {
            "expires_at": new_expires.isoformat()
        }
        
        return self.update(conv_id, data, id_column="conv_id")

    def cleanup_expired_conversations(
        self,
        owner_id: Optional[int] = None,
        channel: Optional[str] = None,
        phone: Optional[str] = None
    ) -> None:
        """Clean up conversations expired by timeout."""
        if (owner_id and not channel) or (channel and not owner_id):
            raise ValueError("Ambos owner_id e channel devem ser fornecidos juntos ou nenhum dos dois")
        if phone and not channel:
            raise ValueError("Ambos phone e channel devem ser fornecidos juntos ou nenhum dos dois")

        try:
            now = datetime.now(timezone.utc).isoformat()

            query = self.client.table(self.table_name)\
                .select("*")\
                .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
                .lt("expires_at", now)

            if owner_id and channel and not phone:
                query = query.eq("owner_id", owner_id).eq("channel", channel)
            elif owner_id and channel and phone:
                phone_expr = ",".join([
                    f"from_number.eq.{phone}",
                    f"to_number.eq.{phone}",
                    f"phone_number.eq.{phone}"
                ])
                query = query.eq("owner_id", owner_id).eq("channel", channel).or_(phone_expr)

            result = query.execute()

            expired_count = 0
            for item in result.data or []:
                conv = self.model_class(**item)
                if conv.conv_id and conv.is_expired():
                    updated = self.update_status(
                        conv.conv_id,
                        ConversationStatus.IDLE_TIMEOUT,
                        ended_at=datetime.now(timezone.utc)
                    )
                    if updated:
                        expired_count += 1

            if expired_count > 0:
                logger.info("Closed expired conversations", count=expired_count)
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
            raise

    def close_by_message_policy(
        self,
        conversation: Conversation,
        should_close: bool,
        message_owner: MessageOwner,
        message_text: Optional[str] = None
    ) -> bool:
        if not should_close:
            return False

        closer_status = ConversationStatus.AGENT_CLOSED
        if message_owner == MessageOwner.SUPPORT:
            closer_status = ConversationStatus.SUPPORT_CLOSED
        elif message_owner == MessageOwner.AGENT:
            closer_status = ConversationStatus.AGENT_CLOSED
        else:
            last = self.client.table("messages")\
                .select("message_owner")\
                .eq("conv_id", conversation.conv_id)\
                .neq("message_owner", MessageOwner.USER.value)\
                .order("timestamp", desc=True)\
                .limit(1)\
                .execute()

            last_owner = None
            if last.data:
                last_owner = last.data[0].get("message_owner")

            if last_owner == MessageOwner.SUPPORT.value:
                closer_status = ConversationStatus.SUPPORT_CLOSED
            else:
                closer_status = ConversationStatus.AGENT_CLOSED

        cid = conversation.conv_id
        if cid is None:
            return False

        closed = self.update_status(
            cid,
            closer_status,
            ended_at=datetime.now(timezone.utc)
        )

        if message_text:
            ctx = conversation.context or {}
            ctx["closed_by_message"] = message_text
            self.update_context(cid, ctx)

        logger.info(
            "Conversation closed by message policy",
            conv_id=conversation.conv_id,
            status=closer_status.value
        )
        return closed is not None
