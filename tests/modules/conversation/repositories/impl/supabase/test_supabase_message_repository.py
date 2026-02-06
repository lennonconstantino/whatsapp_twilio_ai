
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from src.modules.conversation.repositories.impl.supabase.message_repository import SupabaseMessageRepository
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.core.utils.exceptions import DuplicateError

@pytest.mark.asyncio
class TestSupabaseMessageRepository:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_client = MagicMock()
        self.repository = SupabaseMessageRepository(self.mock_client)
        
        self.mock_message_data = {
            "msg_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "from_number": "+1234567890",
            "to_number": "+0987654321",
            "body": "Hello World",
            "direction": "inbound",
            "timestamp": datetime.utcnow().isoformat(),
            "sent_by_ia": False,
            "message_owner": "user",
            "message_type": "text",
            "content": "Hello World",
            "metadata": {"message_sid": "SM12345"}
        }

    async def test_create_duplicate_error(self):
        # Setup mock to raise duplicate error in sync wrapper
        mock_error = Exception("Duplicate key")
        mock_error.code = "23505"
        
        # We mock the super().create call which is called inside run_in_threadpool
        # But we can just mock client.table.insert... since SupabaseRepository.create uses it
        self.mock_client.table.side_effect = mock_error

        # Execute and Verify
        with pytest.raises(DuplicateError):
            await self.repository.create(self.mock_message_data)

    async def test_find_by_conversation(self):
        # Setup mock chain
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [self.mock_message_data]
        mock_query.execute.return_value = mock_response

        # Execute
        messages = await self.repository.find_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV", limit=10, offset=0)

        # Verify
        assert len(messages) == 1
        assert isinstance(messages[0], Message)
        assert messages[0].msg_id == self.mock_message_data["msg_id"]
        
        # Verify calls
        self.mock_client.table.assert_called_with("messages")
        mock_query.eq.assert_called_with("conv_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
        mock_query.order.assert_called_with("timestamp", desc=False)
        mock_query.range.assert_called_with(0, 9)

    async def test_create_success(self):
        # Setup mock chain
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.insert.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [self.mock_message_data]
        mock_query.execute.return_value = mock_response

        # Execute
        result = await self.repository.create(self.mock_message_data)

        # Verify
        assert isinstance(result, Message)
        assert result.msg_id == self.mock_message_data["msg_id"]

    async def test_find_by_external_id(self):
        # Setup mock chain
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [self.mock_message_data]
        mock_query.execute.return_value = mock_response

        # Execute
        message = await self.repository.find_by_external_id("SM12345")

        # Verify
        assert message is not None
        assert isinstance(message, Message)
        assert message.metadata["message_sid"] == "SM12345"
        
        # Verify calls
        mock_query.eq.assert_called_with("metadata->>message_sid", "SM12345")

    async def test_find_by_external_id_not_found(self):
        # Setup mock chain
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_query.execute.return_value = mock_response

        # Execute
        message = await self.repository.find_by_external_id("SM_NOT_FOUND")

        # Verify
        assert message is None

    async def test_find_recent_by_conversation(self):
        # Setup mock chain
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        # Return 2 messages
        mock_response.data = [self.mock_message_data, self.mock_message_data]
        mock_query.execute.return_value = mock_response

        # Execute
        messages = await self.repository.find_recent_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV", limit=5)

        # Verify
        assert len(messages) == 2
        # The method reverses the list
        assert isinstance(messages[0], Message)
        
        # Verify calls
        mock_query.order.assert_called_with("timestamp", desc=True)
        mock_query.limit.assert_called_with(5)

    async def test_find_user_messages(self):
        # Setup mock chain
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.data = [self.mock_message_data]
        mock_query.execute.return_value = mock_response

        # Execute
        messages = await self.repository.find_user_messages("01ARZ3NDEKTSV4RRFFQ69G5FAV", limit=50)

        # Verify
        assert len(messages) == 1
        assert messages[0].message_owner == MessageOwner.USER.value
        
        # Verify calls
        # Note: order of eq calls might vary
        mock_query.eq.assert_any_call("conv_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
        mock_query.eq.assert_any_call("message_owner", MessageOwner.USER.value)
        mock_query.order.assert_called_with("timestamp", desc=False)
        mock_query.limit.assert_called_with(50)

    async def test_count_by_conversation(self):
        # Setup mock chain for count
        # In SupabaseRepository.count, it does:
        # self.client.table(self.table_name).select("*", count="exact").eq(col, val).execute()
        
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        
        mock_response = MagicMock()
        mock_response.count = 42
        mock_query.execute.return_value = mock_response

        # Execute
        count = await self.repository.count_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        # Verify
        assert count == 42
        
        # Verify calls
        mock_query.select.assert_called_with("*", count="exact")
        mock_query.eq.assert_called_with("conv_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")

    async def test_find_by_conversation_error(self):
        self.mock_client.table.side_effect = Exception("Supabase Error")
        with pytest.raises(Exception):
            await self.repository.find_by_conversation("conv_id")

    async def test_find_by_external_id_error(self):
        self.mock_client.table.side_effect = Exception("Supabase Error")
        with pytest.raises(Exception):
            await self.repository.find_by_external_id("SM123")

    async def test_find_recent_by_conversation_error(self):
        self.mock_client.table.side_effect = Exception("Supabase Error")
        with pytest.raises(Exception):
            await self.repository.find_recent_by_conversation("conv_id")

    async def test_find_user_messages_error(self):
        self.mock_client.table.side_effect = Exception("Supabase Error")
        with pytest.raises(Exception):
            await self.repository.find_user_messages("conv_id")
