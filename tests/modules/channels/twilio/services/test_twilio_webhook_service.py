
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.twilio_webhook_service import TwilioWebhookService
from src.modules.channels.twilio.dtos import TwilioWebhookResponseDTO
from src.modules.conversation.enums.message_type import MessageType

@pytest.fixture
def mock_components():
    return {
        "owner_resolver": MagicMock(),
        "message_handler": MagicMock(),
        "audio_processor": MagicMock(),
        "ai_processor": MagicMock(),
        "queue_service": MagicMock(), # queue_service is not async per se in registration
    }

@pytest.fixture
def service(mock_components):
    # Setup async methods for components
    mock_components["owner_resolver"].validate_owner_access = AsyncMock()
    mock_components["message_handler"].get_or_create_conversation = AsyncMock()
    mock_components["message_handler"].send_twilio_message = AsyncMock()
    mock_components["message_handler"].persist_outbound_message = AsyncMock()
    mock_components["message_handler"].persist_inbound_message = AsyncMock()
    mock_components["message_handler"].handle_duplicate_message = AsyncMock()
    mock_components["audio_processor"].enqueue_transcription_task = AsyncMock()
    mock_components["ai_processor"].enqueue_ai_task = AsyncMock()
    
    return TwilioWebhookService(
        owner_resolver=mock_components["owner_resolver"],
        message_handler=mock_components["message_handler"],
        audio_processor=mock_components["audio_processor"],
        ai_processor=mock_components["ai_processor"],
        queue_service=mock_components["queue_service"],
    )

@pytest.fixture
def payload():
    return TwilioWhatsAppPayload(
        MessageSid="SM123",
        Body="Hello",
        From="whatsapp:+1234567890",
        To="whatsapp:+0987654321",
        AccountSid="AC123",
        NumMedia=0,
        NumSegments=1,
        SmsStatus="received",
        ApiVersion="2010-04-01",
    )

@pytest.fixture
def owner_id():
    return "01HRZ32M1X6Z4P5R7W8K9A0M1N"

@pytest.mark.asyncio
async def test_process_webhook_local_sender(service, mock_components, payload, owner_id):
    # Setup
    payload.local_sender = True
    
    # Mocks
    mock_components["owner_resolver"].resolve_owner_id.return_value = owner_id
    mock_components["message_handler"].determine_message_type.return_value = MessageType.TEXT
    
    mock_conv = MagicMock()
    mock_conv.conv_id = "01HRZ32M1X6Z4P5R7W8K9A0M1C"
    mock_components["message_handler"].get_or_create_conversation.return_value = mock_conv
    
    mock_twilio_resp = MagicMock()
    mock_twilio_resp.sid = "SM_resp"
    mock_twilio_resp.status = "sent"
    mock_twilio_resp.num_media = 0
    mock_components["message_handler"].send_twilio_message.return_value = mock_twilio_resp
    
    mock_msg = MagicMock()
    mock_msg.msg_id = "01HRZ32M1X6Z4P5R7W8K9A0M1M"
    mock_msg.body = "response body"
    mock_components["message_handler"].persist_outbound_message.return_value = mock_msg
    
    # Execute
    result = await service.process_webhook(payload)
    
    # Verify
    mock_components["owner_resolver"].resolve_owner_id.assert_called_once_with(payload)
    # validate_owner_access should NOT be called for local_sender
    mock_components["owner_resolver"].validate_owner_access.assert_not_called()
    
    mock_components["message_handler"].get_or_create_conversation.assert_called_once()
    mock_components["message_handler"].send_twilio_message.assert_called_once()
    mock_components["message_handler"].persist_outbound_message.assert_called_once()
    
    assert result.success is True

@pytest.mark.asyncio
async def test_process_webhook_inbound_text(service, mock_components, payload, owner_id):
    # Setup
    payload.local_sender = False
    
    # Mocks
    mock_components["owner_resolver"].resolve_owner_id.return_value = owner_id
    mock_components["owner_resolver"].validate_owner_access.return_value = True
    mock_components["message_handler"].determine_message_type.return_value = MessageType.TEXT
    
    mock_conv = MagicMock()
    mock_conv.conv_id = "01HRZ32M1X6Z4P5R7W8K9A0M1C"
    mock_components["message_handler"].get_or_create_conversation.return_value = mock_conv

    mock_msg = MagicMock()
    mock_msg.msg_id = "01HRZ32M1X6Z4P5R7W8K9A0M1M"
    mock_components["message_handler"].persist_inbound_message.return_value = mock_msg
    
    # Execute
    result = await service.process_webhook(payload)
    
    # Verify
    mock_components["owner_resolver"].validate_owner_access.assert_called_once_with(owner_id)
    mock_components["message_handler"].persist_inbound_message.assert_called_once()
    
    # Verify AI task enqueued
    mock_components["ai_processor"].enqueue_ai_task.assert_called_once()
    mock_components["audio_processor"].enqueue_transcription_task.assert_not_called()
    
    assert result.success is True

@pytest.mark.asyncio
async def test_process_webhook_inbound_audio(service, mock_components, payload, owner_id):
    # Setup
    payload.local_sender = False
    payload.media_url = "http://example.com/audio.ogg"
    payload.media_content_type = "audio/ogg"
    
    # Mocks
    mock_components["owner_resolver"].resolve_owner_id.return_value = owner_id
    mock_components["owner_resolver"].validate_owner_access.return_value = True
    mock_components["message_handler"].determine_message_type.return_value = MessageType.AUDIO
    
    mock_conv = MagicMock()
    mock_conv.conv_id = "01HRZ32M1X6Z4P5R7W8K9A0M1C"
    mock_components["message_handler"].get_or_create_conversation.return_value = mock_conv
    
    mock_msg = MagicMock()
    mock_msg.msg_id = "01HRZ32M1X6Z4P5R7W8K9A0M1M"
    mock_components["message_handler"].persist_inbound_message.return_value = mock_msg
    
    # Execute
    result = await service.process_webhook(payload)
    
    # Verify
    mock_components["message_handler"].persist_inbound_message.assert_called_once()
    
    # Verify Audio task enqueued
    mock_components["audio_processor"].enqueue_transcription_task.assert_called_once()
    mock_components["ai_processor"].enqueue_ai_task.assert_not_called()
    
    assert result.success is True

@pytest.mark.asyncio
async def test_process_webhook_access_denied(service, mock_components, payload, owner_id):
    # Setup
    payload.local_sender = False
    owner_id = "owner_1"
    
    # Mocks
    mock_components["owner_resolver"].resolve_owner_id.return_value = owner_id
    mock_components["owner_resolver"].validate_owner_access.return_value = False
    
    # Execute
    result = await service.process_webhook(payload)
    
    # Verify
    mock_components["owner_resolver"].validate_owner_access.assert_called_once()
    
    # Should stop processing
    mock_components["message_handler"].determine_message_type.assert_not_called()
    
    assert result.success is True
    assert "Plan inactive" in result.message
