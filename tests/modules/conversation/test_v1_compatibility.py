"""
Compatibility tests: Verifying V2 Service behaves like V1 Service.
Integration tests using real V2 components with mocked repositories.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, ANY, AsyncMock

from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.components.conversation_finder import ConversationFinder
from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
from src.modules.conversation.components.conversation_closer import ConversationCloser

@pytest.mark.asyncio
class TestV1Compatibility:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Mock Repositories
        self.mock_repo = AsyncMock()
        self.mock_message_repo = AsyncMock()
        
        # Real Components
        # Finder and Lifecycle need repo which is AsyncMock now.
        # But Finder/Lifecycle might expect some methods.
        self.finder = ConversationFinder(self.mock_repo)
        self.lifecycle = ConversationLifecycle(self.mock_repo)
        self.closer = ConversationCloser(closure_keywords=["encerrar"])
        
        # Service under test
        self.service = ConversationService(
            self.mock_repo,
            self.mock_message_repo,
            self.finder,
            self.lifecycle,
            self.closer
        )
        
        # Common objects
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PROGRESS.value,
            started_at=datetime.now(timezone.utc),
            session_key="+5511888888888::+5511999999999",
            version=1
        )

    async def test_get_or_create_existing_active(self):
        """V1 Compat: Test retrieving an existing active conversation."""
        # Setup
        self.mock_repo.find_active_by_session_key.return_value = self.mock_conv
        
        # Execute
        result = await self.service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp"
        )
        
        # Verify
        assert result.conv_id == self.mock_conv.conv_id
        self.mock_repo.create.assert_not_called()

    async def test_get_or_create_none_creates_new(self):
        """V1 Compat: Test creating new conversation when none exists."""
        # Setup
        self.mock_repo.find_active_by_session_key.return_value = None
        self.mock_repo.find_all_by_session_key.return_value = []
        
        new_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FB1",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value
        )
        self.mock_repo.create.return_value = new_conv
        
        # Execute
        result = await self.service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp"
        )
        
        # Verify
        assert result.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FB1"
        self.mock_repo.create.assert_called_once()

    async def test_add_message_reactivates_idle(self):
        """V1 Compat: Test that adding a message reactivates an IDLE_TIMEOUT conversation."""
        # Setup
        self.mock_conv.status = ConversationStatus.IDLE_TIMEOUT.value
        self.mock_repo.update_status.return_value = self.mock_conv
        
        message_dto = MessageCreateDTO(
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )
        
        self.mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FB2",
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER
        )
        
        # Execute
        await self.service.add_message(self.mock_conv, message_dto)
        
        # Verify
        self.mock_repo.update_status.assert_called()
        call_args = self.mock_repo.update_status.call_args
        assert call_args[0][0] == self.mock_conv.conv_id
        assert call_args[0][1] == ConversationStatus.PROGRESS

    async def test_add_message_agent_accepts_pending(self):
        """V1 Compat: Test that agent message transitions PENDING to PROGRESS."""
        # Setup
        self.mock_conv.status = ConversationStatus.PENDING.value
        self.mock_repo.update_status.return_value = self.mock_conv
        
        message_dto = MessageCreateDTO(
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number="+5511888888888", # Agent
            to_number="+5511999999999",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.AGENT,
            channel="whatsapp",
        )
        
        self.mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FB3",
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.AGENT
        )
        
        # Execute
        await self.service.add_message(self.mock_conv, message_dto)
        
        # Verify
        self.mock_repo.update_status.assert_called()
        call_args = self.mock_repo.update_status.call_args
        assert call_args[0][1] == ConversationStatus.PROGRESS

    async def test_close_conversation_success(self):
        """V1 Compat: Test successful conversation closure."""
        # Setup
        self.mock_repo.update_status.return_value = self.mock_conv
        
        # Execute
        await self.service.close_conversation(
            self.mock_conv,
            ConversationStatus.AGENT_CLOSED,
            initiated_by="agent",
            reason="done"
        )
        
        # Verify
        self.mock_repo.update_status.assert_called()
        call_args = self.mock_repo.update_status.call_args
        assert call_args[0][1] == ConversationStatus.AGENT_CLOSED

    async def test_auto_close_detection(self):
        """V1 Compat: Test auto-closing when intent detected."""
        # Setup
        self.mock_repo.update_status.return_value = self.mock_conv
        
        message_dto = MessageCreateDTO(
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Encerrar", # Keyword
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )
        
        # Mock message creation to return object that triggers closer
        msg_created = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FB4",
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Encerrar",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER
        )
        self.mock_message_repo.create.return_value = msg_created
        
        # Execute
        await self.service.add_message(self.mock_conv, message_dto)
        
        # Verify
        update_calls = self.mock_repo.update_status.call_args_list
        found_closure = False
        for call in update_calls:
            if call[0][1] == ConversationStatus.USER_CLOSED:
                found_closure = True
                break
        
        assert found_closure, "Should have closed conversation"
