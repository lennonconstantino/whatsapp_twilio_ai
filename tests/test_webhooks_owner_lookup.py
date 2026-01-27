from types import SimpleNamespace

import pytest
from dependency_injector import providers
from httpx import AsyncClient

from src.main import app
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.models.results import TwilioMessageResult


class FakeTwilioAccountRepository:
    def __init__(self, client=None):
        pass

    def find_by_account_sid(self, account_sid: str):
        return TwilioAccount(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            account_sid=account_sid,
            auth_token="x",
            phone_numbers=["+14155238886"],
        )

    def find_by_phone_number(self, phone_number: str):
        return TwilioAccount(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            account_sid="AC_test",
            auth_token="x",
            phone_numbers=[phone_number],
        )


class FakeTwilioService:
    def __init__(self, twilio_repo=None):
        pass

    def send_message(
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
        self.message_repo = SimpleNamespace(
            find_by_external_id=lambda external_id: None,
        )

    def get_or_create_conversation(
        self,
        owner_id: int,
        from_number: str,
        to_number: str,
        channel: str = "whatsapp",
        user_id=None,
        metadata=None,
    ):
        return SimpleNamespace(conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV")

    def add_message(self, conversation, message_data):
        msg = SimpleNamespace(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            body=message_data.body,
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

    try:
        payload = {
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

        # The API endpoint has been refactored to NOT accept background_tasks
        # argument. It relies on QueueService which is injected.
        # We test the API endpoint via AsyncClient which calls the endpoint
        # normally.
        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post("/channels/twilio/v1/webhooks/inbound", data=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["conv_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert data["msg_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FA1"

    finally:
        # Reset overrides
        app.container.twilio_account_repository.reset_override()
        app.container.twilio_service.reset_override()
        app.container.conversation_service.reset_override()
        app.container.queue_service.reset_override()
