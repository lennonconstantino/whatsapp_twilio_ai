import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.core.utils.exceptions import DuplicateError
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.twilio_webhook_service import \
    TwilioWebhookService
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_type import MessageType


@pytest.fixture
def mock_services():
    return {
        "twilio_service": MagicMock(),
        "conversation_service": MagicMock(),
        "identity_service": MagicMock(),
        "twilio_account_service": MagicMock(),
        "agent_runner": MagicMock(),
        "queue_service": AsyncMock(),
    }


@pytest.fixture
def service(mock_services):
    mock_services["queue_service"].register_handler = MagicMock()
    return TwilioWebhookService(
        twilio_service=mock_services["twilio_service"],
        conversation_service=mock_services["conversation_service"],
        identity_service=mock_services["identity_service"],
        twilio_account_service=mock_services["twilio_account_service"],
        agent_runner=mock_services["agent_runner"],
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


def test_determine_message_type_text(service):
    msg_type = service._determine_message_type(0, None)
    assert msg_type == MessageType.TEXT


def test_determine_message_type_image(service):
    msg_type = service._determine_message_type(1, "image/jpeg")
    assert msg_type == MessageType.IMAGE


def test_determine_message_type_audio(service):
    msg_type = service._determine_message_type(1, "audio/ogg")
    assert msg_type == MessageType.AUDIO


def test_determine_message_type_video(service):
    msg_type = service._determine_message_type(1, "video/mp4")
    assert msg_type == MessageType.VIDEO


def test_determine_message_type_document(service):
    msg_type = service._determine_message_type(1, "application/pdf")
    assert msg_type == MessageType.DOCUMENT


def test_resolve_owner_id_success(service, mock_services, payload, owner_id):
    mock_account = MagicMock()
    mock_account.owner_id = owner_id
    mock_services["twilio_account_service"].resolve_account.return_value = mock_account

    result = service.resolve_owner_id(payload)
    assert result == owner_id


def test_resolve_owner_id_not_found(service, mock_services, payload):
    mock_services["twilio_account_service"].resolve_account.return_value = None

    with pytest.raises(HTTPException) as exc:
        service.resolve_owner_id(payload)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_process_webhook_local_sender(service, payload, owner_id):
    # Setup
    payload.local_sender = True

    with patch(
        "src.modules.channels.twilio.services.twilio_webhook_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            owner_id,  # resolve_owner_id
        ]

        with patch.object(
            service, "_process_local_sender", new_callable=AsyncMock
        ) as mock_process_local:
            mock_process_local.return_value = "response"

            result = await service.process_webhook(payload)

            mock_process_local.assert_called_once_with(owner_id, payload)
            assert result == "response"


@pytest.mark.asyncio
async def test_process_webhook_inbound(service, payload, owner_id):
    # Setup
    payload.local_sender = False

    with patch(
        "src.modules.channels.twilio.services.twilio_webhook_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            owner_id,  # resolve_owner_id
        ]

        with patch.object(
            service, "_process_inbound_message", new_callable=AsyncMock
        ) as mock_process_inbound:
            mock_process_inbound.return_value = "response"

            result = await service.process_webhook(payload)

            mock_process_inbound.assert_called_once_with(owner_id, payload)
            assert result == "response"


@pytest.mark.asyncio
async def test_process_local_sender(service, payload, owner_id, conv_id, msg_id):
    # Mock conversation
    mock_conv = MagicMock()
    mock_conv.conv_id = conv_id

    # Mock twilio response
    mock_twilio_resp = MagicMock()
    mock_twilio_resp.body = "Sent body"
    mock_twilio_resp.sid = "SM_new"
    mock_twilio_resp.status = "sent"
    mock_twilio_resp.num_media = 0

    # Mock message
    mock_msg = MagicMock()
    mock_msg.msg_id = msg_id
    mock_msg.body = "Sent body"

    with patch(
        "src.modules.channels.twilio.services.twilio_webhook_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            mock_conv,  # get_or_create_conversation
            mock_twilio_resp,  # send_message
            mock_msg,  # add_message
        ]

        result = await service._process_local_sender(owner_id, payload)

        assert result.success is True
        assert result.message == "Sent body"
        assert result.conv_id == conv_id


@pytest.mark.asyncio
async def test_process_inbound_message_success(
    service, mock_services, payload, owner_id, conv_id, msg_id
):
    # Mock conversation
    mock_conv = MagicMock()
    mock_conv.conv_id = conv_id

    # Mock message
    mock_msg = MagicMock()
    mock_msg.msg_id = msg_id

    with patch(
        "src.modules.channels.twilio.services.twilio_webhook_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            mock_conv,  # get_or_create_conversation
            mock_msg,  # add_message
        ]

        result = await service._process_inbound_message(owner_id, payload)

        assert result.success is True
        assert result.message == "Message received and processing started"

        # Verify queue enqueue
        mock_services["queue_service"].enqueue.assert_called_once()
        call_args = mock_services["queue_service"].enqueue.call_args
        assert call_args[1]["task_name"] == "process_ai_response"
        assert call_args[1]["owner_id"] == owner_id


@pytest.mark.asyncio
async def test_process_inbound_message_duplicate(service, payload, owner_id, conv_id):
    # Mock conversation
    mock_conv = MagicMock()
    mock_conv.conv_id = conv_id

    with patch(
        "src.modules.channels.twilio.services.twilio_webhook_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            mock_conv,  # get_or_create_conversation
            DuplicateError(),  # add_message raises DuplicateError
            MagicMock(msg_id="01HRZ32M1X6Z4P5R7W8K9A0M10"),  # find_by_external_id
        ]

        result = await service._process_inbound_message(owner_id, payload)

        assert result.success is True
        assert result.message == "Already processed"
        assert result.msg_id == "01HRZ32M1X6Z4P5R7W8K9A0M10"


@pytest.mark.asyncio
async def test_handle_ai_response_task(service, payload, owner_id, conv_id, msg_id):
    task_payload = {
        "payload": payload.model_dump(),
        "owner_id": owner_id,
        "conversation_id": conv_id,
        "msg_id": msg_id,
        "correlation_id": "corr_123",
    }

    with patch(
        "src.modules.channels.twilio.services.twilio_webhook_service.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        await service.handle_ai_response_task(task_payload)
        mock_run.assert_called_once()


def test_handle_ai_response_success(
    service, mock_services, payload, owner_id, conv_id, msg_id
):
    # Mock dependencies
    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user_1"}
    mock_services["identity_service"].get_user_by_phone.return_value = mock_user

    mock_services["identity_service"].validate_feature_path.return_value = {
        "feature": "finance"
    }
    mock_feature = MagicMock()
    mock_feature.feature_id = "feat_1"
    mock_services["identity_service"].get_feature_by_name.return_value = mock_feature

    mock_services["agent_runner"].run.return_value = "AI Response"

    mock_twilio_resp = MagicMock()
    mock_twilio_resp.body = "AI Response"
    mock_twilio_resp.sid = "SM_resp"
    mock_services["twilio_service"].send_message.return_value = mock_twilio_resp

    service.handle_ai_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        msg_id=msg_id,
        payload=payload,
        correlation_id="corr_123",
    )

    mock_services["agent_runner"].run.assert_called_once()
    mock_services["twilio_service"].send_message.assert_called_once()
    mock_services["conversation_service"].add_message.assert_called_once()


def test_handle_ai_response_user_not_found(
    service, mock_services, payload, owner_id, conv_id, msg_id
):
    mock_services["identity_service"].get_user_by_phone.return_value = None
    mock_services["identity_service"].validate_feature_path.return_value = {
        "feature": "finance"
    }

    mock_twilio_resp = MagicMock()
    mock_twilio_resp.body = "Fallback msg"
    mock_services["twilio_service"].send_message.return_value = mock_twilio_resp

    service.handle_ai_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        msg_id=msg_id,
        payload=payload,
        correlation_id="corr_123",
    )

    # Should not call agent runner
    mock_services["agent_runner"].run.assert_not_called()
    # Should send fallback message
    mock_services["twilio_service"].send_message.assert_called_once()
    args = mock_services["twilio_service"].send_message.call_args[1]
    assert "não encontrei seu cadastro" in args["body"]


def test_handle_ai_response_error(
    service, mock_services, payload, owner_id, conv_id, msg_id
):
    mock_services["identity_service"].get_user_by_phone.side_effect = Exception(
        "DB Error"
    )

    mock_twilio_resp = MagicMock()
    mock_services["twilio_service"].send_message.return_value = mock_twilio_resp

    service.handle_ai_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        msg_id=msg_id,
        payload=payload,
        correlation_id="corr_123",
    )

    # Should send error message
    mock_services["twilio_service"].send_message.assert_called_once()
    args = mock_services["twilio_service"].send_message.call_args[1]
    assert "dificuldades técnicas" in args["body"]


def test_handle_ai_response_empty_agent_response(
    service, mock_services, payload, owner_id, conv_id, msg_id
):
    """Test handling of empty response from agent."""
    # Mock dependencies
    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user_1"}
    mock_services["identity_service"].get_user_by_phone.return_value = mock_user

    mock_services["identity_service"].validate_feature_path.return_value = {
        "feature": "finance"
    }
    mock_feature = MagicMock()
    mock_services["identity_service"].get_feature_by_name.return_value = mock_feature

    # Mock empty response
    mock_services["agent_runner"].run.return_value = ""

    mock_twilio_resp = MagicMock()
    mock_services["twilio_service"].send_message.return_value = mock_twilio_resp

    service.handle_ai_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        msg_id=msg_id,
        payload=payload,
        correlation_id="corr_123",
    )

    # Should send fallback message for empty response
    mock_services["twilio_service"].send_message.assert_called_once()
    args = mock_services["twilio_service"].send_message.call_args[1]
    assert "erro interno ao processar sua mensagem" in args["body"]


def test_send_and_persist_response_failure(service, mock_services, owner_id, conv_id):
    mock_services["twilio_service"].send_message.return_value = None

    service._send_and_persist_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        sender_number="123",
        recipient_number="456",
        body="msg",
        correlation_id="corr",
    )

    mock_services["conversation_service"].add_message.assert_not_called()


def test_send_and_persist_response_exception(service, mock_services, owner_id, conv_id):
    """Test exception handling during send/persist."""
    mock_services["twilio_service"].send_message.side_effect = Exception("Twilio Error")

    # Should not raise exception
    service._send_and_persist_response(
        owner_id=owner_id,
        conversation_id=conv_id,
        sender_number="123",
        recipient_number="456",
        body="msg",
        correlation_id="corr",
    )
