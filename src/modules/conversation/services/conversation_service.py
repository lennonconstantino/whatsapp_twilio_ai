"""
Conversation service for managing conversations.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone

from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.repositories.conversation_repository import ConversationRepository
from src.modules.conversation.repositories.message_repository import MessageRepository

from src.core.config import settings
from src.core.utils import get_logger
from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.components.closure_detector import ClosureDetector

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
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        closure_detector: ClosureDetector
    ):
        """
        Initialize the service.
        
        Args:
            conversation_repo: Conversation repository
            message_repo: Message repository
            closure_detector: Closure intent detector
        """
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.closure_detector = closure_detector
    
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
                    # Update local conversation object with result of close operation
                    conversation = self.close_conversation(
                        conversation, 
                        ConversationStatus.EXPIRED,
                        initiated_by="system",
                        reason="expired_before_new"
                    )
                
                # Prepare metadata with previous conversation context
                new_metadata = metadata.copy() if metadata else {}
                new_metadata.update({
                    "previous_conversation_id": conversation.conv_id,
                    "previous_status": conversation.status,
                    "previous_ended_at": conversation.ended_at.isoformat() if conversation.ended_at else datetime.now(timezone.utc).isoformat(),
                    "linked_at": datetime.now(timezone.utc).isoformat()
                })
                
                # Create new conversation
                conversation = self._create_new_conversation(
                    owner_id, from_number, to_number, channel, user_id, new_metadata
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
            "No active conversation found, checking history and creating new",
            owner_id=owner_id,
            session_key=session_key
        )
        
        # Try to find the most recent previous conversation for context linking
        # This handles cases where we are starting fresh after a FAILED or CLOSED state
        previous_conv = None
        try:
            last_conversations = self.conversation_repo.find_all_by_session_key(
                owner_id, session_key, limit=1
            )
            if last_conversations:
                previous_conv = last_conversations[0]
                logger.info(
                    "Found previous conversation for linking",
                    prev_conv_id=previous_conv.conv_id,
                    prev_status=previous_conv.status
                )
        except Exception as e:
            logger.warning("Failed to fetch conversation history for linking", error=str(e))

        # Prepare metadata
        new_metadata = metadata.copy() if metadata else {}
        if previous_conv:
             new_metadata.update({
                 "previous_conversation_id": previous_conv.conv_id,
                 "previous_status": previous_conv.status,
                 "previous_ended_at": previous_conv.ended_at.isoformat() if previous_conv.ended_at else None,
                 "linked_at": datetime.now(timezone.utc).isoformat()
             })
             
             # If previous was FAILED, we might want to flag it explicitly
             if previous_conv.status == ConversationStatus.FAILED.value:
                 new_metadata["recovery_mode"] = True
        
        conversation = self._create_new_conversation(
            owner_id=owner_id,
            from_number=from_number,
            to_number=to_number,
            channel=channel,
            user_id=user_id,
            metadata=new_metadata
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
            minutes=settings.conversation.pending_expiration_minutes
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
            # RETRY LOOP for state transitions (Optimistic Locking)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Reactivate conversation if it was in IDLE_TIMEOUT
                    if conversation.status == ConversationStatus.IDLE_TIMEOUT.value:
                        updated = self.conversation_repo.update_status(
                            conversation.conv_id,
                            ConversationStatus.PROGRESS,
                            initiated_by="user",
                            reason="reactivation_from_idle"
                        )
                        if not updated:
                             raise ConcurrencyError("Failed to update status (concurrency)", current_version=0)
                        conversation = updated

                        # Add to context
                        context = conversation.context or {}
                        context = context.copy()
                        context['reactivated_from_idle'] = {
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'triggered_by': message_create.message_owner
                        }
                        updated = self.conversation_repo.update_context(
                            conversation.conv_id, 
                            context,
                            expected_version=getattr(conversation, "version", None)
                        )
                        if not updated:
                             raise ConcurrencyError("Failed to update context (concurrency)", current_version=0)
                        conversation = updated
                        
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
                            
                            # Close conversation (close_conversation has its own retry logic now)
                            self.close_conversation(
                                conversation, 
                                ConversationStatus.USER_CLOSED,
                                initiated_by="user",
                                reason="user_cancellation_in_pending"
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
                            
                            # Calculate new expiration for PROGRESS state (standard 24h)
                            new_expires_at = datetime.now(timezone.utc) + timedelta(
                                minutes=settings.conversation.expiration_minutes
                            )

                            updated = self.conversation_repo.update_status(
                                conversation.conv_id,
                                ConversationStatus.PROGRESS,
                                initiated_by="agent",
                                reason="agent_acceptance",
                                expires_at=new_expires_at
                            )
                            if not updated:
                                 raise ConcurrencyError("Failed to update status", current_version=0)
                            conversation = updated
                            
                            # ✅ Registrar quem aceitou a conversa
                            context = conversation.context or {}
                            context = context.copy()
                            context['accepted_by'] = {
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'agent_type': message_create.message_owner,
                                'message_id': None  # Será preenchido após criar mensagem
                            }
                            
                            # Se message_create tiver user_id (agente específico)
                            if hasattr(message_create, 'user_id') and message_create.user_id:
                                context['accepted_by']['user_id'] = message_create.user_id
                            
                            updated = self.conversation_repo.update_context(
                                conversation.conv_id, 
                                context,
                                expected_version=getattr(conversation, "version", None)
                            )
                            if not updated:
                                 raise ConcurrencyError("Failed to update context", current_version=0)
                            conversation = updated
                        else:
                            # Mensagem de USER em PENDING - manter em PENDING
                            logger.debug(
                                "User message while in PENDING - keeping in PENDING",
                                conv_id=conversation.conv_id
                            )
                    
                    # If we complete the block without ConcurrencyError, break the retry loop
                    break
                    
                except (ConcurrencyError, ValueError) as e:
                    # If ValueError, check if it's due to status mismatch (race condition)
                    is_transition_error = isinstance(e, ValueError) and "transition" in str(e)
                    
                    if not isinstance(e, ConcurrencyError) and not is_transition_error:
                        raise e

                    if attempt == max_retries - 1:
                        logger.error("Max retries reached for add_message state transition", conv_id=conversation.conv_id)
                        raise
                    
                    # Reload conversation and retry
                    logger.warning(
                        "Concurrency/State conflict in add_message, retrying...",
                        conv_id=conversation.conv_id,
                        error=str(e),
                        attempt=attempt+1
                    )
                    refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                    if not refreshed:
                        raise ValueError(f"Conversation {conversation.conv_id} not found during retry")
                    conversation = refreshed

            # Persist the message
            message_data = message_create.model_dump(mode='json')
            message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            created_message = self.message_repo.create(message_data)
            
            # Atualizar context com message_id se acabou de aceitar
            if conversation.status == ConversationStatus.PROGRESS.value:
                context = conversation.context or {}
                if 'accepted_by' in context and not context['accepted_by'].get('message_id'):
                    context = context.copy()
                    context['accepted_by']['message_id'] = created_message.msg_id
                    # Use update_context which now has optimistic locking support
                    # We might want a mini-retry here too, but it's less critical
                    try:
                        self.conversation_repo.update_context(
                            conversation.conv_id, 
                            context,
                            expected_version=getattr(conversation, "version", None)
                        )
                    except ConcurrencyError:
                        logger.warning("Failed to update accepted_by message_id due to concurrency", conv_id=conversation.conv_id)
            
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
            # Retry this as well since it's common
            try:
                self.conversation_repo.update_timestamp(conversation.conv_id)
            except ConcurrencyError:
                # If timestamp update fails, it's not critical, but we can try once more
                # Getting fresh version first
                refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                if refreshed:
                    self.conversation_repo.update_timestamp(refreshed.conv_id)
            
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
                    ConversationStatus(result['suggested_status']),
                    initiated_by="system",
                    reason="auto_closure_detection"
                )

            return True
        
        return False
    
    def close_conversation_with_priority(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Conversation:
        """
        Close a conversation respecting status priority.
        
        Priority Order (Highest to Lowest):
        1. FAILED
        2. USER_CLOSED
        3. SUPPORT_CLOSED
        4. AGENT_CLOSED
        5. EXPIRED / IDLE_TIMEOUT
        
        If conversation is already closed with a higher or equal priority status,
        the closure request is ignored.
        """
        current_status = ConversationStatus(conversation.status)
        
        # Define priorities (lower number = higher priority)
        priorities = {
            ConversationStatus.FAILED: 1,
            ConversationStatus.USER_CLOSED: 2,
            ConversationStatus.SUPPORT_CLOSED: 3,
            ConversationStatus.AGENT_CLOSED: 4,
            ConversationStatus.EXPIRED: 5,
            ConversationStatus.IDLE_TIMEOUT: 5
        }
        
        # If not closed yet, just close
        if not current_status.is_closed():
             return self.close_conversation(conversation, status, initiated_by, reason)
             
        # If already closed, check priority
        current_prio = priorities.get(current_status, 99)
        new_prio = priorities.get(status, 99)
        
        if new_prio < current_prio:
            logger.info(
                "Overriding closure status due to higher priority",
                conv_id=conversation.conv_id,
                old_status=current_status.value,
                new_status=status.value
            )
            return self._force_close(conversation, status, initiated_by, reason)
            
        logger.info(
            "Ignoring closure request due to lower/equal priority",
            conv_id=conversation.conv_id,
            current_status=current_status.value,
            ignored_status=status.value
        )
        return conversation

    def _force_close(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        auto_retry: bool = True
    ) -> Conversation:
        """Force close conversation regardless of current status."""
        now = datetime.now(timezone.utc)
        
        # Retry loop for force close
        max_retries = 3 if auto_retry else 1
        for attempt in range(max_retries):
            try:
                closed_conversation = self.conversation_repo.update_status(
                    conversation.conv_id,
                    status,
                    ended_at=now,
                    initiated_by=initiated_by,
                    reason=reason,
                    force=True
                )
                
                logger.info(
                    "Force closed conversation",
                    conv_id=conversation.conv_id,
                    status=status.value,
                    reason=reason
                )
                
                return closed_conversation
            except ConcurrencyError:
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for force_close (or auto_retry=False)", conv_id=conversation.conv_id)
                    raise
                
                # Reload conversation
                logger.warning("Concurrency conflict in force_close, retrying...", conv_id=conversation.conv_id)
                refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                if not refreshed:
                    raise ValueError(f"Conversation {conversation.conv_id} not found during retry")
                conversation = refreshed

    def close_conversation(
        self,
        conversation: Conversation,
        status: ConversationStatus,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        auto_retry: bool = True
    ) -> Conversation:
        """
        Close a conversation with the specified status.
        
        Args:
            conversation: Conversation to close
            status: Closure status
            initiated_by: Who initiated closure
            reason: Closure reason
            auto_retry: Whether to retry on ConcurrencyError
            
        Returns:
            Closed Conversation
        """
        now = datetime.now(timezone.utc)
        
        # Retry loop for close
        max_retries = 3 if auto_retry else 1
        for attempt in range(max_retries):
            try:
                # Update status
                closed_conversation = self.conversation_repo.update_status(
                    conversation.conv_id,
                    status,
                    ended_at=now,
                    initiated_by=initiated_by,
                    reason=reason
                )
                
                logger.info(
                    "Closed conversation",
                    conv_id=conversation.conv_id,
                    status=status.value,
                    reason=reason
                )
                
                return closed_conversation
            except ConcurrencyError:
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for close_conversation (or auto_retry=False)", conv_id=conversation.conv_id)
                    raise
                
                # Reload conversation
                logger.warning("Concurrency conflict in close_conversation, retrying...", conv_id=conversation.conv_id)
                refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                if not refreshed:
                    raise ValueError(f"Conversation {conversation.conv_id} not found during retry")
                conversation = refreshed
    
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
                # Try to expire with auto_retry=False to handle race conditions manually
                self.close_conversation(
                    conversation,
                    ConversationStatus.EXPIRED,
                    initiated_by="system",
                    reason="expired",
                    auto_retry=False
                )
                count += 1
            except ConcurrencyError:
                # Reload and re-check expiration condition
                logger.info("Concurrency conflict during expiration, re-evaluating", conv_id=conversation.conv_id)
                try:
                    refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                    if refreshed and refreshed.is_expired():
                        # Still expired, try again (safe to retry now)
                        self.close_conversation(
                            refreshed,
                            ConversationStatus.EXPIRED,
                            initiated_by="system",
                            reason="expired",
                            auto_retry=True
                        )
                        count += 1
                    else:
                        logger.info("Conversation no longer expired after reload", conv_id=conversation.conv_id)
                except Exception as e:
                    logger.error("Error recovering from expiration concurrency", conv_id=conversation.conv_id, error=str(e))
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
                # Try to close with auto_retry=False
                self.close_conversation(
                    conversation,
                    ConversationStatus.IDLE_TIMEOUT,
                    initiated_by="system",
                    reason="idle_timeout",
                    auto_retry=False
                )
                count += 1
            except ConcurrencyError:
                # Reload and re-check idle condition
                logger.info("Concurrency conflict during idle timeout, re-evaluating", conv_id=conversation.conv_id)
                try:
                    refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                    if refreshed and refreshed.is_idle(idle_minutes):
                        # Still idle, try again
                        self.close_conversation(
                            refreshed,
                            ConversationStatus.IDLE_TIMEOUT,
                            initiated_by="system",
                            reason="idle_timeout",
                            auto_retry=True
                        )
                        count += 1
                    else:
                        logger.info("Conversation no longer idle after reload", conv_id=conversation.conv_id)
                except Exception as e:
                    logger.error("Error recovering from idle concurrency", conv_id=conversation.conv_id, error=str(e))
            except Exception as e:
                logger.error(
                    "Error closing idle conversation",
                    conv_id=conversation.conv_id,
                    error=str(e)
                )
        
        logger.info(f"Closed {count} idle conversations")
        return count
    
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

    def transfer_conversation(
        self,
        conversation: Conversation,
        new_user_id: str,
        reason: Optional[str] = None
    ) -> Conversation:
        """
        Transfer conversation to another agent.
        
        Args:
            conversation: Conversation to transfer
            new_user_id: ID of the new agent (user)
            reason: Reason for transfer
            
        Returns:
            Updated Conversation
        """
        # Retry loop for Optimistic Locking
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use current version if first attempt, otherwise refresh
                if attempt > 0:
                    refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                    if not refreshed:
                         raise ValueError(f"Conversation {conversation.conv_id} not found during retry")
                    conversation = refreshed
                
                old_user_id = conversation.user_id
                
                # Update context
                context = conversation.context or {}
                # Create a copy to avoid mutating the object if retry fails (though we reload anyway)
                context = context.copy()
                context['transfer_history'] = context.get('transfer_history', [])
                context['transfer_history'].append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'from_user_id': old_user_id,
                    'to_user_id': new_user_id,
                    'reason': reason
                })
                
                # Update conversation
                data = {
                    "user_id": new_user_id,
                    "context": context,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                updated_conv = self.conversation_repo.update(
                    conversation.conv_id, 
                    data, 
                    id_column="conv_id",
                    expected_version=getattr(conversation, "version", None)
                )
                
                logger.info(
                    "Transferred conversation",
                    conv_id=conversation.conv_id,
                    from_user=old_user_id,
                    to_user=new_user_id
                )
                
                return updated_conv
                
            except ConcurrencyError:
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for transfer_conversation", conv_id=conversation.conv_id)
                    raise
                logger.warning("Concurrency conflict in transfer_conversation, retrying...", conv_id=conversation.conv_id)
        
        # Should be unreachable due to raise in loop
        return conversation

    def escalate_conversation(
        self,
        conversation: Conversation,
        supervisor_id: str,
        reason: str
    ) -> Conversation:
        """
        Escalate conversation to supervisor.
        
        Keeps the conversation in PROGRESS state but marks it as escalated.
        
        Args:
            conversation: Conversation to escalate
            supervisor_id: ID of the supervisor
            reason: Reason for escalation
            
        Returns:
            Updated Conversation
        """
        # Retry loop for Optimistic Locking
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use current version if first attempt, otherwise refresh
                if attempt > 0:
                    refreshed = self.conversation_repo.find_by_id(conversation.conv_id, id_column="conv_id")
                    if not refreshed:
                         raise ValueError(f"Conversation {conversation.conv_id} not found during retry")
                    conversation = refreshed

                # Update context
                context = conversation.context or {}
                # Create a copy
                context = context.copy()
                context['escalated'] = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'supervisor_id': supervisor_id,
                    'reason': reason,
                    'status': 'open' # explicit status for escalation
                }
                
                # Ensure status is PROGRESS
                data = {
                    "status": ConversationStatus.PROGRESS.value,
                    "context": context,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                updated_conv = self.conversation_repo.update(
                    conversation.conv_id, 
                    data, 
                    id_column="conv_id",
                    expected_version=getattr(conversation, "version", None)
                )
                
                logger.info(
                    "Escalated conversation",
                    conv_id=conversation.conv_id,
                    supervisor_id=supervisor_id
                )
                
                return updated_conv

            except ConcurrencyError:
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for escalate_conversation", conv_id=conversation.conv_id)
                    raise
                logger.warning("Concurrency conflict in escalate_conversation, retrying...", conv_id=conversation.conv_id)
        
        return conversation

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
            ConversationStatus.FAILED,
            initiated_by="system",
            reason="critical_error"
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