
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any

from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.twilio_webhook_service import TwilioWebhookService

@pytest.fixture
def mock_components():
    return {
        "owner_resolver": MagicMock(),
        "message_handler": MagicMock(),
        "audio_processor": MagicMock(),
        "ai_processor": MagicMock(),
        "queue_service": MagicMock(),
    }

@pytest.fixture
def service(mock_components):
    mock_components["queue_service"].enqueue = AsyncMock()
    
    svc = TwilioWebhookService(
        owner_resolver=mock_components["owner_resolver"],
        message_handler=mock_components["message_handler"],
        audio_processor=mock_components["audio_processor"],
        ai_processor=mock_components["ai_processor"],
        queue_service=mock_components["queue_service"],
    )
    # Mock process_webhook to avoid running the full logic in these tests
    svc.process_webhook = AsyncMock()
    return svc

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

@pytest.mark.asyncio
async def test_enqueue_webhook_event(service, mock_components, payload):
    # Execute
    result = await service.enqueue_webhook_event(payload)
    
    # Verify
    assert result.success is True
    assert "enqueued" in result.message
    
    mock_components["queue_service"].enqueue.assert_called_once()
    call_args = mock_components["queue_service"].enqueue.call_args
    assert call_args[0][0] == "process_twilio_event"
    assert call_args[0][1]["MessageSid"] == "SM123"
    assert call_args[1]["correlation_id"] == "SM123"

@pytest.mark.asyncio
async def test_handle_webhook_event_task_success(service, payload):
    # Setup
    payload_dict = payload.model_dump(by_alias=True)
    service.process_webhook.return_value = None
    
    # Execute
    await service.handle_webhook_event_task(payload_dict)
    
    # Verify
    service.process_webhook.assert_called_once()
    # Check if called with equivalent payload
    called_arg = service.process_webhook.call_args[0][0]
    assert isinstance(called_arg, TwilioWhatsAppPayload)
    assert called_arg.message_sid == payload.message_sid

@pytest.mark.asyncio
async def test_handle_webhook_event_task_failure(service, payload):
    # Setup
    payload_dict = payload.model_dump(by_alias=True)
    service.process_webhook.side_effect = Exception("DB Error")
    
    # Execute & Verify
    with pytest.raises(Exception) as exc:
        await service.handle_webhook_event_task(payload_dict)
    
    assert "DB Error" in str(exc.value)
