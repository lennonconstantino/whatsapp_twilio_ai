"""
Conversation service for managing conversations.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone

from src.models.enums import MessageOwner
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
        owner_id: str,
        from_number: str,
        to_number: str,
        channel: str = "whatsapp",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Find an active conversation or create a new one.
        
        Args:
            owner_id: Owner ID (ULID)
            from_number: From phone number
            to_number: To phone number
            channel: Communication channel
            user_id: User ID (ULID, optional)
            metadata: Additional metadata
            
        Returns:
            Active or newly created Conversation
        """
        # Limpar números
        from_clean = from_number.replace("whatsapp:", "").strip()
        to_clean = to_number.replace("whatsapp:", "").strip()

        # Calculate session key (this is the ONLY normalization needed!)
        session_key = self.conversation_repo.calculate_session_key(from_clean, to_clean)

        logger.info(
            "Looking up conversation by session key",
            owner_id=owner_id,
            session_key=session_key,
            from_number=from_number,
            to_number=to_number
        )        

        # Cleanup expired conversations (background task)
        if settings.toggle.enable_background_tasks:
            self.conversation_repo.cleanup_expired_conversations(owner_id=owner_id, channel=channel)
        else:
            logger.info(
                "Background tasks are disabled, skipping cleanup",
                owner_id=owner_id
            )
        
        # Try to find active conversation
        conversation = self.conversation_repo.find_active_by_session_key(
            owner_id=owner_id, session_key=session_key
        )
        
        if conversation:
            logger.info(
                "Found existing conversation",
                conv_id=conversation.conv_id,
                session_key=session_key,
                status=conversation.status
            )

            # ✅ FIX: Check if expired or closed BEFORE deciding what to do
            is_closed = conversation.is_closed()
            is_expired = conversation.is_expired()
            
            logger.debug(
                "Conversation state check",
                conv_id=conversation.conv_id,
                is_closed=is_closed,
                is_expired=is_expired,
                status=conversation.status
            )
            
            # ✅ FIX: Only create new conversation if current one is closed or expired
            if is_closed or is_expired:
                logger.info(
                    "Current conversation is closed/expired, creating new one",
                    conv_id=conversation.conv_id,
                    is_closed=is_closed,
                    is_expired=is_expired
                )
                
                # Close if expired but not yet closed
                if is_expired and not is_closed:
                    logger.info(
                        "Closing expired conversation before creating new one",
                        conv_id=conversation.conv_id
                    )
                    self.close_conversation(conversation, ConversationStatus.EXPIRED)
                
                # Create new conversation
                conversation = self._create_new_conversation(
                    owner_id, from_number, to_number, channel, user_id, metadata or {}
                )
            
                logger.info(
                    "Created new conversation after expired/closed",
                    conv_id=conversation.conv_id,
                    session_key=session_key
                )
            else:
                # ✅ FIX: Conversation is active and valid, just return it
                logger.info(
                    "Returning existing active conversation",
                    conv_id=conversation.conv_id,
                    session_key=session_key,
                    status=conversation.status
                )

            return conversation

        # No active conversation found, create new
        logger.info(
            "No active conversation found, creating new",
            owner_id=owner_id,
            session_key=session_key
        )
        
        conversation = self._create_new_conversation(
            owner_id=owner_id,
            from_number=from_number,
            to_number=to_number,
            channel=channel,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        logger.info(
            "Created new conversation",
            conv_id=conversation.conv_id,
            session_key=session_key
        )
        
        return conversation
    
    def _create_new_conversation(
        self,
        owner_id: str,
        from_number: str,
        to_number: str,
        channel: str,
        user_id: Optional[str],
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
        try:
            # Reactivate conversation if it was in IDLE_TIMEOUT
            if conversation.status == ConversationStatus.IDLE_TIMEOUT.value:
                self.conversation_repo.update_status(
                    conversation.conv_id,
                    ConversationStatus.PROGRESS
                )
                conversation.status = ConversationStatus.PROGRESS
                
                # Add to context
                context = conversation.context or {}
                context['reactivated_from_idle'] = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'triggered_by': message_create.message_owner
                }
                self.conversation_repo.update_context(conversation.conv_id, context)
                
                logger.info(
                    "Conversation reactivated from idle timeout",
                    conv_id=conversation.conv_id
                )

            # Update conversation status to PROGRESS if it was PENDING
            if conversation.status == ConversationStatus.PENDING.value:
                # Check for cancellation before transitioning to PROGRESS
                if self.closure_detector.detect_cancellation_in_pending(message_create, conversation):
                    logger.info("User cancelled conversation in PENDING state", conv_id=conversation.conv_id)
                    
                    # Persist the message first so we have record
                    message_data = message_create.model_dump(mode='json')
                    message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
                    created_message = self.message_repo.create(message_data)
                    
                    # Close conversation
                    self.close_conversation(
                        conversation, 
                        ConversationStatus.USER_CLOSED
                    )
                    
                    return created_message

                # Transicionar apenas se AGENT/SYSTEM/SUPPORT responde
                if message_create.message_owner in [
                    MessageOwner.AGENT.value,
                    MessageOwner.SYSTEM.value,
                    MessageOwner.SUPPORT.value
                ]:
                    logger.info(
                        "Agent accepting conversation",
                        conv_id=conversation.conv_id,
                        agent_type=message_create.message_owner
                    )
                    
                    self.conversation_repo.update_status(
                        conversation.conv_id,
                        ConversationStatus.PROGRESS
                    )
                    conversation.status = ConversationStatus.PROGRESS
                    
                    # ✅ Registrar quem aceitou a conversa
                    context = conversation.context or {}
                    context['accepted_by'] = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'agent_type': message_create.message_owner,
                        'message_id': None  # Será preenchido após criar mensagem
                    }
                    
                    # Se message_create tiver user_id (agente específico)
                    if hasattr(message_create, 'user_id') and message_create.user_id:
                        context['accepted_by']['user_id'] = message_create.user_id
                    
                    self.conversation_repo.update_context(conversation.conv_id, context)
                else:
                    # Mensagem de USER em PENDING - manter em PENDING
                    logger.debug(
                        "User message while in PENDING - keeping in PENDING",
                        conv_id=conversation.conv_id
                    )
            
            # Persist the message
            message_data = message_create.model_dump(mode='json')
            message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            created_message = self.message_repo.create(message_data)
            
            # Atualizar context com message_id se acabou de aceitar
            if conversation.status == ConversationStatus.PROGRESS.value:
                context = conversation.context or {}
                if 'accepted_by' in context and not context['accepted_by'].get('message_id'):
                    context['accepted_by']['message_id'] = created_message.msg_id
                    self.conversation_repo.update_context(conversation.conv_id, context)
            
            logger.info(
                "Added message to conversation",
                msg_id=created_message.msg_id if created_message else None,
                conv_id=conversation.conv_id
            )
            
            # Check closure intent ONLY for USER messages
            if created_message and self._should_check_closure(created_message):
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
            
        except Exception as e:
            self._handle_critical_error(
                conversation, 
                e, 
                {
                    "action": "add_message",
                    "message_create": message_create.model_dump(mode='json')
                }
            )
            raise e
    
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
                    ConversationStatus(result['suggested_status'])
                )

            return True
        
        return False
    
    def close_conversation(
        self,
        conversation: Conversation,
        status: ConversationStatus
    ) -> Conversation:
        """
        Close a conversation with the specified status.
        
        Args:
            conversation: Conversation to close
            status: Closure status
            
        Returns:
            Closed Conversation
        """
        now = datetime.now(timezone.utc)
        
        # Update status
        closed_conversation = self.conversation_repo.update_status(
            conversation.conv_id,
            status,
            ended_at=now
        )
        
        logger.info(
            "Closed conversation",
            conv_id=conversation.conv_id,
            status=status.value
        )
        
        return closed_conversation
    
    def get_conversation_by_id(self, conv_id: str) -> Optional[Conversation]:
        """
        Find a conversation by ID.
        
        Args:
            conv_id: Conversation ID (ULID)
            
        Returns:
            Conversation or None
        """
        return self.conversation_repo.find_by_id(conv_id, id_column="conv_id")
    
    def get_active_conversations(
        self,
        owner_id: str,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Find active conversations for an owner.
        
        Args:
            owner_id: Owner ID (ULID)
            limit: Result limit
            
        Returns:
            List of active Conversations
        """
        return self.conversation_repo.find_active_by_owner(owner_id, limit)
    
    def get_conversation_messages(
        self,
        conv_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """
        Find messages from a conversation.
        
        Args:
            conv_id: Conversation ID (ULID)
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
                    ConversationStatus.IDLE_TIMEOUT
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
            ConversationStatus.EXPIRED
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

    def _handle_critical_error(self, conversation: Conversation, error: Exception, context: Dict[str, Any]):
        """Marca conversa como FAILED quando erro crítico ocorre."""
        logger.error(
            "Critical error in conversation",
            conv_id=conversation.conv_id,
            error=str(error),
            context=context
        )
        
        # Atualizar contexto com detalhes do erro
        ctx = conversation.context or {}
        ctx['failure_details'] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(error),
            'context': context
        }
        self.conversation_repo.update_context(conversation.conv_id, ctx)
        
        # Marcar como FAILED
        self.close_conversation(
            conversation,
            ConversationStatus.FAILED
        )

    def _should_check_closure(self, message: Message) -> bool:
        """
        Determina se deve verificar intenção de closure para esta mensagem.
        
        Regras:
        - Apenas mensagens de USER são verificadas
        - Mensagens de SYSTEM/AGENT/SUPPORT/TOOL são ignoradas
        - Isso evita overhead desnecessário e logs confusos
        
        Args:
            message: Mensagem a verificar
            
        Returns:
            True se deve verificar closure, False caso contrário
            
        Examples:
            >>> msg_user = Message(message_owner=MessageOwner.USER, ...)
            >>> self._should_check_closure(msg_user)
            True
            
            >>> msg_system = Message(message_owner=MessageOwner.SYSTEM, ...)
            >>> self._should_check_closure(msg_system)
            False
        """
        # Handle both enum and string (due to use_enum_values=True in Pydantic)
        if isinstance(message.message_owner, MessageOwner):
            is_user = message.message_owner == MessageOwner.USER
        else:
            is_user = message.message_owner == MessageOwner.USER.value
        
        if not is_user:
            logger.debug(
                "Skipping closure check for non-user message",
                msg_id=message.msg_id,
                conv_id=message.conv_id,
                message_owner=message.message_owner,
                reason="Only USER messages trigger closure detection"
            )
            return False
        
        logger.debug(
            "Proceeding with closure check for user message",
            msg_id=message.msg_id,
            conv_id=message.conv_id
        )
        
        return True