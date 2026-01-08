"""
Conversation service for managing conversations.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone

from src.models.domain import MessageCreateDTO

from ..models import (
    Conversation,
    Message,
    ConversationStatus,
    MessageCreateDTO
)
from ..repositories import ConversationRepository, MessageRepository
from ..config import settings
from ..utils import get_logger, get_db
from .closure_detector import ClosureDetector

logger = get_logger(__name__)


class ConversationService:
    """
    Service for complete conversation management.
    
    Responsibilities:
    - Create and retrieve conversations
    - Manage conversation lifecycle
    - Detect closure intent
    - Process timeouts and expirations
    """
    
    def __init__(
        self,
        conversation_repo: Optional[ConversationRepository] = None,
        message_repo: Optional[MessageRepository] = None,
        closure_detector: Optional[ClosureDetector] = None
    ):
        """
        Initialize the service.
        
        Args:
            conversation_repo: Conversation repository
            message_repo: Message repository
            closure_detector: Closure intent detector
        """
        db_client = get_db()
        self.conversation_repo = conversation_repo or ConversationRepository(db_client)
        self.message_repo = message_repo or MessageRepository(db_client)
        self.closure_detector = closure_detector or ClosureDetector()
    
    def get_or_create_conversation(
        self,
        owner_id: int,
        from_number: str,
        to_number: str,
        channel: str = "whatsapp",
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Find an active conversation or create a new one.
        
        Args:
            owner_id: Owner ID
            from_number: From phone number
            to_number: To phone number
            channel: Communication channel
            user_id: User ID (optional)
            metadata: Additional metadata
            
        Returns:
            Active or newly created Conversation
        """
        self.conversation_repo.cleanup_expired_conversations(owner_id=owner_id, channel=channel)
        # Try to find active conversation
        conversation = self.conversation_repo.find_active_conversation(
            owner_id, from_number, to_number
        )
        
        if conversation:
            logger.info(
                "Found active conversation",
                conv_id=conversation.conv_id,
                owner_id=owner_id
            )
            return conversation
        
        # Create new conversation
        #timeout = timeout_minutes or self.config.DEFAULT_IDLE_TIMEOUT_MINUTES
        return self._create_new_conversation(
            owner_id, from_number, to_number, channel, user_id, metadata
        )
    
    def _create_new_conversation(
        self,
        owner_id: int,
        from_number: str,
        to_number: str,
        channel: str,
        user_id: Optional[int],
        metadata: Optional[Dict[str, Any]]
    ) -> Conversation:
        """Create a new conversation."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(
            minutes=settings.conversation.expiration_minutes
        )
        
        data = {
            "owner_id": owner_id,
            "from_number": from_number,
            "to_number": to_number,
            "channel": channel,
            "status": ConversationStatus.PENDING.value,
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "context": {},
            "metadata": metadata or {}
        }
        
        if user_id:
            data["user_id"] = user_id
        
        conversation = self.conversation_repo.create(data)
        
        logger.info(
            "Created new conversation",
            conv_id=conversation.conv_id if conversation else None,
            owner_id=owner_id
        )
        
        return conversation
    
    def add_message(
        self,
        conversation: Conversation,
        message_create: MessageCreateDTO
    ) -> Message:
        """
        Add a message to the conversation and check for closure intent.
        
        Args:
            conversation: Conversation to add message to
            message_create: Message data
            
        Returns:
            Created Message
        """
        # Update conversation status to PROGRESS if it was PENDING
        if conversation.status == ConversationStatus.PENDING.value:
            self.conversation_repo.update_status(
                conversation.conv_id,
                ConversationStatus.PROGRESS
            )
            conversation.status = ConversationStatus.PROGRESS
        
        # Persist the message
        message_data = message_create.model_dump()
        message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        created_message = self.message_repo.create(message_data)
        
        logger.info(
            "Added message to conversation",
            msg_id=created_message.msg_id if created_message else None,
            conv_id=conversation.conv_id
        )
        
        # Check closure intent if it's a user message
        if created_message:
            is_closure = self._check_closure_intent(conversation, created_message)
            self.conversation_repo.close_by_message_policy(
                conversation,
                is_closure,
                created_message.message_owner,
                created_message.body or created_message.content
            )
        
        # Update conversation timestamp for any message owner
        self.conversation_repo.update_timestamp(conversation.conv_id)
        
        return created_message
    
    def _check_closure_intent(
        self,
        conversation: Conversation,
        message: Message
    ) -> bool:
        """
        Check if there is intent to close the conversation.
        
        Args:
            conversation: Conversation being analyzed
            message: Message that may indicate closure
        """
        # Get recent messages for context
        recent_messages = self.message_repo.find_recent_by_conversation(
            conversation.conv_id,
            limit=10
        )
        
        # Detect closure intent
        result = self.closure_detector.detect_closure_intent(
            message, conversation, recent_messages
        )
        
        logger.info(
            "Closure detection result",
            conv_id=conversation.conv_id,
            should_close=result['should_close'],
            confidence=result['confidence'],
            reasons=result['reasons']
        )
        
        # If should close, update context but don't close automatically
        # Allow system/agent to confirm first
        if result['should_close']:
            context = conversation.context or {}
            context['closure_detected'] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'confidence': result['confidence'],
                'reasons': result['reasons'],
                'suggested_status': result['suggested_status']
            }
            self.conversation_repo.update_context(conversation.conv_id, context)
            
            # If very high confidence (>= 0.8), close automatically
            if result['confidence'] >= 0.8:
                status = ConversationStatus(result['suggested_status'])
                self.close_conversation(
                    conversation,
                    status,
                    reason=f"Auto-closed: {', '.join(result['reasons'])}"
                )

            return True
        
        return False
    
    def close_conversation(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        reason: Optional[str] = None
    ) -> Conversation:
        """
        Close a conversation with the specified status.
        
        Args:
            conversation: Conversation to close
            status: Closure status
            reason: Reason for closure (optional)
            
        Returns:
            Closed Conversation
        """
        now = datetime.now(timezone.utc)
        
        # Update context with closure reason if provided
        if reason:
            context = conversation.context or {}
            context['closure_reason'] = reason
            context['closed_at'] = now.isoformat()
            self.conversation_repo.update_context(conversation.conv_id, context)
        
        # Update status
        closed_conversation = self.conversation_repo.update_status(
            conversation.conv_id,
            status,
            ended_at=now
        )
        
        logger.info(
            "Closed conversation",
            conv_id=conversation.conv_id,
            status=status.value,
            reason=reason
        )
        
        return closed_conversation
    
    def get_conversation_by_id(self, conv_id: int) -> Optional[Conversation]:
        """
        Find a conversation by ID.
        
        Args:
            conv_id: Conversation ID
            
        Returns:
            Conversation or None
        """
        return self.conversation_repo.find_by_id(conv_id, id_column="conv_id")
    
    def get_active_conversations(
        self,
        owner_id: int,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Find active conversations for an owner.
        
        Args:
            owner_id: Owner ID
            limit: Result limit
            
        Returns:
            List of active Conversations
        """
        return self.conversation_repo.find_active_by_owner(owner_id, limit)
    
    def get_conversation_messages(
        self,
        conv_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """
        Find messages from a conversation.
        
        Args:
            conv_id: Conversation ID
            limit: Result limit
            offset: Pagination offset
            
        Returns:
            List of Messages
        """
        return self.message_repo.find_by_conversation(conv_id, limit, offset)
    
    def process_expired_conversations(self, limit: int = 100) -> int:
        """
        Process expired conversations and close them.
        
        Args:
            limit: Maximum number of conversations to process
            
        Returns:
            Number of conversations closed
        """
        expired = self.conversation_repo.find_expired_conversations(limit)
        count = 0
        
        for conversation in expired:
            try:
                self._expire_conversation(conversation)
                count += 1
            except Exception as e:
                logger.error(
                    "Error expiring conversation",
                    conv_id=conversation.conv_id,
                    error=str(e)
                )
        
        logger.info(f"Expired {count} conversations")
        return count
    
    def process_idle_conversations(
        self,
        idle_minutes: Optional[int] = None,
        limit: int = 100
    ) -> int:
        """
        Process idle conversations and close them by timeout.
        
        Args:
            idle_minutes: Minutes of inactivity (uses config if None)
            limit: Maximum number of conversations to process
            
        Returns:
            Number of conversations closed
        """
        idle_minutes = idle_minutes or settings.conversation.idle_timeout_minutes
        idle = self.conversation_repo.find_idle_conversations(idle_minutes, limit)
        count = 0
        
        for conversation in idle:
            try:
                self.close_conversation(
                    conversation,
                    ConversationStatus.IDLE_TIMEOUT,
                    reason=f"Idle timeout after {idle_minutes} minutes"
                )
                count += 1
            except Exception as e:
                logger.error(
                    "Error closing idle conversation",
                    conv_id=conversation.conv_id,
                    error=str(e)
                )
        
        logger.info(f"Closed {count} idle conversations")
        return count
    
    def _expire_conversation(self, conversation: Conversation):
        """Expire a conversation."""
        self.close_conversation(
            conversation,
            ConversationStatus.EXPIRED,
            reason="Expiration time reached"
        )
    
    def extend_expiration(
        self,
        conversation: Conversation,
        additional_minutes: Optional[int] = None
    ) -> Conversation:
        """
        Extend conversation expiration time.
        
        Args:
            conversation: Conversation to extend
            additional_minutes: Minutes to add (uses config if None)
            
        Returns:
            Updated Conversation
        """
        additional_minutes = additional_minutes or settings.conversation.expiration_minutes
        
        return self.conversation_repo.extend_expiration(
            conversation.conv_id,
            additional_minutes
        )
