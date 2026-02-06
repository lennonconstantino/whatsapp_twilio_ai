"""Test suite for conversation service."""

import unittest.mock
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

import pytest

from src.modules.conversation.components.conversation_closer import \
    ConversationCloser
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.models.conversation import (Conversation,
                                                          ConversationStatus)
from src.modules.conversation.models.message import Message
from src.modules.conversation.services.conversation_service import \
    ConversationService


class TestConversationCloser:
    """Test cases for ConversationCloser."""

    def setup_method(self):
        """Setup test fixtures."""
        self.closer = ConversationCloser()

    def test_detect_closure_keywords(self):
        """Test detection of closure keywords."""
        conversation = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS,
            started_at=datetime.now() - timedelta(minutes=10),
            context={"goal_achieved": True},
        )

        message = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5F13",
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="obrigado tchau",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT,
        )

        result = self.closer.detect_intent(message, conversation)
        assert result.should_close is True
        assert result.confidence >= 0.8
        assert "closure keywords detected" in result.reasons[0].lower()

    def test_min_duration_handles_timezone_aware_started_at(self):
        """Test timezone-aware started_at in duration calculation."""
        from datetime import timezone

        conversation = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=5),
            context={},
        )

        message = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="ok",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT,
        )

        result = self.closer.detect_intent(message, conversation)
        assert result.should_close is False

    def test_no_closure_on_normal_message(self):
        """Test that normal messages don't trigger closure."""
        conversation = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS,
            started_at=datetime.now() - timedelta(minutes=10),
        )

        message = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="Qual o horário de funcionamento?",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT,
        )

        result = self.closer.detect_intent(
            message,
            conversation
        )

        assert result.should_close is False


@pytest.mark.asyncio
class TestConversationService:
    """Test cases for ConversationService."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test fixtures."""
        self.mock_conv_repo = AsyncMock()
        self.mock_msg_repo = AsyncMock()
        self.mock_finder = AsyncMock()
        self.mock_lifecycle = AsyncMock()
        self.mock_closer = Mock()  # Closer seems to be sync based on TestConversationCloser

        self.service = ConversationService(
            conversation_repo=self.mock_conv_repo,
            message_repo=self.mock_msg_repo,
            finder=self.mock_finder,
            lifecycle=self.mock_lifecycle,
            closer=self.mock_closer,
        )

    async def test_get_or_create_finds_active_conversation(self):
        """Test that get_or_create returns existing active conversation."""
        existing_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PROGRESS,
        )
        
        # Mocking V2 Finder behavior
        self.mock_finder.find_active.return_value = existing_conv

        result = await self.service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
        )
        assert result.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.mock_finder.find_active.assert_called_once()
        self.mock_finder.create_new.assert_not_called()

    async def test_get_or_create_creates_new_conversation(self):
        """Create new conversation when none exists."""
        self.mock_finder.find_active.return_value = None
        new_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.PENDING,
        )
        self.mock_finder.create_new.return_value = new_conv

        result = await self.service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
        )
        assert result.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FAW"
        self.mock_finder.find_active.assert_called_once()
        self.mock_finder.create_new.assert_called_once()

    async def test_add_message_reactivates_idle_conversation(self):
        """Reactivate IDLE_TIMEOUT conversation when message is added."""
        from src.modules.conversation.dtos.message_dto import MessageCreateDTO

        conversation = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            status=ConversationStatus.IDLE_TIMEOUT,
            started_at=datetime.now() - timedelta(hours=1),
            context={},
        )

        message_create = MessageCreateDTO(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511988887777",
            to_number="+5511999998888",
            body="Olá, voltei",
            direction=MessageDirection.INBOUND,
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT,
        )

        created_msg = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            **message_create.model_dump(),
        )
        self.mock_msg_repo.create.return_value = created_msg
        
        # Lifecycle mock behavior
        self.mock_lifecycle.transition_to.return_value = conversation
        
        # Closer behavior
        self.mock_closer.detect_intent.return_value = Mock(should_close=False, reasons=[])

        await self.service.add_message(conversation, message_create)

        self.mock_lifecycle.transition_to.assert_any_call(
            conversation,
            ConversationStatus.PROGRESS,
            "user_reactivation",
            "user",
            expires_at=None,
        )

    async def test_close_conversation(self):
        """Test close_conversation delegation."""
        conversation = Mock()
        await self.service.close_conversation(
            conversation, ConversationStatus.AGENT_CLOSED, "agent", "resolved"
        )
        self.mock_lifecycle.transition_to.assert_called_with(
            conversation, ConversationStatus.AGENT_CLOSED, "resolved", "agent"
        )

    async def test_transfer_conversation(self):
        """Test transfer_conversation delegation."""
        conversation = Mock()
        await self.service.transfer_conversation(conversation, "new_user", "shift_change")
        self.mock_lifecycle.transfer_owner.assert_called_with(
            conversation, "new_user", "shift_change"
        )

    async def test_escalate_conversation(self):
        """Test escalate_conversation delegation."""
        conversation = Mock()
        await self.service.escalate_conversation(conversation, "supervisor", "angry_customer")
        self.mock_lifecycle.escalate.assert_called_with(
            conversation, "supervisor", "angry_customer"
        )

    async def test_request_handoff(self):
        """Test request_handoff."""
        conversation = Mock()
        await self.service.request_handoff(conversation, reason="help")
        self.mock_lifecycle.transition_to.assert_called_with(
            conversation,
            ConversationStatus.HUMAN_HANDOFF,
            reason="help",
            initiated_by="system"
        )

    async def test_assign_agent(self):
        """Test assign_agent."""
        conversation = Mock(conv_id="123", version=1)
        self.mock_conv_repo.update.return_value = conversation
        
        result = await self.service.assign_agent(conversation, "agent_007")
        
        assert result == conversation
        self.mock_conv_repo.update.assert_called()
        args = self.mock_conv_repo.update.call_args
        assert args[0][0] == "123" # conv_id
        assert args[0][1]["agent_id"] == "agent_007"

    async def test_assign_agent_failure(self):
        """Test assign_agent concurrency failure."""
        conversation = Mock(conv_id="123", version=1)
        self.mock_conv_repo.update.return_value = None
        
        with pytest.raises(Exception):
            await self.service.assign_agent(conversation, "agent_007")

    async def test_release_to_bot(self):
        """Test release_to_bot."""
        conversation = Mock()
        await self.service.release_to_bot(conversation)
        self.mock_lifecycle.transition_to.assert_called_with(
            conversation,
            ConversationStatus.PROGRESS,
            reason="agent_release",
            initiated_by="agent"
        )

    async def test_get_conversation_by_id(self):
        """Test get_conversation_by_id."""
        await self.service.get_conversation_by_id("123")
        self.mock_conv_repo.find_by_id.assert_called_with("123", id_column="conv_id")

    async def test_get_active_conversations(self):
        """Test get_active_conversations."""
        await self.service.get_active_conversations("owner_1", limit=50)
        self.mock_conv_repo.find_active_by_owner.assert_called_with("owner_1", 50)

    async def test_get_handoff_conversations(self):
        """Test get_handoff_conversations."""
        await self.service.get_handoff_conversations("owner_1", agent_id="agent_1")
        self.mock_conv_repo.find_by_status.assert_called_with(
            owner_id="owner_1",
            status=ConversationStatus.HUMAN_HANDOFF,
            agent_id="agent_1",
            limit=100
        )

    async def test_get_conversation_messages(self):
        """Test get_conversation_messages."""
        await self.service.get_conversation_messages("123", limit=10, offset=5)
        self.mock_msg_repo.find_by_conversation.assert_called_with("123", 10, 5)

    async def test_process_expired_conversations(self):
        """Test delegation of expiration processing."""
        await self.service.process_expired_conversations(limit=10)
        self.mock_lifecycle.process_expirations.assert_called_with(10)

    async def test_process_idle_conversations(self):
        """Test delegation of idle processing."""
        await self.service.process_idle_conversations(idle_minutes=30, limit=10)
        self.mock_lifecycle.process_idle_timeouts.assert_called_with(30, 10)

    async def test_close_conversation_with_priority(self):
        """Test delegation of prioritized closure."""
        conversation = Mock()
        await self.service.close_conversation_with_priority(
            conversation, ConversationStatus.FAILED, reason="error"
        )
        self.mock_lifecycle.transition_to_with_priority.assert_called_with(
            conversation, ConversationStatus.FAILED, "error", "system"
        )

    async def test_extend_expiration(self):
        """Test delegation of extend expiration."""
        conversation = Mock()
        await self.service.extend_expiration(conversation, additional_minutes=10)
        self.mock_lifecycle.extend_expiration.assert_called_with(conversation, 10)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
