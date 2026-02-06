"""
Integration tests for Conversation Service V2 (Facade).
"""
import pytest
from unittest.mock import MagicMock, ANY, AsyncMock

from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation

@pytest.mark.asyncio
class TestConversationServiceV2Facade:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.repo = AsyncMock()
        self.message_repo = AsyncMock()
        self.finder = AsyncMock()
        self.lifecycle = AsyncMock()
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

    async def test_facade_delegation_close_priority(self):
        """Test close_conversation_with_priority delegation."""
        await self.service.close_conversation_with_priority(
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

    async def test_facade_delegation_extend(self):
        """Test extend_expiration delegation."""
        await self.service.extend_expiration(self.mock_conv, 120)
        
        self.lifecycle.extend_expiration.assert_called_with(
            self.mock_conv,
            120
        )

    async def test_facade_delegation_transfer(self):
        """Test transfer_conversation delegation."""
        await self.service.transfer_conversation(
            self.mock_conv,
            "new_user",
            "reason"
        )
        
        self.lifecycle.transfer_owner.assert_called_with(
            self.mock_conv,
            "new_user",
            "reason"
        )

    async def test_facade_delegation_escalate(self):
        """Test escalate_conversation delegation."""
        await self.service.escalate_conversation(
            self.mock_conv,
            "supervisor",
            "reason"
        )
        
        self.lifecycle.escalate.assert_called_with(
            self.mock_conv,
            "supervisor",
            "reason"
        )
