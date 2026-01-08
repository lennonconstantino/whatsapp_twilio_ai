"""
Test suite for conversation service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.models import (
    Conversation,
    Message,
    ConversationStatus,
    MessageOwner,
    MessageDirection,
    MessageType
)
from src.services import ConversationService, ClosureDetector


class TestClosureDetector:
    """Test cases for ClosureDetector."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = ClosureDetector()
    
    def test_detect_closure_keywords(self):
        """Test detection of closure keywords."""
        conversation = Conversation(
            conv_id=1,
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS,
            started_at=datetime.now() - timedelta(minutes=10)
        )
        
        message = Message(
            msg_id=1,
            conv_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="obrigado tchau",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT
        )
        
        result = self.detector.detect_closure_intent(
            message, conversation, []
        )
        
        assert result['should_close'] is True
        assert result['confidence'] > 0.6
    
    def test_no_closure_on_normal_message(self):
        """Test that normal messages don't trigger closure."""
        conversation = Conversation(
            conv_id=1,
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS,
            started_at=datetime.now() - timedelta(minutes=10)
        )
        
        message = Message(
            msg_id=1,
            conv_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="Qual o horário de funcionamento?",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT
        )
        
        result = self.detector.detect_closure_intent(
            message, conversation, []
        )
        
        assert result['should_close'] is False
    
    def test_explicit_closure_signal(self):
        """Test explicit closure signal in metadata."""
        conversation = Conversation(
            conv_id=1,
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS
        )
        
        message = Message(
            msg_id=1,
            conv_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="fim",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT,
            metadata={"action": "close_conversation"}
        )
        
        result = self.detector.detect_closure_intent(
            message, conversation, []
        )
        
        assert result['should_close'] is True
        assert result['confidence'] == 1.0


class TestConversationService:
    """Test cases for ConversationService."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock repositories
        self.mock_conv_repo = Mock()
        self.mock_msg_repo = Mock()
        self.mock_detector = Mock()
        
        self.service = ConversationService(
            conversation_repo=self.mock_conv_repo,
            message_repo=self.mock_msg_repo,
            closure_detector=self.mock_detector
        )
    
    def test_get_or_create_finds_active_conversation(self):
        """Test that get_or_create returns existing active conversation."""
        # Mock existing conversation
        existing_conv = Conversation(
            conv_id=1,
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS
        )
        
        self.mock_conv_repo.find_active_conversation.return_value = existing_conv
        
        result = self.service.get_or_create_conversation(
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888"
        )
        
        assert result.conv_id == 1
        self.mock_conv_repo.find_active_conversation.assert_called_once()
        self.mock_conv_repo.create.assert_not_called()
    
    def test_get_or_create_creates_new_conversation(self):
        """Test that get_or_create creates new conversation when none exists."""
        # Mock no existing conversation
        self.mock_conv_repo.find_active_conversation.return_value = None
        
        new_conv = Conversation(
            conv_id=2,
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PENDING
        )
        self.mock_conv_repo.create.return_value = new_conv
        
        result = self.service.get_or_create_conversation(
            owner_id=1,
            from_number="+5511988887777",
            to_number="+5511999998888"
        )
        
        assert result.conv_id == 2
        self.mock_conv_repo.find_active_conversation.assert_called_once()
        self.mock_conv_repo.create.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
