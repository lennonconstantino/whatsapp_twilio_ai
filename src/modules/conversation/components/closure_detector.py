"""
Closure detector service for detecting conversation closure intent.
"""
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from src.modules.conversation.models.conversation import Conversation, ConversationStatus
from src.modules.conversation.models.message import Message, MessageOwner
from src.core.config import settings
from src.core.utils import get_logger

logger = get_logger(__name__)


class ClosureDetector:
    """
    Intelligent detector for conversation closure intent.
    
    Combines analysis of:
    - Contextual keywords
    - Message patterns
    - Metadata signals
    - Conversation duration
    """
    
    def __init__(self, closure_keywords: Optional[List[str]] = None):
        """
        Initialize the detector.
        
        Args:
            closure_keywords: Custom list of closure keywords
        """
        self.closure_keywords = closure_keywords or settings.conversation.closure_keywords
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient detection."""
        # Create regex pattern with word boundaries to avoid false positives
        pattern = r'\b(' + '|'.join(re.escape(kw) for kw in self.closure_keywords) + r')\b'
        self.closure_pattern = re.compile(pattern, re.IGNORECASE)
    
    def detect_closure_intent(
        self,
        message: Message,
        conversation: Conversation,
        recent_messages: Optional[List[Message]] = None
    ) -> Dict[str, Any]:
        """
        Detect if there is intent to close the conversation.
        
        Args:
            message: Current message to analyze
            conversation: Conversation in question
            recent_messages: Recent messages for context
            
        Returns:
            Dict with:
                - should_close (bool): Whether to close conversation
                - confidence (float): Confidence in decision (0-1)
                - reasons (List[str]): Reasons for the decision
                - suggested_status (str): Suggested closure status
        """
        reasons = []
        confidence = 0.0
        
        # 1. Check for explicit signal in metadata
        explicit_signal = self._check_explicit_signal(message)
        if explicit_signal:
            return {
                'should_close': True,
                'confidence': 1.0,
                'reasons': ['Explicit closure signal in metadata'],
                'suggested_status': explicit_signal
            }
        
        # 2. Check if it's a user message
        # Handle both Enum objects and raw values (due to Pydantic use_enum_values=True)
        is_user = False
        if isinstance(message.message_owner, MessageOwner):
            is_user = message.message_owner == MessageOwner.USER
        else:
            is_user = message.message_owner == MessageOwner.USER.value

        if not is_user:
            logger.debug(f"Message owner is {message.message_owner}, not USER. Skipping closure check.")
            return {
                'should_close': False,
                'confidence': 0.0,
                'reasons': ['Message is not from user'],
                'suggested_status': None
            }
        
        # 3. Analyze closure keywords
        keyword_score = self._analyze_keywords(message.body or message.content or "")
        logger.debug(f"Keyword score: {keyword_score}")
        if keyword_score > 0:
            confidence += keyword_score * 0.5
            reasons.append(f'Closure keywords detected (score: {keyword_score:.2f})')
        
        # 4. Analyze recent message pattern
        if recent_messages:
            pattern_score = self._analyze_message_pattern(message, recent_messages)
            logger.debug(f"Pattern score: {pattern_score}")
            if pattern_score > 0:
                confidence += pattern_score * 0.3
                reasons.append(f'Closure pattern detected (score: {pattern_score:.2f})')
        
        # 5. Check minimum conversation duration
        if not self._check_min_duration(conversation):
            confidence *= 0.5  # Reduce confidence if conversation too short
            reasons.append('Conversation still very recent')
        
        # 6. Check conversation context
        context_score = self._analyze_context(conversation)
        logger.debug(f"Context score: {context_score}")
        if context_score > 0:
            confidence += context_score * 0.2
            reasons.append(f'Context indicates closure (score: {context_score:.2f})')
            
        logger.debug(f"Final confidence: {confidence}")
        
        # Final decision
        should_close = confidence >= 0.6  # 60% threshold
        
        return {
            'should_close': should_close,
            'confidence': min(confidence, 1.0),
            'reasons': reasons,
            'suggested_status': ConversationStatus.USER_CLOSED.value if should_close else None
        }
    
    def _check_explicit_signal(self, message: Message) -> Optional[str]:
        """
        Check for explicit closure signals in metadata.
        
        Returns:
            Suggested closure status or None
        """
        metadata = message.metadata or {}
        
        # Check for explicit UI action
        if metadata.get('action') == 'close_conversation':
            return ConversationStatus.USER_CLOSED.value
        
        # Check for channel events
        if metadata.get('event_type') in ['conversation_ended', 'user_left']:
            return ConversationStatus.USER_CLOSED.value
        
        # Check for closure flag
        if metadata.get('close_intent') is True:
            return metadata.get('close_reason', ConversationStatus.USER_CLOSED.value)
        
        return None
    
    def _analyze_keywords(self, content: str) -> float:
        """
        Analyze presence of closure keywords.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not content:
            return 0.0
        
        # Normalize text
        normalized_content = content.lower().strip()
        
        # Search for patterns
        matches = self.closure_pattern.findall(normalized_content)
        
        if not matches:
            return 0.0
        
        # Calculate score based on:
        # - Number of keywords found
        # - Position in text (beginning/end have more weight)
        # - Message length
        
        num_matches = len(matches)
        message_length = len(normalized_content.split())
        
        # Base score by number of matches
        base_score = min(num_matches * 0.3, 0.8)
        
        # Bonus if message is short and direct
        if message_length <= 5:
            base_score += 0.2
        
        # Check if keywords are at beginning or end
        words = normalized_content.split()
        if words and any(match in words[0] for match in matches):
            base_score += 0.1
        if words and any(match in words[-1] for match in matches):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _analyze_message_pattern(
        self,
        current_message: Message,
        recent_messages: List[Message]
    ) -> float:
        """
        Analyze recent message pattern to detect closure.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not recent_messages or len(recent_messages) < 2:
            return 0.0
        
        score = 0.0
        
        # Filter user messages
        user_messages = [
            m for m in recent_messages 
            if m.message_owner == MessageOwner.USER
        ]
        
        # Pattern: short response after AI response
        if len(user_messages) >= 2:
            last_user_msg = user_messages[-1]
            content = last_user_msg.body or last_user_msg.content or ""
            if len(content.split()) <= 3:
                score += 0.3
        
        # Pattern: positive confirmation
        positive_words = ['sim', 'ok', 'certo', 'perfeito', 'ótimo', 'beleza', 'yes']
        current_content = (current_message.body or current_message.content or "").lower()
        if any(word in current_content for word in positive_words):
            score += 0.2
        
        # Pattern: final message after sequence of responses
        ai_messages = [
            m for m in recent_messages[-5:]
            if m.sent_by_ia
        ]
        if len(ai_messages) >= 2:
            score += 0.2
        
        return min(score, 1.0)
    
    def _check_min_duration(self, conversation: Conversation) -> bool:
        """
        Check if conversation has reached minimum duration.
        
        Returns:
            True if minimum time has passed
        """
        if not conversation.started_at:
            return False
        
        min_duration = timedelta(
            seconds=settings.conversation.min_conversation_duration
        )

        now = datetime.now(timezone.utc)
        started_at = conversation.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        duration = now - started_at
        
        return duration >= min_duration
    
    def _analyze_context(self, conversation: Conversation) -> float:
        """
        Analyze conversation context for closure signals.
        
        Returns:
            Score from 0.0 to 1.0
        """
        context = conversation.context or {}
        score = 0.0
        
        # Check if goal was achieved
        if context.get('goal_achieved') is True:
            score += 0.5
        
        # Check if no pending actions
        if context.get('pending_actions') == []:
            score += 0.3
        
        # Check closure flag
        if context.get('can_close') is True:
            score += 0.4
        
        return min(score, 1.0)
    
    def add_keywords(self, keywords: List[str]):
        """
        Add new closure keywords.
        
        Args:
            keywords: List of keywords to add
        """
        self.closure_keywords.extend(keywords)
        self._compile_patterns()
    
    def set_owner_keywords(self, owner_id: str, keywords: List[str]):
        """
        Set specific keywords for an owner.
        
        Args:
            owner_id: Owner ID
            keywords: List of custom keywords
        """
        # In a real implementation, this would be persisted and loaded per owner
        # For now, just replace global keywords
        self.closure_keywords = keywords
        self._compile_patterns()

    def detect_cancellation_in_pending(self, message: Message, conversation: Conversation) -> bool:
        """
        Detecta se usuário quer cancelar conversa pendente.
        
        Args:
            message: Mensagem a ser analisada
            conversation: Conversa atual
            
        Returns:
            True se deve cancelar, False caso contrário
        """
        if conversation.status != ConversationStatus.PENDING.value:
            return False
        
        cancel_keywords = ['cancelar', 'desistir', 'deixa pra lá', 'esquece', 'cancel']
        content = (message.body or message.content or "").lower()
        
        return any(kw in content for kw in cancel_keywords)
