import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.modules.channels.twilio.workers.outbound_worker import TwilioOutboundWorker
from src.modules.channels.twilio.services.twilio_service import TwilioService
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.conversation.models.message import Message

class TestTwilioOutboundWorker:
    @pytest.fixture
    def mock_twilio_service(self):
        return MagicMock(spec=TwilioService)

    @pytest.fixture
    def mock_message_repo(self):
        # Remove spec to allow find_by_id and update which are likely from BaseRepository
        return MagicMock()

    @pytest.fixture
    def worker(self, mock_twilio_service, mock_message_repo):
        return TwilioOutboundWorker(mock_twilio_service, mock_message_repo)

    @pytest.fixture
    def mock_payload(self):
        return {
            "owner_id": "owner_123",
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456",
            "body": "Hello",
            "msg_id": "msg_123",
            "correlation_id": "corr_123"
        }

    @pytest.mark.asyncio
    async def test_handle_send_message_task_success(self, worker, mock_twilio_service, mock_message_repo, mock_payload):
        # Mock Twilio response
        mock_response = MagicMock()
        mock_response.sid = "SM123"
        mock_response.status = "queued"
        mock_response.num_media = "0"
        mock_twilio_service.send_message.return_value = mock_response

        # Mock Repo
        mock_msg = MagicMock(spec=Message)
        mock_msg.metadata = {}
        mock_message_repo.find_by_id.return_value = mock_msg
        
        # Execute
        await worker.handle_send_message_task(mock_payload)
        
        # Verify
        mock_twilio_service.send_message.assert_called_with(
            owner_id="owner_123",
            from_number="whatsapp:+123",
            to_number="whatsapp:+456",
            body="Hello"
        )
        
        mock_message_repo.find_by_id.assert_called_with("msg_123", id_column="msg_id")
        mock_message_repo.update.assert_called_once()
        
        # Check update arguments
        args, kwargs = mock_message_repo.update.call_args
        assert kwargs["id_value"] == "msg_123"
        assert kwargs["data"]["metadata"]["message_sid"] == "SM123"
        assert kwargs["data"]["metadata"]["delivery_status"] == "sent"

    @pytest.mark.asyncio
    async def test_handle_send_message_task_missing_fields(self, worker):
        payload = {"owner_id": "owner_123"} # Missing others
        
        with pytest.raises(ValueError, match="payload inválido"):
            await worker.handle_send_message_task(payload)

    @pytest.mark.asyncio
    async def test_handle_send_message_task_exception(self, worker, mock_twilio_service, mock_payload):
        mock_twilio_service.send_message.side_effect = Exception("Twilio Error")
        
        with pytest.raises(Exception, match="Twilio Error"):
            await worker.handle_send_message_task(mock_payload)

    @pytest.mark.asyncio
    async def test_handle_send_message_task_nested_payload(self, worker, mock_twilio_service, mock_message_repo, mock_payload):
        # Test wrapper structure: {"payload": {...}, "owner_id": ...}
        wrapper = {
            "payload": mock_payload,
            "owner_id": "override_owner", # Should verify precedence or usage
            "correlation_id": "override_corr"
        }
        
        mock_response = MagicMock()
        mock_response.sid = "SM123"
        mock_twilio_service.send_message.return_value = mock_response
        
        mock_message_repo.find_by_id.return_value = MagicMock(metadata={})
        
        await worker.handle_send_message_task(wrapper)
        
        # Should use payload values primarily, but owner_id might be overridden if logic says so
        # Code: owner_id = task_payload.get("owner_id") or payload.get("owner_id")
        # So task_payload takes precedence
        
        mock_twilio_service.send_message.assert_called()
        args = mock_twilio_service.send_message.call_args[1]
        assert args["owner_id"] == "override_owner"
