
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi import HTTPException

from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.webhook.owner_resolver import TwilioWebhookOwnerResolver

@pytest.fixture
def mock_services():
    return {
        "twilio_account_service": MagicMock(),
        "identity_service": MagicMock(),
    }

@pytest.fixture
def resolver(mock_services):
    return TwilioWebhookOwnerResolver(
        twilio_account_service=mock_services["twilio_account_service"],
        identity_service=mock_services["identity_service"],
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
async def test_resolve_owner_id_success(resolver, mock_services, payload, owner_id):
    mock_account = MagicMock()
    mock_account.owner_id = owner_id
    mock_services["twilio_account_service"].resolve_account = AsyncMock(return_value=mock_account)

    result = await resolver.resolve_owner_id(payload)
    assert result == owner_id
    
    mock_services["twilio_account_service"].resolve_account.assert_called_once_with(
        to_number=payload.to_number, account_sid=payload.account_sid
    )

@pytest.mark.asyncio
async def test_resolve_owner_id_not_found(resolver, mock_services, payload):
    mock_services["twilio_account_service"].resolve_account = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await resolver.resolve_owner_id(payload)

    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_validate_owner_access(resolver, mock_services, owner_id):
    # Mock run_in_threadpool since it wraps the synchronous identity_service call
    with patch(
        "src.modules.channels.twilio.services.webhook.owner_resolver.run_in_threadpool",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.return_value = True
        
        result = await resolver.validate_owner_access(owner_id)
        
        assert result is True
        mock_run.assert_called_once()
        # Ensure it calls identity_service method (indirectly via run_in_threadpool args)
        # Note: checking args of run_in_threadpool is tricky as it takes func as first arg
        assert mock_run.call_args[0][0] == mock_services["identity_service"].validate_owner_access
