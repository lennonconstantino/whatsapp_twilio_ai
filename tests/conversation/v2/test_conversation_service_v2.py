"""
Unit tests for Conversation Service V2.
"""
import sys
import os
from unittest.mock import MagicMock

# Set dummy environment variables for Supabase settings validation
os.environ['SUPABASE_URL'] = 'https://example.supabase.co'
os.environ['SUPABASE_KEY'] = 'dummy-key'

# Mock database connection BEFORE importing modules that use it
sys.modules['src.core.database.session'] = MagicMock()
sys.modules['src.core.database.session'].db = MagicMock()
sys.modules['src.core.database.session'].get_db = MagicMock()
sys.modules['src.core.database.session'].DatabaseConnection = MagicMock()

import unittest
from unittest.mock import Mock, ANY
from datetime import datetime, timezone, timedelta

from src.modules.conversation.v2.services.conversation_service import ConversationServiceV2
from src.modules.conversation.v2.components.conversation_closer import ClosureResult
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.dtos.message_dto import MessageCreateDTO

class TestConversationServiceV2(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.message_repo = Mock()
        self.finder = Mock()
        self.lifecycle = Mock()
        self.closer = Mock()
        
        self.service = ConversationServiceV2(
            self.repo,
            self.message_repo,
            self.finder,
            self.lifecycle,
            self.closer
        )
        
        # Valid ULIDs for testing
        self.valid_ulid_1 = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.valid_ulid_2 = "01ARZ3NDEKTSV4RRFFQ69G5FAW"

        self.mock_conv = Conversation(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            channel="whatsapp",
            session_key="123::456",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

    def test_get_or_create_active_found(self):
        """Test finding an existing active conversation."""
        self.finder.find_active.return_value = self.mock_conv
        # Ensure conversation is not expired and not closed
        self.mock_conv.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        self.mock_conv.status = ConversationStatus.PENDING.value
        
        result = self.service.get_or_create_conversation(self.valid_ulid_2, "123", "456")
        
        self.assertEqual(result, self.mock_conv)
        self.finder.create_new.assert_not_called()

    def test_get_or_create_active_expired(self):
        """Test finding an active conversation that is actually expired."""
        self.finder.find_active.return_value = self.mock_conv
        # Make it expired
        self.mock_conv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.mock_conv.status = ConversationStatus.PENDING.value
        
        new_conv = Mock(spec=Conversation)
        self.finder.create_new.return_value = new_conv
        
        result = self.service.get_or_create_conversation(self.valid_ulid_2, "123", "456")
        
        # Should expire old one
        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.EXPIRED,
            reason="expired_before_new",
            initiated_by="system"
        )
        
        # Should create new one linked
        self.finder.create_new.assert_called_with(
            self.valid_ulid_2, "123", "456", "whatsapp", None, None,
            previous_conversation=self.mock_conv
        )
        self.assertEqual(result, new_conv)

    def test_get_or_create_not_found(self):
        """Test creating new conversation when none found."""
        self.finder.find_active.return_value = None
        self.finder.find_last_conversation.return_value = None
        
        new_conv = Mock(spec=Conversation)
        self.finder.create_new.return_value = new_conv
        
        result = self.service.get_or_create_conversation(self.valid_ulid_2, "123", "456")
        
        self.finder.create_new.assert_called()
        self.assertEqual(result, new_conv)

    def test_add_message_closure_intent(self):
        """Test detecting closure intent."""
        msg_dto = MessageCreateDTO(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            body="Stop please",
            message_owner=MessageOwner.USER,
            content="Stop please",
            direction="inbound",
            message_type="text"
        )
        
        self.closer.detect_intent.return_value = ClosureResult(
            should_close=True,
            confidence=1.0,
            reasons=[],
            suggested_status=ConversationStatus.USER_CLOSED
        )
        
        self.service.add_message(self.mock_conv, msg_dto)
        
        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.USER_CLOSED,
            reason="user_intent_detected",
            initiated_by="user"
        )

    def test_add_message_agent_acceptance(self):
        """Test agent message transitioning PENDING -> PROGRESS."""
        msg_dto = MessageCreateDTO(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            body="Hello",
            message_owner=MessageOwner.AGENT,
            content="Hello",
            direction="outbound",
            message_type="text"
        )
        
        self.closer.detect_intent.return_value = ClosureResult(
            should_close=False, confidence=0, reasons=[]
        )
        
        self.mock_conv.status = ConversationStatus.PENDING.value
        
        self.service.add_message(self.mock_conv, msg_dto)
        
        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.PROGRESS,
            reason="agent_acceptance",
            initiated_by="agent",
            expires_at=ANY
        )

    def test_add_message_reactivation(self):
        """Test user message transitioning IDLE -> PROGRESS."""
        msg_dto = MessageCreateDTO(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            body="Hi again",
            message_owner=MessageOwner.USER,
            content="Hi again",
            direction="inbound",
            message_type="text"
        )
        
        self.closer.detect_intent.return_value = ClosureResult(
            should_close=False, confidence=0, reasons=[]
        )
        
        self.mock_conv.status = ConversationStatus.IDLE_TIMEOUT.value
        
        self.service.add_message(self.mock_conv, msg_dto)
        
        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.PROGRESS,
            reason="user_reactivation",
            initiated_by="user"
        )

if __name__ == '__main__':
    unittest.main()
