"""
Unit tests for Conversation Finder Component (V2).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, ANY, AsyncMock

from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.components.conversation_finder import ConversationFinder

@pytest.mark.asyncio
class TestConversationFinder:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.repo = AsyncMock()
        self.finder = ConversationFinder(self.repo)
        
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="whatsapp:+123",
            to_number="whatsapp:+456",
            channel="whatsapp",
            status=ConversationStatus.PROGRESS.value,
            started_at=datetime.now(timezone.utc),
            session_key="whatsapp:+123::whatsapp:+456",
            version=1
        )

    def test_calculate_session_key(self):
        """Test session key calculation."""
        # Order independence
        key1 = self.finder.calculate_session_key("whatsapp:+123", "whatsapp:+456")
        key2 = self.finder.calculate_session_key("whatsapp:+456", "whatsapp:+123")
        assert key1 == key2
        
        # Normalization
        key3 = self.finder.calculate_session_key("+123", "+456")
        assert key3 == key1

    async def test_find_active(self):
        """Test finding active conversation."""
        self.repo.find_active_by_session_key.return_value = self.mock_conv
        
        result = await self.finder.find_active("OWNER", "+123", "+456")
        
        assert result == self.mock_conv
        self.repo.find_active_by_session_key.assert_called_with(
            "OWNER",
            "whatsapp:+123::whatsapp:+456"
        )

    async def test_find_last_conversation(self):
        """Test finding last conversation."""
        self.repo.find_all_by_session_key.return_value = [self.mock_conv]
        
        result = await self.finder.find_last_conversation("OWNER", "+123", "+456")
        
        assert result == self.mock_conv
        self.repo.find_all_by_session_key.assert_called_with(
            "OWNER",
            "whatsapp:+123::whatsapp:+456",
            limit=1
        )

    async def test_create_new(self):
        """Test creating new conversation."""
        self.repo.create.return_value = self.mock_conv
        
        result = await self.finder.create_new(
            "OWNER",
            "+123",
            "+456",
            "whatsapp",
            metadata={"source": "test"}
        )
        
        assert result == self.mock_conv
        self.repo.create.assert_called()
        args = self.repo.create.call_args[0][0]
        assert args["owner_id"] == "OWNER"
        assert args["status"] == ConversationStatus.PENDING.value
        assert args["metadata"]["source"] == "test"

    async def test_create_new_linked(self):
        """Test creating new linked conversation."""
        self.repo.create.return_value = self.mock_conv
        prev_conv = self.mock_conv
        prev_conv.ended_at = datetime.now(timezone.utc)
        
        await self.finder.create_new(
            "OWNER",
            "+123",
            "+456",
            "whatsapp",
            previous_conversation=prev_conv
        )
        
        args = self.repo.create.call_args[0][0]
        assert args["metadata"]["previous_conversation_id"] == prev_conv.conv_id
        assert "linked_at" in args["metadata"]
