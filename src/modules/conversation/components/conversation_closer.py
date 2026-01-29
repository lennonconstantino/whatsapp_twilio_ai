"""
Conversation Closer component (V2).
Responsible for detecting conversation closure intent.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.utils import get_logger
from src.modules.conversation.models.conversation import (Conversation,
                                                          ConversationStatus)
from src.modules.conversation.models.message import Message, MessageOwner

logger = get_logger(__name__)


@dataclass
class ClosureResult:
    """Result of a closure detection analysis."""

    should_close: bool
    confidence: float
    reasons: List[str]
    suggested_status: Optional[ConversationStatus] = None


class ConversationCloser:
    """
    Component for detecting closure intent in messages.
    """

    def __init__(self, closure_keywords: Optional[List[str]] = None):
        self.closure_keywords = (
            closure_keywords or settings.conversation.closure_keywords
        )
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient detection."""
        # Create regex pattern with word boundaries to avoid false positives
        if not self.closure_keywords:
            self.closure_pattern = None
            return

        pattern = (
            r"\b(" + "|".join(re.escape(kw) for kw in self.closure_keywords) + r")\b"
        )
        self.closure_pattern = re.compile(pattern, re.IGNORECASE)

    def detect_intent(
        self, message: Message, conversation: Conversation
    ) -> ClosureResult:
        """
        Analyze a message to detect if the user wants to close the conversation.
        """
        reasons = []
        confidence = 0.0

        # 1. Check for explicit signal in metadata (e.g. button click payload)
        # Assuming message metadata might carry signals
        # (This logic mimics v1 but could be refined based on actual payload structure)
        explicit_signal = self._check_explicit_signal(message)
        if explicit_signal:
            return ClosureResult(
                should_close=True,
                confidence=1.0,
                reasons=["Explicit closure signal in metadata"],
                suggested_status=explicit_signal,
            )

        # 2. Check if it's a user message
        # Only users can trigger "USER_CLOSED" via text intent
        is_user = False
        if isinstance(message.message_owner, MessageOwner):
            is_user = message.message_owner == MessageOwner.USER
        else:
            is_user = message.message_owner == MessageOwner.USER.value

        if not is_user:
            return ClosureResult(
                should_close=False, confidence=0.0, reasons=[], suggested_status=None
            )

        # 3. Analyze closure keywords
        keyword_score = self._analyze_keywords(message.body or message.content or "")
        if keyword_score > 0:
            confidence += keyword_score
            reasons.append(f"Closure keywords detected (score: {keyword_score:.2f})")

        # Decision threshold (can be tuned)
        should_close = confidence >= 0.8

        return ClosureResult(
            should_close=should_close,
            confidence=confidence,
            reasons=reasons,
            suggested_status=ConversationStatus.USER_CLOSED if should_close else None,
        )

    def _check_explicit_signal(self, message: Message) -> Optional[ConversationStatus]:
        """Check for explicit closure signals in message metadata."""
        if not message.metadata:
            return None

        intent = message.metadata.get("intent")
        if intent == "close_conversation":
            return ConversationStatus.USER_CLOSED

        return None

    def _analyze_keywords(self, text: str) -> float:
        """Analyze text for closure keywords."""
        if not text or not self.closure_pattern:
            return 0.0

        matches = self.closure_pattern.findall(text)
        if matches:
            # Simple scoring: 1.0 if any match found
            # Could be more sophisticated based on number of matches or specific words
            return 1.0

        return 0.0
