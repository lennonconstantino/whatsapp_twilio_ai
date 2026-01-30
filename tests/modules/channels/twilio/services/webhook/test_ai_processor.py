
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.webhook.ai_processor import TwilioWebhookAIProcessor

@pytest.fixture
def mock_services():
    return {
        "identity_service": MagicMock(),
        "agent_factory": MagicMock(),
        "queue_service": AsyncMock(),
        "message_handler": AsyncMock(),
    }

@pytest.fixture
def processor(mock_services):
    return TwilioWebhookAIProcessor(
        identity_service=mock_services["identity_service"],
        agent_factory=mock_services["agent_factory"],
        queue_service=mock_services["queue_service"],
        message_handler=mock_services["message_handler"],
    )

@pytest.fixture
def payload():
    return TwilioWhatsAppPayload(
        MessageSid="SM123",
        Body="Hello AI",
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

@pytest.mark.asyncio
async def test_enqueue_ai_task(processor, mock_services, owner_id, conv_id, msg_id):
    await processor.enqueue_ai_task(
        owner_id=owner_id,
        conversation_id=conv_id,
        msg_id=msg_id,
        payload_dump={},
        correlation_id="corr_1"
    )
    
    mock_services["queue_service"].enqueue.assert_called_once()
    args = mock_services["queue_service"].enqueue.call_args[1]
    assert args["task_name"] == "process_ai_response"

@pytest.mark.asyncio
async def test_handle_ai_response_success(processor, mock_services, payload, owner_id, conv_id, msg_id):
    # Mock user
    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user_1"}
    
    # Mock feature
    mock_feature = MagicMock()
    mock_feature.name = "finance"
    
    # Mock agent
    mock_agent = MagicMock()
    mock_agent.run = MagicMock() # Sync method in agent
    
    # Mock agent.run call via run_in_threadpool
    with patch(
        "src.modules.channels.twilio.services.webhook.ai_processor.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        # Sequence:
        # 1. get_user_by_phone
        # 2. get_active_feature
        # 3. agent.run
        mock_run.side_effect = [
            mock_user,
            mock_feature,
            "AI Response Text"
        ]
        
        mock_services["agent_factory"].get_agent.return_value = mock_agent
        
        await processor.handle_ai_response(
            owner_id=owner_id,
            conversation_id=conv_id,
            msg_id=msg_id,
            payload=payload,
            correlation_id="corr_1"
        )
        
        # Verify agent factory called
        mock_services["agent_factory"].get_agent.assert_called_once_with("finance")
        
        # Verify response sent
        mock_services["message_handler"].send_and_persist_response.assert_called_once()
        call_kwargs = mock_services["message_handler"].send_and_persist_response.call_args.kwargs
        # Fallback to positional check if kwargs empty (depends on how it was called)
        if not call_kwargs:
             # Check call_args[1] if it exists
             call_kwargs = mock_services["message_handler"].send_and_persist_response.call_args[1]
             
        assert call_kwargs.get("body") == "AI Response Text"
        # is_error might be default False, so check if it's NOT True if missing
        assert call_kwargs.get("is_error", False) is False


@pytest.mark.asyncio
async def test_handle_ai_response_persists_profile_name_and_injects_context(processor, mock_services, owner_id, conv_id, msg_id):
    named_payload = TwilioWhatsAppPayload(
        MessageSid="SM123",
        Body="Meu nome é Lennon, e eu gosto de Café",
        From="whatsapp:+1234567890",
        To="whatsapp:+0987654321",
        AccountSid="AC123",
        NumMedia=0,
        NumSegments=1,
        SmsStatus="received",
        ApiVersion="2010-04-01",
    )

    mock_user = MagicMock()
    mock_user.user_id = "user_1"
    mock_user.model_dump.return_value = {"user_id": "user_1", "profile_name": None}

    mock_feature = MagicMock()
    mock_feature.name = "finance"
    mock_feature.feature_id = 123

    mock_agent = MagicMock()
    mock_agent.run = MagicMock()
    mock_services["agent_factory"].get_agent.return_value = mock_agent

    with patch(
        "src.modules.channels.twilio.services.webhook.ai_processor.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            mock_user,
            mock_feature,
            mock_user,
            "AI Response Text",
        ]

        await processor.handle_ai_response(
            owner_id=owner_id,
            conversation_id=conv_id,
            msg_id=msg_id,
            payload=named_payload,
            correlation_id="corr_1",
        )

        assert mock_run.call_args_list[2].args[0] == mock_services["identity_service"].update_user_profile_name
        assert mock_run.call_args_list[2].args[1] == "user_1"
        assert mock_run.call_args_list[2].args[2] == "Lennon"

        agent_call = mock_run.call_args_list[3]
        assert agent_call.args[0] == mock_agent.run
        assert "profile_name: Lennon" in agent_call.kwargs.get("additional_context", "")


@pytest.mark.asyncio
async def test_handle_ai_response_forgets_profile_name(processor, mock_services, owner_id, conv_id, msg_id):
    forget_payload = TwilioWhatsAppPayload(
        MessageSid="SM123",
        Body="Esquece meu nome",
        From="whatsapp:+1234567890",
        To="whatsapp:+0987654321",
        AccountSid="AC123",
        NumMedia=0,
        NumSegments=1,
        SmsStatus="received",
        ApiVersion="2010-04-01",
    )

    mock_user = MagicMock()
    mock_user.user_id = "user_1"
    mock_user.model_dump.return_value = {"user_id": "user_1", "profile_name": "Lennon"}

    mock_feature = MagicMock()
    mock_feature.name = "finance"
    mock_feature.feature_id = 123

    mock_agent = MagicMock()
    mock_agent.run = MagicMock()
    mock_services["agent_factory"].get_agent.return_value = mock_agent

    with patch(
        "src.modules.channels.twilio.services.webhook.ai_processor.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = [
            mock_user,
            mock_feature,
            mock_user,
            "AI Response Text",
        ]

        await processor.handle_ai_response(
            owner_id=owner_id,
            conversation_id=conv_id,
            msg_id=msg_id,
            payload=forget_payload,
            correlation_id="corr_1",
        )

        assert mock_run.call_args_list[2].args[0] == mock_services["identity_service"].clear_user_profile_name
        assert mock_run.call_args_list[2].args[1] == "user_1"

@pytest.mark.asyncio
async def test_handle_ai_response_user_not_found(processor, mock_services, payload, owner_id, conv_id, msg_id):
    with patch(
        "src.modules.channels.twilio.services.webhook.ai_processor.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        # 1. get_user_by_phone -> None
        # 2. get_active_feature -> feature
        mock_run.side_effect = [
            None,
            MagicMock(name="finance")
        ]
        
        await processor.handle_ai_response(
            owner_id=owner_id,
            conversation_id=conv_id,
            msg_id=msg_id,
            payload=payload,
            correlation_id="corr_1"
        )
        
        # Should NOT run agent
        mock_services["agent_factory"].get_agent.assert_not_called()
        
        # Should send fallback
        mock_services["message_handler"].send_and_persist_response.assert_called_once()
        call_kwargs = mock_services["message_handler"].send_and_persist_response.call_args.kwargs
        assert "não encontrei seu cadastro" in call_kwargs.get("body", "")

@pytest.mark.asyncio
async def test_handle_ai_response_exception(processor, mock_services, payload, owner_id, conv_id, msg_id):
    with patch(
        "src.modules.channels.twilio.services.webhook.ai_processor.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.side_effect = Exception("DB Error")
        
        await processor.handle_ai_response(
            owner_id=owner_id,
            conversation_id=conv_id,
            msg_id=msg_id,
            payload=payload,
            correlation_id="corr_1"
        )
        
        # Should send error message
        mock_services["message_handler"].send_and_persist_response.assert_called_once()
        call_kwargs = mock_services["message_handler"].send_and_persist_response.call_args.kwargs
        assert "dificuldades técnicas" in call_kwargs.get("body", "")
        assert call_kwargs.get("is_error") is True
