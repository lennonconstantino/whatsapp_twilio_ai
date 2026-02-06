
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import uuid

from src.core.utils.exceptions import DuplicateError
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.webhook.message_handler import TwilioWebhookMessageHandler
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner

@pytest.fixture
def mock_services():
    queue_service = MagicMock()
    queue_service.enqueue = AsyncMock()
    
    conversation_service = MagicMock()
    conversation_service.get_or_create_conversation = AsyncMock()
    conversation_service.add_message = AsyncMock()
    conversation_service.message_repo = MagicMock()
    conversation_service.message_repo.find_by_external_id = AsyncMock()
    
    return {
        "conversation_service": conversation_service,
        "twilio_service": MagicMock(),
        "queue_service": queue_service,
    }

@pytest.fixture
def handler(mock_services):
    return TwilioWebhookMessageHandler(
        conversation_service=mock_services["conversation_service"],
        twilio_service=mock_services["twilio_service"],
        queue_service=mock_services["queue_service"],
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

@pytest.fixture
def conv_id():
    return "01HRZ32M1X6Z4P5R7W8K9A0M1C"

@pytest.fixture
def msg_id():
    return "01HRZ32M1X6Z4P5R7W8K9A0M1M"

def test_determine_message_type_text(handler):
    msg_type = handler.determine_message_type(0, None)
    assert msg_type == MessageType.TEXT

def test_determine_message_type_image(handler):
    msg_type = handler.determine_message_type(1, "image/jpeg")
    assert msg_type == MessageType.IMAGE

def test_determine_message_type_audio(handler):
    msg_type = handler.determine_message_type(1, "audio/ogg")
    assert msg_type == MessageType.AUDIO

def test_determine_message_type_video(handler):
    msg_type = handler.determine_message_type(1, "video/mp4")
    assert msg_type == MessageType.VIDEO

def test_determine_message_type_document(handler):
    msg_type = handler.determine_message_type(1, "application/pdf")
    assert msg_type == MessageType.DOCUMENT

@pytest.mark.asyncio
async def test_get_or_create_conversation(handler, mock_services, payload, owner_id):
    mock_conv = MagicMock()
    mock_services["conversation_service"].get_or_create_conversation.return_value = mock_conv
    
    result = await handler.get_or_create_conversation(owner_id, payload)
    
    assert result == mock_conv
    mock_services["conversation_service"].get_or_create_conversation.assert_called_once()

@pytest.mark.asyncio
async def test_persist_outbound_message(handler, mock_services, payload, owner_id, conv_id):
    mock_conv = MagicMock()
    mock_conv.conv_id = conv_id
    
    mock_services["conversation_service"].add_message.return_value = MagicMock()
    
    await handler.persist_outbound_message(
        conversation=mock_conv,
        owner_id=owner_id,
        payload=payload,
        response_sid="SM_resp",
        response_status="sent",
        response_num_media=0,
        response_body="response",
        correlation_id="corr_123",
        message_type=MessageType.TEXT
    )
    
    mock_services["conversation_service"].add_message.assert_called_once()
    # Verify message data
    message_data = mock_services["conversation_service"].add_message.call_args[0][1]
    assert message_data.direction == MessageDirection.OUTBOUND.value

@pytest.mark.asyncio
async def test_persist_inbound_message(handler, mock_services, payload, owner_id, conv_id):
    mock_conv = MagicMock()
    mock_conv.conv_id = conv_id
    
    mock_services["conversation_service"].add_message.return_value = MagicMock()
    
    await handler.persist_inbound_message(
        conversation=mock_conv,
        owner_id=owner_id,
        payload=payload,
        message_type=MessageType.TEXT,
        correlation_id="corr_123"
    )
    
    mock_services["conversation_service"].add_message.assert_called_once()
    message_dto = mock_services["conversation_service"].add_message.call_args[0][1]
    assert message_dto.direction == MessageDirection.INBOUND.value
    assert message_dto.message_owner == MessageOwner.USER.value

@pytest.mark.asyncio
async def test_handle_duplicate_message(handler, mock_services, payload, conv_id, msg_id):
    mock_conv = MagicMock()
    mock_conv.conv_id = conv_id
    
    mock_existing = MagicMock()
    mock_existing.msg_id = msg_id
    
    mock_services["conversation_service"].message_repo.find_by_external_id.return_value = mock_existing
    
    result = await handler.handle_duplicate_message(payload, mock_conv)
    
    assert result.success is True
    assert result.message == "Already processed"
    assert result.msg_id == msg_id

@pytest.mark.asyncio
async def test_send_and_persist_response_success(handler, mock_services, owner_id, conv_id):
    mock_message = MagicMock()
    mock_message.msg_id = str(uuid.uuid4())
    mock_message.conv_id = conv_id
    mock_message.owner_id = owner_id
    mock_message.body = "msg"
    mock_message.message_owner = MessageOwner.SYSTEM

    mock_services["conversation_service"].get_or_create_conversation.return_value = MagicMock(conv_id=conv_id)
    mock_services["conversation_service"].add_message.return_value = mock_message
    
    await handler.send_and_persist_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        sender_number="123",
        recipient_number="456",
        body="msg",
        correlation_id="corr"
    )
    
    assert mock_services["conversation_service"].get_or_create_conversation.call_count == 1
    assert mock_services["conversation_service"].add_message.call_count == 1
    # 1 for enqueue sending, 1 for enqueue embedding
    assert mock_services["queue_service"].enqueue.call_count == 2

@pytest.mark.asyncio
async def test_send_and_persist_response_failure(handler, mock_services, owner_id, conv_id):
    mock_services["conversation_service"].get_or_create_conversation.return_value = MagicMock(conv_id=conv_id)
    # add_message fails (returns None)
    mock_services["conversation_service"].add_message.return_value = None
    
    await handler.send_and_persist_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        sender_number="123",
        recipient_number="456",
        body="msg",
        correlation_id="corr"
    )
    
    assert mock_services["conversation_service"].get_or_create_conversation.call_count == 1
    assert mock_services["conversation_service"].add_message.call_count == 1
    mock_services["queue_service"].enqueue.assert_not_called()
