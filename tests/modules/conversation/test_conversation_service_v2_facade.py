"""
Integration tests for Conversation Service V2 (Facade).
"""
import unittest
from unittest.mock import MagicMock, ANY

from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation

class TestConversationServiceV2Facade(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.message_repo = MagicMock()
        self.finder = MagicMock()
        self.lifecycle = MagicMock()
        self.closer = MagicMock()
        
        self.service = ConversationService(
            self.repo,
            self.message_repo,
            self.finder,
            self.lifecycle,
            self.closer
        )
        
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="123",
            to_number="456",
            channel="whatsapp",
            status=ConversationStatus.PROGRESS.value
        )

    def test_facade_delegation_close_priority(self):
        """Test close_conversation_with_priority delegation."""
        self.service.close_conversation_with_priority(
            self.mock_conv,
            ConversationStatus.FAILED,
            "agent",
            "reason"
        )
        
        self.lifecycle.transition_to_with_priority.assert_called_with(
            self.mock_conv,
            ConversationStatus.FAILED,
            "reason",
            "agent"
        )

    def test_facade_delegation_extend(self):
        """Test extend_expiration delegation."""
        self.service.extend_expiration(self.mock_conv, 120)
        
        self.lifecycle.extend_expiration.assert_called_with(
            self.mock_conv,
            120
        )

    def test_facade_delegation_transfer(self):
        """Test transfer_conversation delegation."""
        self.service.transfer_conversation(
            self.mock_conv,
            "new_user",
            "reason"
        )
        
        self.lifecycle.transfer_owner.assert_called_with(
            self.mock_conv,
            "new_user",
            "reason"
        )

    def test_facade_delegation_escalate(self):
        """Test escalate_conversation delegation."""
        self.service.escalate_conversation(
            self.mock_conv,
            "supervisor",
            "reason"
        )
        
        self.lifecycle.escalate.assert_called_with(
            self.mock_conv,
            "supervisor",
            "reason"
        )

if __name__ == "__main__":
    unittest.main()
