"""
Message repository for database operations.
"""
from typing import List, Optional
from supabase import Client

from .base import BaseRepository
from ..models import Message, MessageOwner
from ..utils import get_logger

logger = get_logger(__name__)


class MessageRepository(BaseRepository[Message]):
    """Repository for Message entity operations."""
    
    def __init__(self, client: Client):
        """Initialize message repository."""
        super().__init__(client, "messages", Message)
    
    def find_by_conversation(
        self,
        conv_id: int,
        limit: int = 100,
        offset: int = 0
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
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("conv_id", conv_id)\
                .order("timestamp", desc=False)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding messages by conversation", error=str(e))
            raise
    
    def find_recent_by_conversation(
        self,
        conv_id: int,
        limit: int = 10
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
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("conv_id", conv_id)\
                .order("timestamp", desc=True)\
                .limit(limit)\
                .execute()
            
            # Return in chronological order (oldest first)
            messages = [self.model_class(**item) for item in result.data]
            return list(reversed(messages))
        except Exception as e:
            logger.error("Error finding recent messages", error=str(e))
            raise
    
    def find_user_messages(
        self,
        conv_id: int,
        limit: int = 50
    ) -> List[Message]:
        """
        Find user messages from a conversation.
        
        Args:
            conv_id: Conversation ID
            limit: Maximum number of messages to return
            
        Returns:
            List of user Message instances
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("conv_id", conv_id)\
                .eq("message_owner", MessageOwner.USER.value)\
                .order("timestamp", desc=False)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding user messages", error=str(e))
            raise
    
    def count_by_conversation(self, conv_id: int) -> int:
        """
        Count messages in a conversation.
        
        Args:
            conv_id: Conversation ID
            
        Returns:
            Number of messages
        """
        return self.count({"conv_id": conv_id})
