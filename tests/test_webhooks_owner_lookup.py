from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from dependency_injector import providers
from httpx import AsyncClient

from src.main import app
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.models.results import TwilioMessageResult
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload

class FakeTwilioAccountRepository:
    def __init__(self, client=None):
        pass

    async def find_by_account_sid(self, account_sid: str):
        return TwilioAccount(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            tw_account_id=1,
            account_sid=account_sid,
            auth_token="x",
            phone_numbers=["+14155238886"],
        )

    async def find_by_phone_number(self, phone_number: str):
        return TwilioAccount(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            tw_account_id=1,
            account_sid="AC_test",
            auth_token="x",
            phone_numbers=[phone_number],
        )


class FakeTwilioService:
    def __init__(self, twilio_repo=None):
        pass

    async def send_message(
        self,
        owner_id: int,
        from_number: str,
        to_number: str,
        body: str,
        media_url=None,
    ):
        return TwilioMessageResult(
            sid="SM123",
            status="sent",
            to=to_number,
            from_number=from_number,
            body=body,
            direction="outbound-api",
            num_media=0,
        )


class FakeConversationService:
    def __init__(
        self, conversation_repo=None, message_repo=None, closure_detector=None
    ):
        self.message_repo = MagicMock()
        async def find_by_external_id(ext_id):
            return None
        self.message_repo.find_by_external_id = find_by_external_id

    async def get_or_create_conversation(
        self,
        owner_id: int,
        from_number: str,
        to_number: str,
        channel: str = "whatsapp",
        user_id=None,
        metadata=None,
    ):
        return SimpleNamespace(conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV")

    async def add_message(self, conversation, message_data):
        msg = SimpleNamespace(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            body=message_data.body,
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            conv_id=conversation.conv_id,
            timestamp=SimpleNamespace(isoformat=lambda: "2024-01-01T00:00:00Z"),
            message_owner=message_data.message_owner,
            metadata={}
        )
        return msg


@pytest.mark.asyncio
async def test_owner_lookup_inbound_local_sender():
    # Override dependencies
    app.container.twilio_account_repository.override(
        providers.Factory(FakeTwilioAccountRepository)
    )
    app.container.twilio_service.override(providers.Factory(FakeTwilioService))
    app.container.conversation_service.override(
        providers.Factory(FakeConversationService)
    )
    
    # Mock QueueService as it is used by message handler
    mock_queue = MagicMock()
    async def enqueue(*args, **kwargs):
        pass
    mock_queue.enqueue = enqueue
    app.container.queue_service.override(providers.Object(mock_queue))

    try:
        payload_dict = {
            "MessageSid": "SM_local_123",
            "AccountSid": "AC_test",
            "Body": "Olá",
            "MessageType": "text",
            "ProfileName": "Tester",
            "From": "whatsapp:+5511999999999",
            "To": "whatsapp:+14155238886",
            "NumMedia": "0",
            "NumSegments": "1",
            "SmsStatus": "received",
            "ApiVersion": "2010-04-01",
            "LocalSender": "True",
        }

        # Validate logic directly using the service, bypassing the API which is async/queue based
        twilio_webhook_service = app.container.twilio_webhook_service()
        payload = TwilioWhatsAppPayload(**payload_dict)
        
        # Call the logic directly
        response = await twilio_webhook_service.process_webhook(payload)

        assert response.success is True
        assert response.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert response.msg_id == "01ARZ3NDEKTSV4RRFFQ69G5FA1"

    finally:
        # Reset overrides
        app.container.twilio_account_repository.reset_override()
        app.container.twilio_service.reset_override()
        app.container.conversation_service.reset_override()
        app.container.queue_service.reset_override()
